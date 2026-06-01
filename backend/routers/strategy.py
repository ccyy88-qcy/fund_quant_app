"""自定义策略回测 API路由"""
from fastapi import APIRouter, Query
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import custom_backtest as cb
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/strategy', tags=['strategy'])


@router.get('/describe')
async def describe_strategies(strategy_type: Optional[str] = None):
    """策略说明和参数规则"""
    result = cb.describe_strategy(strategy_type)
    return {'data': result}


@router.get('/backtest')
async def custom_backtest(
    code: str = Query('562360', description='基金/ETF代码'),
    strategy: str = Query('ma_cross', description='策略类型'),
    params: str = Query('{}', description='JSON参数字符串'),
):
    """执行自定义策略回测"""
    import json
    try:
        params_dict = json.loads(params)
    except:
        params_dict = {}

    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}

    result = cb.run_custom_strategy(kline, strategy, params_dict)
    result['code'] = code
    return {'data': result}


@router.get('/optimize')
async def optimize_strategy(
    code: str = Query('562360', description='基金/ETF代码'),
    strategy: str = Query('ma_cross', description='策略类型'),
    objective: str = Query('sharpe', description='优化目标'),
):
    """参数网格优化"""
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}

    result = cb.optimize_params(kline, strategy, objective=objective)
    result['code'] = code
    return {'data': result}


@router.get('/comparison')
async def strategy_comparison(
    code: str = Query('562360', description='基金/ETF代码'),
):
    """多策略对比"""
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}

    strategies = ['ma_cross', 'rsi_threshold', 'bollinger', 'macd', 'price_volume']
    results = {}
    for s in strategies:
        try:
            r = cb.run_custom_strategy(kline, s)
            if 'metrics' in r:
                results[s] = {
                    'strategy': cb.describe_strategy(s).get('name', s),
                    'metrics': r['metrics'],
                }
        except:
            continue

    return {'data': {'code': code, 'strategies': results}}
