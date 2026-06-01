"""行业轮动 API路由"""
from fastapi import APIRouter
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import sector_rotation as sr

router = APIRouter(prefix='/api/rotation', tags=['rotation'])


@router.get('/macro-cycle')
async def macro_cycle():
    """宏观周期定位"""
    import numpy as np
    np.random.seed(42)
    macro_data = {
        'pmi': round(np.random.normal(51, 2), 1),
        'cpi': round(np.random.normal(2.1, 0.5), 1),
        'ppi': round(np.random.normal(-0.5, 1), 1),
        'interest_rate': round(np.random.normal(3.1, 0.2), 2),
        'm2_growth': round(np.random.normal(8.5, 0.5), 1),
        'gdp_growth': round(np.random.normal(5.0, 0.3), 1),
    }
    result = sr.macro_cycle_position(macro_data)
    return {'data': result}


@router.get('/sector-scores')
async def sector_scores():
    """行业评分排行"""
    import numpy as np
    np.random.seed(42)
    sectors = ['银行', '非银金融', '房地产', '食品饮料', '医药生物',
               '电子', '计算机', '电力设备', '机械设备', '汽车',
               '化工', '有色金属', '煤炭', '钢铁', '建筑装饰',
               '交通运输', '农林牧渔', '商贸零售', '传媒', '通信',
               '公用事业', '环保', '国防军工', '综合']
    sector_data = []
    for s in sectors:
        sector_data.append({
            'name': s,
            'price_momentum': round(np.random.normal(5, 10), 2),
            'capital_flow': round(np.random.normal(0, 5), 2),
            'capital_flow_5d': round(np.random.normal(0, 15), 2),
            'pe_percentile': round(np.random.uniform(10, 90), 1),
            'pb_percentile': round(np.random.uniform(10, 90), 1),
            'revenue_growth': round(np.random.normal(8, 10), 1),
            'profit_growth': round(np.random.normal(5, 15), 1),
        })
    result = sr.sector_score(sector_data)
    return {'data': result}


@router.get('/rotation-signals')
async def rotation_signals(top_n: int = 5):
    """轮动信号"""
    import numpy as np
    np.random.seed(42)
    sectors = ['科技', '消费', '金融', '医疗', '能源', '制造', '材料', '地产']
    scores = []
    for i, s in enumerate(sectors):
        scores.append({
            'name': s,
            'total_score': round(np.random.uniform(30, 80), 2),
            'momentum_score': round(np.random.uniform(20, 80), 2),
            'capital_flow_score': round(np.random.uniform(20, 80), 2),
            'valuation_score': round(np.random.uniform(20, 80), 2),
            'macro_score': round(np.random.uniform(20, 80), 2),
        })
    scores.sort(key=lambda x: x['total_score'], reverse=True)
    result = sr.rotation_signal(scores, top_n)
    return {'data': result}


@router.get('/rotation-backtest')
async def rotation_backtest():
    """轮动回测"""
    import numpy as np
    np.random.seed(42)
    dates = []
    for i in range(100):
        from datetime import datetime, timedelta
        d = (datetime.now() - timedelta(days=200-i*2)).strftime('%Y-%m-%d')
        dates.append(d)
    sectors_history = []
    for s in ['科技', '消费', '金融', '医疗', '能源']:
        for d in dates:
            sectors_history.append({
                'name': s,
                'date': d,
                'return': round(np.random.normal(0.5, 3), 2),
            })
    result = sr.rotation_backtest(sectors_history, interval=20)
    return {'data': result}
