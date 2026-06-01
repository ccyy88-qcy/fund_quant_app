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
    raw_kline = df.get_kline(code, 500)
    if not raw_kline:
        return {'error': f'基金{code}数据获取失败'}

    # 转list→DataFrame
    import pandas as pd
    kdf = pd.DataFrame(raw_kline)
    if 'close' not in kdf.columns:
        return {'error': 'K线数据缺少close字段'}

    info = df.get_fund_info(code)
    report = sa.generate_full_report(
        df=kdf,
        pe_percentile=pe_pct,
        pb_percentile=pb_pct,
    )
    # 展平report嵌套结构，App直接读取顶层字段
    flat = report.get('report', report)
    
    # Flutter App期望的字段名映射
    flat['technical_score'] = flat.get('technical_analysis', {})
    flat['valuation_score'] = flat.get('valuation_analysis', {})
    flat['momentum_score'] = flat.get('momentum_analysis', {}).get('momentum_score', 50)
    risk = flat.get('risk_analysis', {})
    if isinstance(risk, dict) and 'score' not in risk and 'risk_score' in risk:
        risk['score'] = risk['risk_score']
    flat['risk_score'] = risk
    # Flutter advice字段映射
    advice = flat.get('investment_advice', {})
    if isinstance(advice, dict) and 'direction' not in advice and 'action' in advice:
        advice['direction'] = advice['action']

    flat['code'] = code
    flat['name'] = info.get('name', code)
    return {'data': flat}


@router.get('/technical')
async def technical_analysis(code: str = Query('562360')):
    """技术面评分"""
    raw_kline = df.get_kline(code, 500)
    if not raw_kline:
        return {'error': '数据获取失败'}
    import pandas as pd
    kdf = pd.DataFrame(raw_kline)
    score = sa.calc_technical_score(kdf)
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
    raw_kline = df.get_kline(code, 500)
    if not raw_kline:
        return {'error': '数据获取失败'}
    import pandas as pd
    kdf = pd.DataFrame(raw_kline)
    rating = sa.calc_comprehensive_rating(kdf, pe_pct, pb_pct)
    return {'data': {'code': code, **rating}}


@router.get('/advice')
async def investment_advice(code: str = Query('562360'),
                             pe_pct: Optional[float] = None,
                             pb_pct: Optional[float] = None):
    """投资建议"""
    raw_kline = df.get_kline(code, 500)
    if not raw_kline:
        return {'error': '数据获取失败'}
    import pandas as pd
    kdf = pd.DataFrame(raw_kline)
    rating = sa.calc_comprehensive_rating(kdf, pe_pct, pb_pct)
    advice = sa.calc_investment_advice(rating)
    return {'data': {'code': code, **advice}}
