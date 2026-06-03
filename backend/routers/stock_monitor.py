"""股票实时监控系统 - 行情、资金流向、技术指标"""
import sys, os, json, math, re, asyncio
from datetime import datetime, timedelta
import urllib.request
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse as FastJSONResponse
from typing import Optional
import numpy as np


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.ndarray,)): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        return super().default(obj)


class _NumpyJSONResponse(FastJSONResponse):
    def render(self, content: dict) -> bytes:
        return json.dumps(content, cls=_NumpyEncoder, ensure_ascii=False).encode('utf-8')


router = APIRouter(prefix="/api/monitor", tags=["股票监控"])

# ========== 默认自选股 ==========
DEFAULT_WATCHLIST = [
    {"code": "600711.SH", "name": "盛屯矿业"},
    {"code": "600497.SH", "name": "驰宏锌锗"},
    {"code": "000737.SZ", "name": "北方铜业"},
    {"code": "000630.SZ", "name": "铜陵有色"},
    {"code": "002429.SZ", "name": "兆驰股份"},
]

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "watchlist.json")


def _load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except:
            return DEFAULT_WATCHLIST.copy()
    return DEFAULT_WATCHLIST.copy()


def _save_watchlist(data):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def _tencent_to_code(code: str) -> str:
    """转换代码为腾讯格式"""
    if code.endswith(".SH"):
        return "sh" + code.split(".")[0]
    elif code.endswith(".SZ"):
        return "sz" + code.split(".")[0]
    return code


def _code_to_secid(code: str) -> str:
    """转东方财富secid格式"""
    if code.endswith(".SH"):
        return f"1.{code.split('.')[0]}"
    elif code.endswith(".SZ"):
        return f"0.{code.split('.')[0]}"
    return code


def _fetch_tencent_quote(codes):
    """从腾讯财经获取实时行情"""
    tencodes = [_tencent_to_code(c) for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(tencodes)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read()
        try:
            text = raw.decode("gbk")
        except:
            text = raw.decode("utf-8", errors="replace")
        results = {}
        for line in text.strip().split("\n"):
            if not line.strip():
                continue
            match = re.search(r'"(.*)"', line)
            if not match:
                continue
            parts = match.group(1).split("~")
            if len(parts) < 40:
                continue
            code_raw = parts[2]
            results[code_raw] = {
                "name": parts[1].replace("铅", "铅").replace("锗", "锗").replace("钼", "钼").replace("锌", "锌").replace("驰", "驰").replace("铜", "铜"),
                "price": _safe_float(parts[3]),
                "yclose": _safe_float(parts[4]),
                "open": _safe_float(parts[5]),
                "volume": _safe_int(parts[6]),
                "high": _safe_float(parts[33]),
                "low": _safe_float(parts[34]),
                "change_pct": _safe_float(parts[32]),
                "change_amt": _safe_float(parts[31]),
                "amount": _safe_float(parts[37]),
                "turnover_rate": _safe_float(parts[38]),
                "pe": _safe_float(parts[39]),
                "time": parts[30],
                "bid_prices": [],
                "ask_prices": [],
            }
            # 五档
            for i in range(5):
                bp = _safe_float(parts[9 + i * 2]) if 9 + i * 2 < len(parts) else 0
                bv = _safe_int(parts[10 + i * 2]) if 10 + i * 2 < len(parts) else 0
                if bp > 0:
                    results[code_raw]["bid_prices"].append({"p": bp, "v": bv})
            for i in range(5):
                ap = _safe_float(parts[19 + i * 2]) if 19 + i * 2 < len(parts) else 0
                av = _safe_int(parts[20 + i * 2]) if 20 + i * 2 < len(parts) else 0
                if ap > 0:
                    results[code_raw]["ask_prices"].append({"p": ap, "v": av})

        return results
    except Exception as e:
        return {"_error": str(e)}


def _safe_float(v):
    try:
        return float(v)
    except:
        return 0.0


def _safe_int(v):
    try:
        return int(float(v))
    except:
        return 0


# ========== K线获取 & 技术指标 ==========

def _fetch_kline(code: str, days: int = 60):
    """从新浪获取K线数据"""
    tcode = _tencent_to_code(code)
    url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={tcode}&scale=240&datalen={days}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        return data
    except:
        return None


def _calc_ema(data, period):
    """计算EMA"""
    result = []
    k = 2 / (period + 1)
    ema = None
    for v in data:
        if ema is None:
            ema = v
        else:
            ema = v * k + ema * (1 - k)
        result.append(ema)
    return result


def _calc_sma(data, period):
    """计算SMA"""
    result = []
    s = 0
    for i, v in enumerate(data):
        s += v
        if i >= period - 1:
            if i >= period:
                s -= data[i - period]
            result.append(s / period)
        else:
            result.append(None)
    return result


def _calc_macd(closes):
    """计算MACD"""
    ema12 = _calc_ema(closes, 12)
    ema26 = _calc_ema(closes, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    dea = _calc_ema(dif, 9)
    macd = [(d - dea[i]) * 2 if dea[i] is not None else 0 for i, d in enumerate(dif)]
    return {
        "dif": round(dif[-1], 4) if dif else 0,
        "dea": round(dea[-1], 4) if dea else 0,
        "macd": round(macd[-1], 4) if macd else 0,
        "trend": "金叉" if len(dif) > 1 and dif[-1] > dea[-1] and dif[-2] <= dea[-2] else
                 "死叉" if len(dif) > 1 and dif[-1] < dea[-1] and dif[-2] >= dea[-2] else
                 "多头" if dif[-1] > dea[-1] else "空头",
    }


def _calc_rsi(closes, period=14):
    """计算RSI"""
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(len(closes) - period, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100
    rs = gains / losses
    return round(100 - 100 / (1 + rs), 2)


def _calc_kdj(closes, highs, lows):
    """计算KDJ"""
    n = 9
    if len(closes) < n:
        return {"k": 50, "d": 50, "j": 50}
    hv = max(highs[-n:])
    lv = min(lows[-n:])
    if hv == lv:
        return {"k": 50, "d": 50, "j": 50}
    rsv = (closes[-1] - lv) / (hv - lv) * 100
    k = rsv / 3 + 50 * 2 / 3
    d = k / 3 + 50 * 2 / 3
    j = 3 * k - 2 * d
    return {"k": round(k, 2), "d": round(d, 2), "j": round(j, 2)}


def _calc_ma(closes, period):
    """计算均线"""
    if len(closes) < period:
        return round(sum(closes) / len(closes), 2) if closes else 0
    return round(sum(closes[-period:]) / period, 2)


def _calc_boll(closes, period=20):
    """计算布林带"""
    if len(closes) < period:
        return {"mid": closes[-1], "upper": closes[-1], "lower": closes[-1]}
    ma = sum(closes[-period:]) / period
    variance = sum((x - ma) ** 2 for x in closes[-period:]) / period
    std = math.sqrt(variance)
    return {
        "mid": round(ma, 2),
        "upper": round(ma + 2 * std, 2),
        "lower": round(ma - 2 * std, 2),
    }


def calc_technical(code: str):
    """综合计算技术指标"""
    kline = _fetch_kline(code, 60)
    if not kline or len(kline) < 10:
        return None

    closes = [float(k.get("close", k.get("c", 0))) for k in kline]
    highs = [float(k.get("high", k.get("h", 0))) for k in kline]
    lows = [float(k.get("low", k.get("l", 0))) for k in kline]
    opens = [float(k.get("open", k.get("o", 0))) for k in kline]
    volumes = [float(k.get("volume", k.get("v", 0))) for k in kline]

    return {
        "price": closes[-1],
        "ma5": _calc_ma(closes, 5),
        "ma10": _calc_ma(closes, 10),
        "ma20": _calc_ma(closes, 20),
        "ma60": _calc_ma(closes, 60),
        "macd": _calc_macd(closes),
        "rsi": _calc_rsi(closes, 14),
        "kdj": _calc_kdj(closes, highs, lows),
        "boll": _calc_boll(closes, 20),
        "ma_trend": "多头排列" if len(closes) >= 20 and
                    _calc_ma(closes, 5) > _calc_ma(closes, 10) > _calc_ma(closes, 20)
                    else "空头排列" if len(closes) >= 20 and
                    _calc_ma(closes, 5) < _calc_ma(closes, 10) < _calc_ma(closes, 20)
                    else "震荡",
        "vol_ma5": _calc_ma(volumes, 5),
        "vol_ma20": _calc_ma(volumes, 20),
        "last_kline_date": kline[-1].get("day", kline[-1].get("d", "")),
    }


# ========== 问财资金流向 ==========

def _get_today_str():
    return datetime.now().strftime("%Y%m%d")


def _get_flow_iwencai(code: str):
    """从问财获取资金流向"""
    api_key = os.environ.get("IWENCAI_API_KEY", "")
    if not api_key:
        return None

    c = code.replace(".SH", "").replace(".SZ", "")
    query = f"{c} 今日主力资金净流入 特大单净买入 大单净买入 中单净买入 小单净买入 主力增仓占比"
    import secrets

    payload = json.dumps({
        "query": query,
        "page": "1",
        "limit": "3",
        "is_cache": "1",
        "expand_index": "true",
    })
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": "custom-stock-monitor",
        "X-Claw-Skill-Version": "1.0.0",
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }
    req = urllib.request.Request(
        "https://api.iwencai.com/unifiedwap/chat",
        data=payload.encode(),
        headers=headers,
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode())
        if result.get("status_code") != 0:
            return None
        datas = result.get("datas", [])
        if not datas:
            return None
        d = datas[0]
        td = _get_today_str()
        return {
            "main_force": _safe_float(d.get(f"主力资金流向[{td}]", 0)),
            "super_large": _safe_float(d.get(f"特大单净买入额[{td}]", 0)),
            "large": _safe_float(d.get(f"dde大单净额[{td}]", 0)),
            "medium": _safe_float(d.get(f"中单净买入额[{td}]", 0)),
            "small": _safe_float(d.get(f"小单净买入额[{td}]", 0)),
            "main_ratio": _safe_float(d.get(f"主力增仓占比[{td}]", 0)),
        }
    except:
        return None


# ========== API接口 ==========

@router.get("/stocks")
async def get_stocks():
    """获取所有自选股实时行情+技术指标+资金流向"""
    watchlist = _load_watchlist()
    codes = [item["code"] for item in watchlist]
    name_map = {item["code"]: item["name"] for item in watchlist}

    quotes = _fetch_tencent_quote(codes)
    results = []
    for item in watchlist:
        code = item["code"]
        code_raw = code.replace(".SH", "").replace(".SZ", "")
        q = quotes.get(code_raw, {})
        if not q or q.get("price", 0) == 0:
            continue

        # 技术指标（异步）
        tech = calc_technical(code)
        # 资金流向
        flow = _get_flow_iwencai(code)

        results.append({
            "code": code,
            "name": name_map.get(code, q.get("name", "")),
            "quote": q,
            "technical": tech,
            "flow": flow,
            "updated_at": datetime.now().strftime("%H:%M:%S"),
        })
    return {"stocks": results, "count": len(results)}


@router.get("/stocks/{code}")
async def get_stock_detail(code: str):
    """获取单只股票详细数据"""
    if not code.startswith("0") and not code.startswith("1"):
        # 自动补全
        pass
    codes = [code]
    quotes = _fetch_tencent_quote(codes)
    code_raw = code.replace(".SH", "").replace(".SZ", "")
    q = quotes.get(code_raw, {})
    if not q:
        raise HTTPException(404, "股票未找到")
    tech = calc_technical(code)
    flow = _get_flow_iwencai(code)
    return {
        "quote": q,
        "technical": tech,
        "flow": flow,
        "updated_at": datetime.now().strftime("%H:%M:%S"),
    }


@router.get("/watchlist")
async def get_watchlist():
    """获取自选列表"""
    return {"watchlist": _load_watchlist()}


@router.post("/watchlist")
async def add_watchlist(code: str = Query(...), name: str = Query("")):
    """添加自选"""
    wl = _load_watchlist()
    if not any(w["code"] == code for w in wl):
        wl.append({"code": code, "name": name or code})
        _save_watchlist(wl)
    return {"watchlist": wl}


@router.delete("/watchlist")
async def remove_watchlist(code: str = Query(...)):
    """删除自选"""
    wl = _load_watchlist()
    wl = [w for w in wl if w["code"] != code]
    _save_watchlist(wl)
    return {"watchlist": wl}
