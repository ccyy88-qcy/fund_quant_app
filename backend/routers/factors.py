"""多因子选股 API路由"""
from fastapi import APIRouter, Query
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import factor_model as fm

router = APIRouter(prefix='/api/factors', tags=['factors'])


@router.get('/describe')
async def describe_factors():
    """因子说明"""
    return {'data': fm.describe_strategy() if hasattr(fm, 'describe_strategy') else {
        'factors': [
            {'name': 'PE因子', 'type': '估值', 'direction': '负向'},
            {'name': 'PB因子', 'type': '估值', 'direction': '负向'},
            {'name': 'PS因子', 'type': '估值', 'direction': '负向'},
            {'name': '营收增长', 'type': '成长', 'direction': '正向'},
            {'name': '利润增速', 'type': '成长', 'direction': '正向'},
            {'name': 'ROE', 'type': '质量', 'direction': '正向'},
            {'name': 'ROA', 'type': '质量', 'direction': '正向'},
            {'name': '动量1月', 'type': '动量', 'direction': '正向'},
            {'name': '动量3月', 'type': '动量', 'direction': '正向'},
            {'name': '动量6月', 'type': '动量', 'direction': '正向'},
            {'name': '动量12月', 'type': '动量', 'direction': '正向'},
            {'name': '流通市值', 'type': '规模', 'direction': '负向'},
        ]
    }}


@router.get('/analysis')
async def factor_analysis():
    """完整因子分析（模拟数据）"""
    # 生成模拟因子数据
    import numpy as np
    n = 200
    np.random.seed(42)
    stock_data = []
    for i in range(n):
        f = {  # 12个因子
            'code': f'{600000+i:06d}',
            'pe': round(abs(np.random.normal(25, 15)), 2),
            'pb': round(abs(np.random.normal(2.5, 1.5)), 2),
            'ps': round(abs(np.random.normal(3, 2)), 2),
            'revenue_growth': round(np.random.normal(15, 10), 2),
            'profit_growth': round(np.random.normal(12, 15), 2),
            'roe': round(abs(np.random.normal(12, 8)), 2),
            'roa': round(abs(np.random.normal(5, 3)), 2),
            'momentum_1m': round(np.random.normal(2, 8), 2),
            'momentum_3m': round(np.random.normal(5, 12), 2),
            'momentum_6m': round(np.random.normal(8, 18), 2),
            'momentum_12m': round(np.random.normal(15, 25), 2),
            'market_cap': round(abs(np.random.lognormal(15, 1)), 2),
        }
        # 未来收益（与因子有一定相关性）
        future_ret = (f['pe'] * -0.05 + f['roe'] * 0.3 + f['profit_growth'] * 0.2
                      + f['momentum_6m'] * 0.1 + np.random.normal(0, 5))
        f['forward_return'] = round(future_ret, 2)
        stock_data.append(f)

    result = {}
    try:
        result['factors'] = fm.calc_factor_returns(stock_data)
        result['ic_analysis'] = fm.factor_ic_analysis(stock_data, [s['forward_return'] for s in stock_data])
        result['layer_backtest'] = fm.factor_layer_backtest(
            [s.get('pe', 0) for s in stock_data],
            [s['forward_return'] for s in stock_data]
        )
        corr = fm.factor_correlation_matrix(stock_data)
        if isinstance(corr, dict) and 'correlation_matrix' in corr:
            result['correlation'] = corr
        else:
            result['correlation'] = {'correlation_matrix': corr}
        result['composite'] = fm.composite_factor(stock_data)
    except Exception as e:
        result = {'error': str(e), 'stock_count': len(stock_data)}

    return {'data': result}


@router.get('/ic-history')
async def factor_ic_history():
    """因子IC历史序列（模拟）"""
    import numpy as np
    np.random.seed(42)
    factors = ['PE', 'PB', 'ROE', '营收增长', '动量3月', '动量6月']
    dates = []
    ic_data = {}
    from datetime import datetime, timedelta
    base = datetime.now() - timedelta(days=500)
    for i in range(60):
        d = (base + timedelta(days=i*8)).strftime('%Y-%m-%d')
        dates.append(d)
        for f in factors:
            if f not in ic_data:
                ic_data[f] = []
            ic_data[f].append(round(np.random.normal(0.05, 0.08), 4))

    return {'data': {'dates': dates, 'ic_series': ic_data}}


@router.get('/layer-backtest')
async def layer_backtest(factor_name: str = 'PE', layers: int = 5):
    """因子分层回测"""
    import numpy as np
    np.random.seed(42)
    vals = np.random.normal(20, 10, 200)
    fwd_rets = np.array([v * -0.08 + np.random.normal(2, 5) for v in vals])
    try:
        result = fm.factor_layer_backtest(vals.tolist(), fwd_rets.tolist(), layers)
    except Exception as e:
        result = {'error': str(e)}
    return {'data': {'factor_name': factor_name, **result}}
