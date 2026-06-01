"""全市场扫描 API路由 — 真实数据，无模拟"""
from fastapi import APIRouter, Query
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import market_scanner as ms
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/scanner', tags=['scanner'])


@router.get('/build-candidates')
async def build_candidates(top_n: int = Query(10, description='返回数量')):
    """全市场扫描：找出最适合建仓的ETF（真实数据）"""
    import asyncio
    try:
        results = await asyncio.to_thread(ms.scan_build_candidates, top_n=top_n)
        return {'data': results, 'source': 'real_market', 'count': len(results)}
    except Exception as e:
        return {'data': [], 'source': 'error', 'error': str(e)}


@router.get('/hot-etfs')
async def hot_etfs(top_n: int = Query(20)):
    """热门ETF排行（按活跃度：成交额+量比+振幅）"""
    import asyncio
    try:
        results = await asyncio.to_thread(ms.scan_etf_market, top_n=top_n)
        return {'data': results, 'source': 'real_market', 'count': len(results)}
    except Exception as e:
        return {'data': [], 'source': 'error', 'error': str(e)}


@router.get('/analyze')
async def analyze_etf(code: str = Query('562360', description='ETF代码')):
    """单只ETF深度分析（真实K线+技术指标）"""
    kline = df.get_kline(code, 300)
    if not kline:
        return {'error': f'获取{code}数据失败'}

    # 获取实时行情
    import akshare as ak
    try:
        spot = ak.fund_etf_spot_em()
        spot_row = spot[spot['代码'].astype(str).str.strip() == code]
    except:
        spot_row = None

    import pandas as pd
    import numpy as np
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])

    from quant_engine.indicators import calc_ma, calc_rsi, calc_macd, calc_bollinger
    from quant_engine.signals import calc_signal_v4

    # 计算各项指标
    current = float(closes.iloc[-1])
    ma_info = {}
    for p in [5, 10, 20, 30, 60]:
        ma = calc_ma(closes, p)
        ma_info[f'ma{p}'] = round(float(ma.iloc[-1]), 4) if not np.isnan(ma.iloc[-1]) else None

    rsi_val = round(float(calc_rsi(closes, 14).iloc[-1]), 2)
    dif, dea, macd_bar = calc_macd(closes)
    boll_u, boll_m, boll_l = calc_bollinger(closes)

    result = {
        'code': code,
        'name': str(spot_row.iloc[0].get('名称', code)) if spot_row is not None and len(spot_row) > 0 else code,
        'price': current,
        'ma': ma_info,
        'rsi_14': rsi_val,
        'macd': {
            'dif': round(float(dif.iloc[-1]), 4),
            'dea': round(float(dea.iloc[-1]), 4),
            'bar': round(float(macd_bar.iloc[-1]), 4),
        },
        'bollinger': {
            'upper': round(float(boll_u.iloc[-1]), 4),
            'mid': round(float(boll_m.iloc[-1]), 4),
            'lower': round(float(boll_l.iloc[-1]), 4),
        },
        'signal': calc_signal_v4(kline),
    }
    return {'data': result}
