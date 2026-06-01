"""市场情绪 + 建仓提醒 API路由"""
from fastapi import APIRouter, Query
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import market_sentiment as ms
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/sentiment', tags=['sentiment'])


@router.get('/')
async def market_sentiment():
    """市场情绪综合指数"""
    result = ms.calc_market_sentiment()
    return {'data': result}


@router.get('/advance-decline')
async def advance_decline():
    """涨跌家数"""
    result = ms.calc_advance_decline()
    return {'data': result}


@router.get('/volume')
async def volume_analysis():
    """成交量分析"""
    result = ms.calc_volume_analysis()
    return {'data': result}


@router.get('/build-signal')
async def build_signal(
    code: str = Query('562360', description='基金/ETF代码'),
    pe_pct: Optional[float] = Query(None),
    pb_pct: Optional[float] = Query(None),
):
    """建仓提醒信号"""
    kline = df.get_kline(code, 500) if code else None
    sentiment = ms.calc_market_sentiment()
    result = ms.calc_build_signal(kline, pe_pct, pb_pct, sentiment)
    info = df.get_fund_info(code) if code else {}
    result['code'] = code
    result['fund_name'] = info.get('name', code)
    return {'data': result}


@router.get('/fund-ranks')
async def fund_ranks():
    """基金评分排名"""
    result = ms.score_funds(None)
    return {'data': result}
