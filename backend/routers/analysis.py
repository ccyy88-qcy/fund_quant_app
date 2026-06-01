"""AI智能分析 API路由"""
from fastapi import APIRouter, Query
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import smart_analysis as sa
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/analysis', tags=['analysis'])


@router.get('/report')
async def full_report(code: str = Query('562360', description='基金/ETF代码'),
                      pe_pct: Optional[float] = Query(None, description='PE分位'),
                      pb_pct: Optional[float] = Query(None, description='PB分位')):
    """一键基金分析报告"""
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}

    info = df.get_fund_info(code)
    result = sa.generate_full_report(
        kline_data=kline,
        fund_info=info,
        pe_pct=pe_pct,
        pb_pct=pb_pct,
    )
    result['code'] = code
    result['name'] = info.get('name', code)
    return {'data': result}


@router.get('/technical')
async def technical_analysis(code: str = Query('562360')):
    """技术面评分"""
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': '数据获取失败'}
    score = sa.calc_technical_score(kline)
    return {'data': {'code': code, **score}}


@router.get('/valuation')
async def valuation_analysis(code: str = Query('562360'),
                              pe_pct: Optional[float] = None,
                              pb_pct: Optional[float] = None):
    """估值评分"""
    if pe_pct is None and pb_pct is None:
        return {'data': {'code': code, 'score': 50, 'rating': 'N/A', 'detail': '请提供PE/PB分位'}}
    score = sa.calc_valuation_score(pe_pct, pb_pct)
    return {'data': {'code': code, **score}}


@router.get('/rating')
async def comprehensive_rating(code: str = Query('562360'),
                                pe_pct: Optional[float] = None,
                                pb_pct: Optional[float] = None):
    """综合评级"""
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': '数据获取失败'}
    rating = sa.calc_comprehensive_rating(kline, pe_pct, pb_pct)
    return {'data': {'code': code, **rating}}


@router.get('/advice')
async def investment_advice(code: str = Query('562360'),
                             pe_pct: Optional[float] = None,
                             pb_pct: Optional[float] = None):
    """投资建议"""
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': '数据获取失败'}
    rating = sa.calc_comprehensive_rating(kline, pe_pct, pb_pct)
    advice = sa.calc_investment_advice(rating)
    return {'data': {'code': code, **advice}}
