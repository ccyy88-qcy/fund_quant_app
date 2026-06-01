"""数据获取模块 — 复用现有脚本的数据管线"""
import re
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak
import httpx
import pandas as pd
import numpy as np

CACHE_DIR = __file__.rsplit("/", 2)[0] + "/data"
CACHE_TTL = 3600  # 1h

def _cache_get(key: str) -> Optional[dict]:
    import os
    path = f"{CACHE_DIR}/{hashlib.md5(key.encode()).hexdigest()}.json"
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < CACHE_TTL:
            return json.loads(open(path).read())
    return None

def _cache_set(key: str, data):
    import os
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = f"{CACHE_DIR}/{hashlib.md5(key.encode()).hexdigest()}.json"
    with open(path, "w") as f:
        json.dump(data, f)

# ─── 基金搜索 ───

def search_funds(keyword: str, limit: int = 20) -> list:
    """搜索基金，按关键字匹配名称/代码"""
    cache_key = f"search:{keyword}"
    cached = _cache_get(cache_key)
    if cached:
        return cached[:limit]
    # 缓存全量基金列表（每天刷新）
    full_key = "fund_list_full"
    full = _cache_get(full_key)
    if not full:
        try:
            df = ak.fund_name_em()
            full = df.to_dict('records')
            _cache_set(full_key, full)
        except Exception as e:
            return [{'code': '', 'name': f'数据获取失败: {str(e)}', 'type': ''}]
    # 匹配
    results = []
    for r in full:
        code = str(r.get('基金代码', ''))
        name = str(r.get('基金简称', ''))
        ftype = str(r.get('基金类型', ''))
        if keyword in code or keyword in name:
            results.append({'code': code, 'name': name, 'type': ftype})
            if len(results) >= limit:
                break
    return results

# ─── 基金基本信息 ───

def get_fund_info(code: str) -> dict:
    """获取基金基本信息"""
    cache_key = f"info:{code}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    info = {'code': code, 'name': '', 'type': '', 'established': '', 'manager': '',
            'fund_size': '', 'tracking': '', 'risk_level': ''}

    # 从排行数据获取
    try:
        rank_df = ak.fund_open_fund_rank_em()
        row = rank_df[rank_df['基金代码'] == code]
        if len(row) > 0:
            row = row.iloc[0]
            info['name'] = row.get('基金简称', '')
            info['type'] = row.get('基金类型', '')
            info['fund_size'] = str(row.get('基金规模', ''))
            info['established'] = str(row.get('成立日期', ''))
    except:
        pass

    # 如果排行数据找不到，从全量基金列表获取
    if not info['name']:
        try:
            df = ak.fund_name_em()
            row = df[df['基金代码'] == code]
            if len(row) > 0:
                info['name'] = row.iloc[0].get('基金简称', '')
                info['type'] = row.iloc[0].get('基金类型', '')
        except:
            pass

    _cache_set(cache_key, info)
    return info

# ─── K线数据 ───

def get_kline(code: str, days: int = 500) -> list:
    """获取基金/ETF日K线"""
    cache_key = f"kline:{code}:{days}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    kline = []
    # 策略1: 新浪财经ETF K线API（优先，Termux兼容）
    try:
        prefix = "sh" if code.startswith("51") or code.startswith("56") else "sz"
        url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={prefix}{code}&scale=240&datalen={min(days, 2000)}'
        resp = httpx.get(url, timeout=15)
        data = json.loads(resp.text)
        if data and len(data) > 0:
            for d in data[-days:]:
                kline.append({
                    'day': str(d['day'])[:10],
                    'open': float(d['open']),
                    'high': float(d['high']),
                    'low': float(d['low']),
                    'close': float(d['close']),
                    'volume': float(d.get('volume', 0)),
                })
    except:
        pass

    # 策略2: 东方财富ETF历史行情（备用）
    if not kline:
        try:
            df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date="20180101", adjust="qfq")
            if df is not None and len(df) > 0:
                df = df.tail(days)
                for _, r in df.iterrows():
                    kline.append({
                        'day': str(r['日期'])[:10],
                        'open': float(r['开盘']),
                        'high': float(r['最高']),
                        'low': float(r['最低']),
                        'close': float(r['收盘']),
                        'volume': float(r.get('成交量', 0)),
                    })
        except:
            pass

    # 策略3: 场外基金净值（天天基金）
    if not kline:
        try:
            url = f'https://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={code}&page=1&per={min(days, 260)}'
            resp = httpx.get(url, timeout=15)
            rows = re.findall(
                r'<td>(\d{4}-\d{2}-\d{2})</td><td[^>]*>([\d\.]+)</td><td[^>]*>([\d\.]+)</td>',
                resp.text
            )
            for day, nav, acc_nav in rows[-days:]:
                nav_f = float(nav)
                kline.append({
                    'day': day, 'open': nav_f, 'high': nav_f, 'low': nav_f, 'close': nav_f,
                    'volume': 0, 'acc_nav': float(acc_nav),
                })
        except:
            pass

    _cache_set(cache_key, kline)
    return kline

# ─── 实时估值 ───

def get_realtime_estimation(codes: list) -> list:
    """获取多只基金实时估值（ETF用K线收盘价）"""
    results = []
    for code in codes:
        try:
            kline = get_kline(code, 5)
            if kline and len(kline) > 0:
                last = kline[-1]
                prev = kline[-2] if len(kline) > 1 else kline[-1]
                close = float(last['close'])
                prev_close = float(prev['close'])
                change = round((close - prev_close) / prev_close * 100, 2) if prev_close > 0 else None
                info = get_fund_info(code)
                results.append({
                    'code': code,
                    'name': info.get('name', code),
                    'est_nav': close,
                    'est_change': change,
                    'nav': close,
                })
        except:
            pass
    return results

# ─── 大盘指数行情 ───

def get_market_index() -> list:
    """获取主要指数行情（上证/沪深300/创业板/恒生/纳斯达克）"""
    indices = {
        'sh': '000001', 'sz': '399001', 'cyb': '399006',
        'hs300': '000300', 'zz500': '000905',
    }
    results = []
    for name, code in indices.items():
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{code}" if code.startswith('00') else f"sz{code}")
            if df is not None and len(df) > 0:
                latest = df.iloc[-1]
                prev = df.iloc[-2]
                change = (latest['close'] - prev['close']) / prev['close'] * 100
                results.append({
                    'name': {'sh':'上证指数','sz':'深证成指','cyb':'创业板指','hs300':'沪深300','zz500':'中证500'}.get(name, name),
                    'code': code,
                    'price': round(float(latest['close']), 2),
                    'change': round(float(change), 2),
                })
        except:
            pass
    return results

# ─── 申万行业涨跌 ───

def get_sector_performance() -> list:
    """获取行业板块涨跌排行（东方财富行业板块，一次性接口）"""
    try:
        df = ak.stock_board_industry_name_em()
        if df is None or len(df) == 0:
            return []
        results = []
        for _, row in df.iterrows():
            results.append({
                'code': str(row.get('板块代码', '')),
                'name': str(row.get('板块名称', '')),
                'change': round(float(row.get('涨跌幅', 0)), 2),
                'price': round(float(row.get('最新价', 0)), 2),
                'amount': float(row.get('成交额', 0)),
            })
        return sorted(results, key=lambda x: x['change'], reverse=True)[:20]
    except:
        return []
