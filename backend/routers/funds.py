"""基金相关API路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import data_fetcher as df
from quant_engine import indicators as ind
from quant_engine import signals as sig

router = APIRouter(prefix='/api/funds', tags=['funds'])


@router.get('/search')
async def search_funds(keyword: str = '', limit: int = 20):
    """搜索基金"""
    results = df.search_funds(keyword, limit)
    return {'data': results}


@router.get('/{code}/info')
async def fund_info(code: str):
    """基金基本信息"""
    info = df.get_fund_info(code)
    return {'data': info}


@router.get('/{code}/kline')
async def fund_kline(code: str, days: int = 500):
    """基金K线数据"""
    kline = df.get_kline(code, days)
    return {'data': kline}


@router.get('/{code}/indicators')
async def fund_indicators(code: str, days: int = 500):
    """全部技术指标"""
    kline = df.get_kline(code, days)
    if not kline:
        raise HTTPException(404, '数据获取失败')

    import pandas as pd
    kdf = pd.DataFrame(kline)
    kdf.columns = [c if c != 'day' else 'date' for c in kdf.columns]

    # 计算指标
    indicators = ind.calc_all_indicators(kdf.rename(columns={'date': 'day'}))
    patterns = ind.get_latest_kline_patterns(kline)

    return {
        'data': {
            'kline': kline,
            'indicators': {
                k: [None if pd.isna(v) or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else round(float(v), 4) for v in vals]
                for k, vals in indicators.items()
            },
            'latest_patterns': patterns,
        }
    }


@router.get('/{code}/signal')
async def fund_signal(code: str, pe_pct: Optional[float] = None,
                      pb_pct: Optional[float] = None):
    """信号判定"""
    kline = df.get_kline(code, 500)
    if not kline:
        raise HTTPException(404, f'基金{code}数据获取失败')

    info = df.get_fund_info(code)
    is_fund = any(t in info.get('type', '') for t in ['混合', '偏股', '指数'])

    signal = sig.calc_signal_v4(kline, pe_pct, pb_pct, is_fund)
    return {'data': signal}


@router.get('/{code}/backtest')
async def fund_backtest(code: str, pe_pct_history: Optional[str] = None):
    """历史回测"""
    kline = df.get_kline(code, 500)
    if not kline:
        raise HTTPException(404, f'基金{code}数据获取失败')

    result = sig.run_backtest(kline)
    return {'data': result}


@router.post('/watchlist')
async def set_watchlist(codes: List[str]):
    """设置自选列表"""
    import json, os
    path = df.CACHE_DIR + '/watchlist.json'
    with open(path, 'w') as f:
        json.dump(codes, f)
    return {'data': 'ok'}


@router.get('/watchlist')
async def get_watchlist():
    """获取自选列表"""
    import json, os
    path = df.CACHE_DIR + '/watchlist.json'
    if os.path.exists(path):
        return {'data': json.loads(open(path).read())}
    return {'data': []}


@router.get('/watchlist/realtime')
async def watchlist_realtime():
    """自选基金实时估值"""
    import json, os
    path = df.CACHE_DIR + '/watchlist.json'
    if not os.path.exists(path):
        return {'data': []}
    codes = json.loads(open(path).read())
    results = df.get_realtime_estimation(codes)
    return {'data': results}
