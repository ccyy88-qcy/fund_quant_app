"""风险分析 API路由"""
from fastapi import APIRouter, Query
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import risk_metrics as rm

router = APIRouter(prefix='/api/risk', tags=['risk'])


@router.get('/analysis')
async def risk_analysis(code: str = Query('562360', description='基金/ETF代码')):
    """全面风险分析"""
    from quant_engine import data_fetcher as df
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': f'基金{code}数据获取失败'}

    import pandas as pd
    import numpy as np
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
    dates = [d['day'] for d in kline if float(d.get('close', 0)) > 0]

    if len(closes) < 20:
        return {'error': '数据不足'}

    # 基础风险指标
    base_metrics = rm.calc_risk_metrics(closes)

    # VaR计算
    returns = closes.pct_change().dropna() * 100
    var_95 = round(float(np.percentile(returns, 5)), 4)
    var_99 = round(float(np.percentile(returns, 1)), 4)
    cvar_95 = round(float(returns[returns <= var_95].mean()), 4)

    # 回撤分析
    peak = closes.expanding().max()
    dd = ((closes - peak) / peak * 100).tolist()
    dd_series = pd.Series(dd)
    max_dd_idx = int(dd_series.idxmin()) if len(dd_series) > 0 else 0
    max_dd_date = dates[max_dd_idx] if max_dd_idx < len(dates) else ''

    # 回撤区间
    dd_regions = []
    in_dd = False
    dd_start = 0
    for i in range(len(dd)):
        if dd[i] < -5 and not in_dd:
            in_dd = True
            dd_start = i
        elif (dd[i] >= -2 or i == len(dd)-1) and in_dd:
            if i - dd_start >= 5:
                dd_regions.append({
                    'start_date': dates[dd_start] if dd_start < len(dates) else '',
                    'end_date': dates[i] if i < len(dates) else '',
                    'max_dd': round(min(dd[dd_start:i+1]), 2),
                    'duration_days': i - dd_start,
                })
            in_dd = False

    # 下行风险
    downside = returns[returns < 0]
    downside_vol = round(float(downside.std() * np.sqrt(250)), 4) if len(downside) > 1 else 0
    sortino = round((base_metrics.get('annual_return', 0) - 2.5) / downside_vol, 2) if downside_vol > 0 else 0
    calmar = round(base_metrics.get('annual_return', 0) / abs(base_metrics.get('max_drawdown', 1)), 2) if base_metrics.get('max_drawdown', 0) != 0 else 0

    # 尾部风险（极端亏损次数）
    extreme_losses = returns[returns < -3]
    extreme_count = len(extreme_losses)
    extreme_freq = round(extreme_count / len(returns) * 100, 2) if len(returns) > 0 else 0

    return {
        'data': {
            'code': code,
            'basic_metrics': base_metrics,
            'var_analysis': {
                'var_95': var_95,
                'var_99': var_99,
                'cvar_95': cvar_95,
                'sortino': sortino,
                'calmar': calmar,
            },
            'drawdown_analysis': {
                'max_dd_date': max_dd_date,
                'dd_series': [round(v, 4) for v in dd[-100:]],
                'dd_regions': dd_regions[:5],
            },
            'tail_risk': {
                'extreme_loss_count': extreme_count,
                'extreme_loss_freq_pct': extreme_freq,
                'downside_vol': downside_vol,
            },
        }
    }


@router.get('/var')
async def var_analysis(code: str = Query('562360'), confidence: float = 0.95):
    """VaR/CVaR分析"""
    from quant_engine import data_fetcher as df
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': '数据获取失败'}

    import pandas as pd
    import numpy as np
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
    returns = closes.pct_change().dropna() * 100
    ret_arr = returns.values

    # 多种VaR方法
    var_hist = round(float(np.percentile(ret_arr, (1 - confidence) * 100)), 4)
    cvar = round(float(ret_arr[ret_arr <= var_hist].mean()), 4)

    # 参数法
    mu = np.mean(ret_arr)
    sigma = np.std(ret_arr)
    from scipy.stats import norm
    var_param = round(float(mu + sigma * norm.ppf(1 - confidence)), 4)

    return {
        'data': {
            'code': code,
            'confidence': confidence,
            'historical_var': var_hist,
            'historical_cvar': cvar,
            'parametric_var': var_param,
            'daily_vol': round(sigma, 4),
        }
    }


@router.get('/stress-test')
async def stress_test(code: str = Query('562360')):
    """压力测试"""
    from quant_engine import data_fetcher as df
    kline = df.get_kline(code, 500)
    if not kline:
        return {'error': '数据获取失败'}

    import pandas as pd
    import numpy as np
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
    current = float(closes.iloc[-1])

    scenarios = [
        {'name': '市场暴跌', 'shock': -10, 'desc': '单日暴跌10%'},
        {'name': '持续下跌', 'shock': -20, 'desc': '持续下跌20%'},
        {'name': '温和下跌', 'shock': -5, 'desc': '下跌5%'},
        {'name': '牛市回调', 'shock': -3, 'desc': '回调3%'},
        {'name': '小幅波动', 'shock': -1, 'desc': '波动1%'},
    ]

    results = []
    for s in scenarios:
        pct = s['shock']
        target = round(current * (1 + pct / 100), 4)
        results.append({
            'scenario': s['name'],
            'description': s['desc'],
            'shock_pct': pct,
            'current_price': round(current, 4),
            'target_price': target,
            'loss_amount': round(target - current, 4),
        })

    return {'data': {'code': code, 'current_price': round(current, 4), 'scenarios': results}}
