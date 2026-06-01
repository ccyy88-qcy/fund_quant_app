"""智能定投 API路由"""
from fastapi import APIRouter, Query
from typing import Optional
import sys, os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import dca_backtest as dca
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/dca', tags=['dca'])


@router.get('/strategies')
async def list_strategies():
    """定投策略说明"""
    return {'data': {
        'strategies': [
            {'id': 'fixed', 'name': '定期定额', 'desc': '每期固定金额买入'},
            {'id': 'ma_based', 'name': '均线定投', 'desc': '低于MA均线多买，高于少买'},
            {'id': 'valuation', 'name': '估值定投', 'desc': '低估值多买，高估值少买/卖出'},
            {'id': 'target_profit', 'name': '目标止盈', 'desc': '达到目标收益自动止盈'},
            {'id': 'trailing_stop', 'name': '移动止盈', 'desc': '从高点回落X%止盈'},
        ]
    }}


@router.get('/backtest')
async def dca_backtest(
    code: str = Query('562360', description='基金/ETF代码'),
    strategy: str = Query('fixed', description='定投策略'),
    amount: float = Query(1000, description='每期定投金额'),
    frequency: int = Query(20, description='定投频率(交易日间隔)'),
    years: int = Query(3, description='回测年数'),
    ma_period: int = Query(60, description='均线定投参数'),
    ma_multiplier: float = Query(0.5, description='均线定投倍数'),
    target_return: float = Query(20, description='目标止盈收益率%'),
    trailing_drawdown: float = Query(10, description='移动止盈回撤%'),
):
    """定投回测"""
    days = min(years * 250, 1500)
    kline = df.get_kline(code, days)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}

    result = {}
    if strategy == 'fixed':
        result = dca.dca_fixed_amount(kline, amount, frequency)
    elif strategy == 'ma_based':
        result = dca.dca_ma_strategy(kline, amount, frequency, ma_period, ma_multiplier)
    elif strategy == 'valuation':
        result = dca.dca_valuation_strategy(kline, amount, frequency, ma_period)
    elif strategy == 'target_profit':
        result = dca.dca_target_take_profit(kline, amount, frequency, target_return)
    elif strategy == 'trailing_stop':
        result = dca.dca_trailing_stop_profit(kline, amount, frequency, trailing_drawdown)
    else:
        return {'error': f'未知策略: {strategy}'}

    result['code'] = code
    result['strategy'] = strategy
    result['amount'] = amount
    result['frequency'] = frequency
    return {'data': result}


@router.get('/compare')
async def compare_strategies(
    code: str = Query('562360'),
    amount: float = Query(1000),
    frequency: int = Query(20),
    years: int = Query(3),
):
    """定投策略对比"""
    days = min(years * 250, 1500)
    kline = df.get_kline(code, days)
    if not kline:
        return {'error': '数据获取失败'}

    result = dca.compare_dca_strategies(kline, amount, frequency)
    result['code'] = code
    return {'data': result}
