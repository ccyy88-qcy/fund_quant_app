"""资产配置/组合优化 API路由"""
from fastapi import APIRouter, Query
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import portfolio_optimizer as po

router = APIRouter(prefix='/api/portfolio', tags=['portfolio'])


@router.get('/efficient-frontier')
async def efficient_frontier(n_assets: int = 5, risk_free: float = 2.5):
    """有效前沿 + MVP + 最大夏普"""
    import numpy as np
    np.random.seed(42)
    n = min(n_assets, 10)
    means = np.random.uniform(5, 20, n)
    cov = np.random.uniform(-0.3, 0.8, (n, n))
    cov = (cov + cov.T) / 2
    cov[np.diag_indices_from(cov)] = np.random.uniform(200, 600, n)

    try:
        ef = po.efficient_frontier(means, cov, n_points=50)
        mvp = po.min_variance_portfolio(means, cov)
        msr = po.max_sharpe_portfolio(means, cov, risk_free)
        rp = po.risk_parity_portfolio(cov)
        mvp_stats = po.portfolio_stats(means, cov, mvp['weights'], risk_free)
        msr_stats = po.portfolio_stats(means, cov, msr['weights'], risk_free)
        rp_stats = po.portfolio_stats(means, cov, rp['weights'], risk_free)
    except Exception as e:
        return {'error': str(e)}

    return {
        'data': {
            'efficient_frontier': ef,
            'min_variance': {**mvp, **mvp_stats},
            'max_sharpe': {**msr, **msr_stats},
            'risk_parity': {**rp, **rp_stats},
            'asset_labels': [f'资产{i+1}' for i in range(n)],
        }
    }


@router.get('/optimize')
async def optimize_portfolio(
    objective: str = Query('max_sharpe', description='max_sharpe/min_variance/risk_parity'),
    n_assets: int = 5,
    risk_free: float = 2.5,
):
    """组合优化"""
    import numpy as np
    np.random.seed(42)
    n = min(n_assets, 10)
    means = np.random.uniform(5, 20, n)
    cov = np.random.uniform(-0.3, 0.8, (n, n))
    cov = (cov + cov.T) / 2
    cov[np.diag_indices_from(cov)] = np.random.uniform(200, 600, n)

    try:
        if objective == 'min_variance':
            result = po.min_variance_portfolio(means, cov)
        elif objective == 'risk_parity':
            result = po.risk_parity_portfolio(cov)
        else:
            result = po.max_sharpe_portfolio(means, cov, risk_free)
        stats = po.portfolio_stats(means, cov, result['weights'], risk_free)
    except Exception as e:
        return {'error': str(e)}

    return {
        'data': {
            'objective': objective,
            **result,
            **stats,
            'asset_labels': [f'资产{i+1}' for i in range(n)],
        }
    }


@router.get('/stats')
async def portfolio_stats_endpoint(weights: str = '', returns: str = ''):
    """组合统计指标"""
    import numpy as np
    np.random.seed(42)
    n = 5
    means = np.random.uniform(5, 20, n)
    cov = np.random.uniform(-0.3, 0.8, (n, n))
    cov = (cov + cov.T) / 2
    cov[np.diag_indices_from(cov)] = np.random.uniform(200, 600, n)
    weights = np.ones(n) / n
    stats = po.portfolio_stats(means, cov, weights, 2.5)
    return {'data': stats}
