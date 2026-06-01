"""持有期分析 API路由"""
from fastapi import APIRouter, Query
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import holding_analysis as ha
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/holding', tags=['holding'])


@router.get('/analysis')
async def holding_analysis(code: str = Query('562360', description='基金/ETF代码')):
    """持有期收益分析"""
    kline = df.get_kline(code, 1000)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}
    result = ha.calc_holding_period_analysis(kline)
    result['code'] = code

    info = df.get_fund_info(code)
    result['name'] = info.get('name', code)
    return {'data': result}


@router.get('/compare')
async def holding_compare(code: str = Query('562360')):
    """持有策略对比（不动 vs 定投 vs 择时）"""
    kline = df.get_kline(code, 1000)
    if not kline:
        return {'error': '数据获取失败'}
    result = ha.compare_holding_strategies(kline)
    result['code'] = code
    return {'data': result}
