"""
资产配置/组合优化模块
- 马科维茨有效前沿 (均值-方差优化)
- 最小方差组合 (MVP)
- 最大夏普组合
- 风险平价模型 (等风险贡献)
- 约束：个股权重上下限、行业集中度
- 有效前沿曲线点集
"""
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Union, Tuple


def _mean_var_weights(
    cov: np.ndarray,
    target_return: Optional[float] = None,
    lb: float = 0.0,
    ub: float = 1.0,
    sector_map: Optional[Dict[str, List[int]]] = None,
    sector_limit: Optional[float] = None
) -> np.ndarray:
    """
    均值-方差优化：解析求解 (无scipy时使用)。
    用拉格朗日乘子法求给定目标收益下的最优权重。
    min 0.5 * w' @ cov @ w  s.t. w'@mu = target_return, sum(w) = 1, lb<=w<=ub
    解析解适用于无不等式约束的情况，有上下界约束时我们用迭代投影法。
    这里实现一个简化版的带约束求解器。
    """
    n = cov.shape[0]
    # 如果无约束，用解析解
    if lb <= 0 and ub >= 1 and sector_map is None and target_return is not None:
        return _analytic_mean_var(cov, np.ones(n) * (target_return / n), target_return)
    # 带约束用迭代的坐标下降法 (SMO-like)
    w = np.ones(n) / n
    for _ in range(1000):
        grad = cov @ w
        # 梯度下降 + 投影
        step = 0.01
        w_new = w - step * grad
        # 投影到可行域
        w_new = np.clip(w_new, lb, ub)
        # 归一化到 sum=1
        w_new = w_new / w_new.sum()
        if np.max(np.abs(w_new - w)) < 1e-8:
            break
        w = w_new
    return w


def _analytic_mean_var(cov: np.ndarray, mu: np.ndarray, target_return: float) -> np.ndarray:
    """解析求解均值-方差 (无约束)"""
    n = cov.shape[0]
    ones = np.ones(n)
    inv_cov = np.linalg.inv(cov)
    A = ones.T @ inv_cov @ ones
    B = mu.T @ inv_cov @ ones
    C = mu.T @ inv_cov @ mu
    D = A * C - B ** 2
    if abs(D) < 1e-12:
        return ones / n
    lam = (C - B * target_return) / D
    gamma = (A * target_return - B) / D
    w = inv_cov @ (lam * ones + gamma * mu)
    return w / w.sum()


def min_variance_portfolio(
    returns: np.ndarray,
    cov: Optional[np.ndarray] = None,
    lb: float = 0.0,
    ub: float = 1.0,
    sector_map: Optional[Dict[str, List[int]]] = None,
    sector_limit: Optional[float] = None
) -> dict:
    """
    最小方差组合 (MVP)
    参数:
        returns: (n_assets, n_periods) 收益率矩阵 或 (n_assets,) 均值向量
        cov: 协方差矩阵 (n_assets, n_assets), 如None则从returns计算
        lb: 个股权重下限
        ub: 个股权重上限
        sector_map: {行业名: [资产索引列表], ...}
        sector_limit: 行业集中度上限 (单个行业最大权重)
    返回:
        dict: {weights, variance, volatility, annual_return}
    """
    if isinstance(returns, pd.DataFrame):
        returns = returns.values
    if cov is None:
        cov = np.cov(returns, ddof=1)
    n = cov.shape[0]
    # 最小方差解析解: w = inv(cov) @ 1 / (1' @ inv(cov) @ 1)
    ones = np.ones(n)
    try:
        inv_cov = np.linalg.inv(cov)
        w = inv_cov @ ones
        w = w / w.sum()
    except np.linalg.LinAlgError:
        w = np.ones(n) / n
    # 应用约束
    w = _apply_constraints(w, lb, ub, sector_map, sector_limit)
    var = w.T @ cov @ w
    vol = np.sqrt(var)
    ret = _calc_annual_return(returns, w)
    return {
        'weights': {str(i): round(float(w[i]), 4) for i in range(n)},
        'weights_list': [round(float(x), 4) for x in w],
        'variance': round(float(var), 4),
        'volatility': round(float(vol), 4),
        'annual_return': round(float(ret), 4)
    }


def max_sharpe_portfolio(
    returns: np.ndarray,
    cov: Optional[np.ndarray] = None,
    risk_free_rate: float = 0.02,
    lb: float = 0.0,
    ub: float = 1.0,
    sector_map: Optional[Dict[str, List[int]]] = None,
    sector_limit: Optional[float] = None
) -> dict:
    """
    最大夏普比率组合
    参数:
        returns: (n_assets, n_periods) 或 (n_assets,) 均值向量
        cov: 协方差矩阵
        risk_free_rate: 无风险利率 (年化)
        lb/ub: 权重约束
    返回:
        dict
    """
    if isinstance(returns, pd.DataFrame):
        returns = returns.values
    if cov is None:
        cov = np.cov(returns, ddof=1)
    n = cov.shape[0]
    # 估计期望收益
    if returns.ndim == 2:
        mu = np.mean(returns, axis=1) * 252
    else:
        mu = returns
    # 最大夏普解析解: w = inv(cov) @ (mu - rf)
    ex_ret = mu - risk_free_rate
    try:
        inv_cov = np.linalg.inv(cov)
        w = inv_cov @ ex_ret
        if w.sum() != 0:
            w = w / w.sum()
        else:
            w = np.ones(n) / n
    except np.linalg.LinAlgError:
        w = np.ones(n) / n
    w = _apply_constraints(w, lb, ub, sector_map, sector_limit)
    var = w.T @ cov @ w
    vol = np.sqrt(var)
    ret = _calc_annual_return(returns, w)
    sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0.0
    return {
        'weights': {str(i): round(float(w[i]), 4) for i in range(n)},
        'weights_list': [round(float(x), 4) for x in w],
        'variance': round(float(var), 4),
        'volatility': round(float(vol), 4),
        'annual_return': round(float(ret), 4),
        'sharpe_ratio': round(float(sharpe), 4)
    }


def _calc_annual_return(returns: np.ndarray, weights: np.ndarray) -> float:
    """计算年化收益"""
    if returns.ndim == 2:
        mu = np.mean(returns, axis=1) * 252
    else:
        mu = returns
    return float(mu @ weights)


def _apply_constraints(
    w: np.ndarray,
    lb: float,
    ub: float,
    sector_map: Optional[Dict[str, List[int]]] = None,
    sector_limit: Optional[float] = None
) -> np.ndarray:
    """应用约束的迭代投影算法"""
    n = len(w)
    w = w.copy()
    # 个股权重约束
    w = np.clip(w, lb, ub)
    # 行业集中度约束
    if sector_map is not None and sector_limit is not None:
        for _ in range(200):
            changed = False
            for sector, indices in sector_map.items():
                s_w = w[indices].sum()
                if s_w > sector_limit:
                    # 按比例压缩
                    scale = sector_limit / s_w
                    w[indices] *= scale
                    changed = True
            # 重新归一化
            w = w / w.sum()
            if not changed:
                break
    else:
        w = w / w.sum()
    return w


def risk_parity_portfolio(
    cov: np.ndarray,
    lb: float = 0.0,
    ub: float = 1.0
) -> dict:
    """
    风险平价模型 (等风险贡献)
    使用迭代方法求解，使各资产对组合风险的贡献相等。
    参数:
        cov: 协方差矩阵 (n_assets, n_assets)
        lb/ub: 权重约束
    返回:
        dict
    """
    n = cov.shape[0]
    w = np.ones(n) / n
    # 迭代求解
    iteration = 0
    for iteration in range(5000):
        sigma = np.sqrt(w.T @ cov @ w)
        if sigma < 1e-12:
            break
        mrc = (cov @ w) / sigma  # 边际风险贡献
        rc = w * mrc  # 风险贡献
        target_rc = sigma / n
        # 更新权重
        w_new = w * (target_rc / np.maximum(rc, 1e-12))
        w_new = np.clip(w_new, lb, ub)
        w_new = w_new / w_new.sum()
        if np.max(np.abs(w_new - w)) < 1e-8:
            break
        w = w_new
    var = w.T @ cov @ w
    vol = np.sqrt(var)
    rc_final = w * (cov @ w) / vol
    return {
        'weights': {str(i): round(float(w[i]), 4) for i in range(n)},
        'weights_list': [round(float(x), 4) for x in w],
        'variance': round(float(var), 4),
        'volatility': round(float(vol), 4),
        'risk_contributions': [round(float(x / vol), 4) for x in rc_final],
        'iterations': iteration + 1
    }


def efficient_frontier(
    returns: np.ndarray,
    cov: Optional[np.ndarray] = None,
    n_points: int = 50,
    risk_free_rate: float = 0.02,
    lb: float = 0.0,
    ub: float = 1.0,
    sector_map: Optional[Dict[str, List[int]]] = None,
    sector_limit: Optional[float] = None
) -> dict:
    """
    有效前沿曲线点集 (用于前端绘图)
    参数:
        returns: (n_assets, n_periods) 或 (n_assets,) 均值向量
        cov: 协方差矩阵
        n_points: 前沿上点的数量
        risk_free_rate: 无风险利率
        lb/ub: 权重约束
    返回:
        dict: {
            frontier: [{volatility, return, sharpe, weights}, ...],
            mvp: {最小方差组合},
            max_sharpe: {最大夏普组合},
            tangency: {切点组合}
        }
    """
    if isinstance(returns, pd.DataFrame):
        returns = returns.values
    if cov is None and returns.ndim == 2:
        cov = np.cov(returns, ddof=1)
    elif cov is None:
        raise ValueError("cov required when returns is 1D")
    n = cov.shape[0]
    if returns.ndim == 2:
        mu = np.mean(returns, axis=1) * 252
    else:
        mu = returns
    # 计算MVP
    mvp = min_variance_portfolio(returns, cov, lb, ub, sector_map, sector_limit)
    mvp_vol = mvp['volatility']
    mvp_ret = mvp['annual_return']
    # 计算最大夏普
    ms = max_sharpe_portfolio(returns, cov, risk_free_rate, lb, ub, sector_map, sector_limit)
    ms_vol = ms['volatility']
    ms_ret = ms['annual_return']
    # 生成有效前沿上的点
    # 方法：在MVP收益和最大收益之间等分，求解每个收益率水平的最优权重
    max_asset_ret = mu.max()
    ret_range = np.linspace(mvp_ret, max_asset_ret * 1.2, n_points)
    frontier = []
    ones = np.ones(n)
    try:
        inv_cov = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        inv_cov = np.linalg.pinv(cov)
    for target_ret in ret_range:
        try:
            # 解析解：给定目标收益，最小化方差
            A = ones.T @ inv_cov @ ones
            B = mu.T @ inv_cov @ ones
            C = mu.T @ inv_cov @ mu
            D = A * C - B ** 2
            if abs(D) < 1e-12:
                continue
            lam = (C - B * target_ret) / D
            gamma = (A * target_ret - B) / D
            w = inv_cov @ (lam * ones + gamma * mu)
            w = w / w.sum()
            # 应用约束
            w = _apply_constraints(w, lb, ub, sector_map, sector_limit)
            vol = float(np.sqrt(w.T @ cov @ w))
            ret = float(mu @ w)
            sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0.0
            frontier.append({
                'volatility': round(vol, 4),
                'return': round(ret, 4),
                'sharpe_ratio': round(sharpe, 4),
                'weights': [round(float(x), 4) for x in w]
            })
        except Exception:
            continue
    # 按波动率排序
    frontier.sort(key=lambda x: x['volatility'])
    return {
        'frontier': frontier,
        'mvp': {
            'volatility': mvp_vol,
            'return': mvp_ret,
            'weights': mvp['weights_list']
        },
        'max_sharpe': {
            'volatility': ms_vol,
            'return': ms_ret,
            'sharpe_ratio': ms['sharpe_ratio'],
            'weights': ms['weights_list']
        },
        'parameters': {
            'n_assets': n,
            'risk_free_rate': risk_free_rate,
            'lb': lb,
            'ub': ub,
            'n_points': n_points
        }
    }


def portfolio_stats(
    weights: List[float],
    returns: np.ndarray,
    cov: Optional[np.ndarray] = None,
    risk_free_rate: float = 0.02
) -> dict:
    """
    计算组合统计指标
    参数:
        weights: 权重列表
        returns: (n_assets, n_periods) 收益率矩阵
    返回:
        dict: {annual_return, annual_vol, sharpe, var_95, cvar_95, ...}
    """
    w = np.array(weights)
    if isinstance(returns, pd.DataFrame):
        returns = returns.values
    if cov is None:
        cov = np.cov(returns, ddof=1)
    # 组合日收益率
    if returns.ndim == 2:
        port_ret = w @ returns  # (n_periods,)
        mu = np.mean(port_ret) * 252
        vol = np.sqrt(w.T @ cov @ w)
        sharpe = (mu - risk_free_rate) / vol if vol > 0 else 0.0
        # VaR / CVaR
        sorted_ret = np.sort(port_ret)
        n = len(sorted_ret)
        var_95 = float(sorted_ret[int(n * 0.05)])
        cvar_95 = float(np.mean(sorted_ret[:int(n * 0.05)]))
        max_drawdown = _calc_max_drawdown(port_ret)
        calmar = mu / max_drawdown if max_drawdown > 0 else 0.0
    else:
        port_ret = w @ returns
        mu = float(port_ret)
        vol = float(np.sqrt(w.T @ cov @ w))
        sharpe = (mu - risk_free_rate) / vol if vol > 0 else 0.0
        var_95 = None
        cvar_95 = None
        max_drawdown = None
        calmar = None
    return {
        'annual_return': round(mu, 4),
        'annual_volatility': round(float(vol), 4),
        'sharpe_ratio': round(float(sharpe), 4),
        'var_95': round(var_95, 4) if var_95 is not None else None,
        'cvar_95': round(cvar_95, 4) if cvar_95 is not None else None,
        'max_drawdown': round(float(max_drawdown), 4) if max_drawdown is not None else None,
        'calmar_ratio': round(float(calmar), 4) if calmar is not None else None
    }


def _calc_max_drawdown(returns: np.ndarray) -> float:
    """计算最大回撤 (基于日收益率序列)"""
    cum = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    return float(np.min(dd))
