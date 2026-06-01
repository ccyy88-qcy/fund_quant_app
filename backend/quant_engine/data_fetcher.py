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

def _cache_get(key: str, ttl: int = None) -> Optional[dict]:
    import os
    path = f"{CACHE_DIR}/{hashlib.md5(key.encode()).hexdigest()}.json"
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        max_age = ttl if ttl is not None else CACHE_TTL
        if age < max_age:
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

    # 策略3: 场外基金净值（天天基金JSON API）
    if not kline:
        try:
            headers = {'Referer': 'https://fund.eastmoney.com/', 'User-Agent': 'Mozilla/5.0'}
            max_pages = max(1, (days + 19) // 20)
            for page in range(1, max_pages + 1):
                url = f'https://api.fund.eastmoney.com/f10/lsjz?callback=jQuery&fundCode={code}&pageIndex={page}&pageSize=20'
                resp = httpx.get(url, headers=headers, timeout=15)
                text = resp.text.strip()
                if text.startswith('jQuery('):
                    text = text[7:-1]
                data = json.loads(text)
                items = data.get('Data', {}).get('LSJZList', [])
                if not items:
                    break
                for item in items:
                    nav = item.get('DWJZ', '')
                    acc_nav = item.get('LJJZ', '')
                    if nav and acc_nav:
                        nav_f = float(nav)
                        kline.append({
                            'day': item['FSRQ'], 'open': nav_f, 'high': nav_f,
                            'low': nav_f, 'close': nav_f,
                            'volume': 0, 'acc_nav': float(acc_nav),
                        })
            kline.reverse()  # API返回倒序
        except Exception:
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
    """获取主要指数实时行情（新浪实时API，含今日涨跌）"""
    indices = {
        'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指',
        'sh000300': '沪深300', 'sh000905': '中证500',
    }
    results = []
    for sym, name in indices.items():
        try:
            url = f'https://hq.sinajs.cn/list={sym}'
            resp = httpx.get(url, headers={'Referer': 'https://finance.sina.com.cn'}, timeout=10)
            text = resp.text.strip()
            # 格式: var hq_str_sh000001="名称,昨收,今开,当前,最高,最低,...";
            if '="' not in text:
                continue
            parts = text.split('="')[1].split('","')[0].split(',')
            if len(parts) < 4:
                continue
            yesterday_close = float(parts[1])  # 昨收
            current_price = float(parts[3])   # 当前价
            change = round((current_price - yesterday_close) / yesterday_close * 100, 2) if yesterday_close > 0 else 0
            results.append({
                'name': name, 'code': sym.replace('sh', '').replace('sz', ''),
                'price': round(current_price, 2), 'change': change,
            })
        except Exception:
            pass
    return results

# ─── 申万行业涨跌（curl方案，带缓存防限频）───

def get_sector_performance() -> list:
    """获取行业板块涨跌排行（东方财富行业板块，curl子进程调用，60s缓存防限频）"""
    cache_key = "sector_performance"
    cached = _cache_get(cache_key, ttl=60)
    if cached:
        return cached
    try:
        import subprocess, traceback
        url = ('https://push2.eastmoney.com/api/qt/clist/get?'
               'pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&'
               'fs=m:90+t:2&fields=f12,f14,f2,f3,f4')
        r = subprocess.run(
            ['curl', '-s', '--connect-timeout', '10', '--max-time', '15',
             '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
             url],
            capture_output=True, text=True, timeout=20)
        stdout_len = len(r.stdout)
        if stdout_len == 0:
            print(f"[sector_warn] curl stdout empty, stderr={r.stderr[:100]}")
            return []
        data = json.loads(r.stdout)
        if data.get('rc') != 0:
            return []
        results = []
        for item in data['data']['diff']:
            results.append({
                'code': str(item.get('f12', '')),
                'name': str(item.get('f14', '')),
                'change': round(float(item.get('f3', 0)), 2),
                'price': round(float(item.get('f2', 0)), 2),
                'amount': float(item.get('f4', 0)),
            })
        results = sorted(results, key=lambda x: x['change'], reverse=True)[:20]
        _cache_set(cache_key, results)  # 60s缓存防限频
        return results
    except Exception:
        return []
