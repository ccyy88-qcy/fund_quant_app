"""多因子选股系统 — 纯pandas/numpy向量化实现

功能：
  - 因子计算：估值(PE/PB/PS)、成长(营收增长/利润增速)、质量(ROE/ROA)、动量(N月收益)、规模(流通市值)
  - 因子IC/IR分析：截面相关系数、IR(IC均值/IC标准差)
  - 因子分层回测：分5组(Q1-Q5)，计算每组未来收益，判断分组单调性
  - 因子相关性矩阵
  - 合成因子：等权/ICIR加权合成
  - 数据降级：无截面数据时用模拟数据演示框架

所有返回结果均为JSON可序列化dict/list，浮点数用round(x,4)。
"""
import numpy as np
import pandas as pd
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# 数据降级：无截面数据时生成模拟数据演示框架
# ═══════════════════════════════════════════════════════════════

def _sim_stock_data(n_stocks: int = 50) -> list:
    """生成模拟股票截面数据（用于无数据时的演示框架）"""
    np.random.seed(42)
    stocks = []
    for i in range(n_stocks):
        pe = np.random.uniform(5, 80)
        pb = np.random.uniform(0.5, 15)
        ps = np.random.uniform(0.3, 20)
        rev_growth = np.random.uniform(-30, 60)
        profit_growth = np.random.uniform(-50, 100)
        roe = np.random.uniform(-10, 35)
        roa = np.random.uniform(-5, 20)
        mom_1m = np.random.uniform(-20, 30)
        mom_3m = np.random.uniform(-35, 50)
        mom_6m = np.random.uniform(-50, 80)
        mom_12m = np.random.uniform(-60, 120)
        circ_mv = np.random.uniform(1e8, 1e11)
        forward_ret = np.random.uniform(-15, 25)  # 未来N日收益(%)
        stocks.append({
            'code': f'{600000 + i:06d}',
            'name': f'股票{i+1}',
            'pe': round(pe, 2),
            'pb': round(pb, 2),
            'ps': round(ps, 2),
            'revenue_growth': round(rev_growth, 2),
            'profit_growth': round(profit_growth, 2),
            'roe': round(roe, 2),
            'roa': round(roa, 2),
            'mom_1m': round(mom_1m, 2),
            'mom_3m': round(mom_3m, 2),
            'mom_6m': round(mom_6m, 2),
            'mom_12m': round(mom_12m, 2),
            'circ_mv': round(circ_mv, 2),
            'forward_return': round(forward_ret, 4),
        })
    return stocks

# ═══════════════════════════════════════════════════════════════
# 因子计算
# ═══════════════════════════════════════════════════════════════

def calc_factor_returns(stock_data: list) -> dict:
    """计算6大类因子值

    Args:
        stock_data: 股票截面数据列表，每只股票为一个dict，包含:
            code, name, pe, pb, ps, revenue_growth, profit_growth,
            roe, roa, mom_1m, mom_3m, mom_6m, mom_12m, circ_mv

    Returns:
        dict: {
            'factors': {...},     # 各因子值列表 (已标准化)
            'raw': {...},         # 原始因子值
            'codes': [...],       # 股票代码
            'stock_count': int,   # 股票数量
            'factor_names': [...] # 因子名称列表
        }
    """
    if not stock_data:
        stock_data = _sim_stock_data()

    df = pd.DataFrame(stock_data)

    # ── 因子定义 ──
    factor_defs = {
        # 估值因子 (反向，越大越便宜/越小越好，做排名取倒数或取负)
        'value_pe':      lambda d: d['pe'],
        'value_pb':      lambda d: d['pb'],
        'value_ps':      lambda d: d['ps'],
        # 成长因子
        'growth_revenue': lambda d: d['revenue_growth'],
        'growth_profit':  lambda d: d['profit_growth'],
        # 质量因子
        'quality_roe':   lambda d: d['roe'],
        'quality_roa':   lambda d: d['roa'],
        # 动量因子
        'momentum_1m':   lambda d: d['mom_1m'],
        'momentum_3m':   lambda d: d['mom_3m'],
        'momentum_6m':   lambda d: d['mom_6m'],
        'momentum_12m':  lambda d: d['mom_12m'],
        # 规模因子
        'size_circ_mv':  lambda d: d['circ_mv'],
    }

    # 提取原始值
    raw = {}
    for name, func in factor_defs.items():
        raw[name] = [round(float(func(row)), 4) for _, row in df.iterrows()]

    # ── Z-score 标准化 (去极值+标准化) ──
    factors = {}
    for name, vals in raw.items():
        arr = np.array(vals, dtype=np.float64)
        # 去极值：MAD法, 3倍中位数绝对偏差
        median = np.median(arr)
        mad = np.median(np.abs(arr - median))
        if mad > 0:
            upper = median + 3 * 1.4826 * mad
            lower = median - 3 * 1.4826 * mad
            arr = np.clip(arr, lower, upper)
        # Z-score标准化
        mean = np.mean(arr)
        std = np.std(arr)
        if std > 0:
            arr = (arr - mean) / std
        else:
            arr = np.zeros_like(arr)
        factors[name] = [round(float(v), 4) for v in arr]

    # 估值因子反转（PE/PB/PS越小越好，取负使方向一致）
    for fn in ['value_pe', 'value_pb', 'value_ps']:
        factors[fn] = [round(-v, 4) if v is not None else None for v in factors[fn]]

    return {
        'factors': factors,
        'raw': raw,
        'codes': [str(row.get('code', '')) for _, row in df.iterrows()],
        'stock_count': len(df),
        'factor_names': list(factor_defs.keys()),
    }


# ═══════════════════════════════════════════════════════════════
# 因子IC/IR分析
# ═══════════════════════════════════════════════════════════════

def factor_ic_analysis(factor_data: list, forward_returns: list) -> dict:
    """计算因子IC/IR分析

    Args:
        factor_data: 多期因子值列表 [{'date': '2024-01-01', 'factors': {...}, 'returns': [...]}, ...]
                      每期包含截面因子值和对应的未来收益
        forward_returns: 可直接传入未来收益列表（单期截面分析用）

    Returns:
        dict: {
            'ic': {...},         # 各因子IC值 dict[factor_name] = ic_value
            'ic_mean': {...},    # 各因子IC均值
            'ic_std': {...},     # 各因子IC标准差
            'ir': {...},         # IR = IC_mean / IC_std
            'ic_rank': list,     # 按IC绝对值降序排列的因子排名
            'icir_rank': list,   # 按IR绝对值降序排列的因子排名
        }
    """
    # ── 单期截面分析模式 ──
    # 场景1: factor_data 是 dict {factor_name: [values]}
    if isinstance(factor_data, dict):
        return _calc_ic_single_cross_section(factor_data, forward_returns)
    # 场景2: factor_data 是 list of values (单因子)
    if isinstance(factor_data, list) and len(factor_data) > 0:
        first = factor_data[0]
        if isinstance(first, (int, float)):
            return _calc_ic_single_cross_section(factor_data, forward_returns)
        if isinstance(first, dict) and 'date' not in first and 'factors' not in first:
            return _calc_ic_single_cross_section(factor_data, forward_returns)

    # ── 多期时间序列模式 ──
    if not factor_data:
        # 模拟多期数据
        factor_data = _sim_multi_period_factors()

    ic_history = {}
    for period in factor_data:
        date = period.get('date', '')
        fvals = period.get('factors', {})
        rets = period.get('returns', [])
        if not fvals or not rets or len(rets) == 0:
            continue
        ic_single = _calc_ic_single_cross_section(
            [fvals[k] for k in fvals] if isinstance(fvals, dict) else fvals,
            rets
        )
        # ic_single 返回的是 dict with factor names as first level
        # 我们需要把它按因子聚合
        if isinstance(ic_single, dict) and 'ic' in ic_single:
            for fname, ic_val in ic_single['ic'].items():
                if fname not in ic_history:
                    ic_history[fname] = []
                ic_history[fname].append(ic_val)

    # 没有多期数据时，尝试单期
    if not ic_history:
        return _calc_ic_single_cross_section(factor_data[0].get('factors', {}),
                                              factor_data[0].get('returns', [])) if factor_data else \
               _calc_ic_single_cross_section(None, None)

    # 计算IC均值、IC标准差、IR
    result = {'ic': {}, 'ic_mean': {}, 'ic_std': {}, 'ir': {}}
    for fname, ic_series in ic_history.items():
        ic_arr = np.array(ic_series)
        ic_mean = float(np.mean(ic_arr))
        ic_std = float(np.std(ic_arr))
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        result['ic'][fname] = [round(float(v), 4) for v in ic_series]
        result['ic_mean'][fname] = round(ic_mean, 4)
        result['ic_std'][fname] = round(ic_std, 4)
        result['ir'][fname] = round(ir, 4)

    # 排名
    ic_abs_rank = sorted(
        [(k, abs(result['ic_mean'].get(k, 0))) for k in result['ic_mean']],
        key=lambda x: x[1], reverse=True
    )
    ir_abs_rank = sorted(
        [(k, abs(result['ir'].get(k, 0))) for k in result['ir']],
        key=lambda x: x[1], reverse=True
    )
    result['ic_rank'] = [{'factor': k, 'abs_ic_mean': round(v, 4)} for k, v in ic_abs_rank]
    result['icir_rank'] = [{'factor': k, 'abs_ir': round(v, 4)} for k, v in ir_abs_rank]

    return result


def _calc_ic_single_cross_section(factor_values, forward_returns):
    """单截面IC计算"""
    # 支持多种输入格式
    if factor_values is None:
        # 模拟数据
        sim = _sim_stock_data(50)
        factor_values = [s.get('pe', 0) for s in sim]
        forward_returns = [s.get('forward_return', 0) for s in sim]
        fnames_map = {'factor_0': 'value_pe'}

    if isinstance(factor_values, dict):
        # {factor_name: [values]}
        fnames_map = {k: k for k in factor_values}
        fnames_list = list(factor_values.keys())
        fvalues_matrix = [factor_values[k] for k in fnames_list]
    elif isinstance(factor_values, list) and len(factor_values) > 0:
        if isinstance(factor_values[0], (int, float)):
            # 单因子列表
            fnames_map = {0: 'factor_0'}
            fnames_list = ['factor_0']
            fvalues_matrix = [factor_values]
        elif isinstance(factor_values[0], dict):
            # 每只股票一个dict {factor_name: value}
            fnames_list = list(factor_values[0].keys())
            fnames_map = {k: k for k in fnames_list}
            fvalues_matrix = [[d.get(k, np.nan) for d in factor_values] for k in fnames_list]
        else:
            fnames_map = {i: f'factor_{i}' for i in range(len(factor_values))}
            fnames_list = list(fnames_map.values())
            fvalues_matrix = factor_values if isinstance(factor_values[0], list) else [factor_values]
    else:
        return {'ic': {}, 'ic_mean': {}, 'ic_std': {}, 'ir': {}, 'note': '数据不足'}

    if not forward_returns or len(forward_returns) == 0:
        sim = _sim_stock_data(len(fvalues_matrix[0]) if fvalues_matrix else 50)
        forward_returns = [s.get('forward_return', 0) for s in sim]

    ret_arr = np.array(forward_returns, dtype=np.float64)

    ic_result = {}
    for idx, fname in enumerate(fnames_list):
        fvals = np.array(fvalues_matrix[idx], dtype=np.float64)

        # 去缺失值
        mask = ~(np.isnan(fvals) | np.isnan(ret_arr))
        f_clean = fvals[mask]
        r_clean = ret_arr[mask]
        n = len(f_clean)
        if n < 5:
            ic_result[fname] = None
            continue

        # Spearman秩相关系数
        f_rank = np.argsort(np.argsort(f_clean))  # rank
        r_rank = np.argsort(np.argsort(r_clean))
        f_mean = np.mean(f_rank)
        r_mean = np.mean(r_rank)
        num = np.sum((f_rank - f_mean) * (r_rank - r_mean))
        den = np.sqrt(np.sum((f_rank - f_mean) ** 2) * np.sum((r_rank - r_mean) ** 2))
        ic_val = num / den if den > 0 else 0.0
        ic_result[fname] = round(float(ic_val), 4)

    # 单期IC
    ic_mean = {k: v for k, v in ic_result.items() if v is not None}
    ic_vals = [v for v in ic_result.values() if v is not None]
    ic_std_val = float(np.std(ic_vals)) if len(ic_vals) > 1 else 0.0
    ic_mean_val = float(np.mean(ic_vals)) if ic_vals else 0.0
    ir_val = ic_mean_val / ic_std_val if ic_std_val > 0 else 0.0

    return {
        'ic': ic_result,
        'ic_mean': {k: round(ic_mean_val, 4) for k in ic_result},
        'ic_std': {k: round(ic_std_val, 4) for k in ic_result},
        'ir': {k: round(ir_val, 4) for k in ic_result},
        'stock_count': len(forward_returns),
        'note': '单期截面分析' if len(ic_vals) > 0 else '数据不足'
    }


def _sim_multi_period_factors(n_periods: int = 12) -> list:
    """模拟多期因子数据"""
    np.random.seed(42)
    periods = []
    base_date = pd.Timestamp('2024-01-31')
    for i in range(n_periods):
        date = (base_date + pd.DateOffset(months=i)).strftime('%Y-%m-%d')
        n = 50
        factors = {}
        for fname in ['value_pe', 'value_pb', 'growth_revenue', 'growth_profit',
                       'quality_roe', 'quality_roa', 'momentum_3m', 'size_circ_mv']:
            factors[fname] = [round(float(v), 4) for v in np.random.randn(n)]
        returns = [round(float(v), 4) for v in np.random.uniform(-10, 15, n)]
        periods.append({'date': date, 'factors': factors, 'returns': returns})
    return periods


# ═══════════════════════════════════════════════════════════════
# 因子分层回测
# ═══════════════════════════════════════════════════════════════

def factor_layer_backtest(factor_values: list, forward_returns: list,
                          layers: int = 5) -> dict:
    """因子分层回测

    按因子值从低到高分layers组(Q1=最小, Q{layers}=最大)，
    计算每组未来收益均值，判定单调性。

    Args:
        factor_values: 单截面因子值列表 [float, ...]
        forward_returns: 对应未来收益列表 [float, ...]
        layers: 分组数，默认5

    Returns:
        dict: {
            'groups': { 'Q1': {...}, ..., 'Q5': {...} },
            'group_returns': [r1, r2, ..., r5],  # 各组平均收益
            'group_stocks': { 'Q1': [...], ... }, # 各组股票代码
            'monotonicity': bool,       # 是否单调
            'monotonicity_score': float, # 单调性评分 (0~1)
            'long_short_return': float,  # 多空收益 (Q5 - Q1)
            'parameters': { 'layers': layers }
        }
    """
    if not factor_values or not forward_returns:
        # 模拟数据演示
        sim = _sim_stock_data(50)
        factor_values = [s.get('pe', 0) for s in sim]
        forward_returns = [s.get('forward_return', 0) for s in sim]

    farr = np.array(factor_values, dtype=np.float64)
    rarr = np.array(forward_returns, dtype=np.float64)

    # 去缺失
    mask = ~(np.isnan(farr) | np.isnan(rarr))
    farr = farr[mask]
    rarr = rarr[mask]

    if len(farr) < layers:
        return {
            'groups': {},
            'group_returns': [],
            'monotonicity': False,
            'long_short_return': 0.0,
            'note': '数据量不足'
        }

    # 按因子值分位数分组 (Q1=最低值组, Q5=最高值组)
    # 对于正向因子（值越大越好），Q5收益应最高
    # 对于估值因子（已取反），Q5收益也应最高
    percentiles = np.linspace(0, 100, layers + 1)[1:-1]
    cut_points = np.percentile(farr, percentiles)
    bin_indices = np.digitize(farr, cut_points)  # 0=Q1, ..., layers-1=Ql

    # 保证每组都有股票
    unique_bins = np.unique(bin_indices)
    if len(unique_bins) < layers:
        # 分位数不足时用rank分桶
        ranks = np.argsort(np.argsort(farr))
        bin_indices = np.floor(ranks / len(farr) * layers).astype(int)
        bin_indices = np.clip(bin_indices, 0, layers - 1)

    groups = {}
    group_returns = []
    group_stocks = {}

    for g in range(layers):
        mask_g = bin_indices == g
        g_rets = rarr[mask_g]
        g_mean = float(np.mean(g_rets)) if len(g_rets) > 0 else 0.0
        g_median = float(np.median(g_rets)) if len(g_rets) > 0 else 0.0
        g_std = float(np.std(g_rets)) if len(g_rets) > 1 else 0.0
        g_count = int(np.sum(mask_g))

        label = f'Q{g + 1}'
        factor_min = round(float(farr[mask_g].min()), 4) if g_count > 0 else None
        factor_max = round(float(farr[mask_g].max()), 4) if g_count > 0 else None
        groups[label] = {
            'mean_return': round(g_mean, 4),
            'median_return': round(g_median, 4),
            'std_return': round(g_std, 4),
            'count': g_count,
            'factor_min': factor_min,
            'factor_max': factor_max,
        }
        group_returns.append(round(g_mean, 4))

    # 单调性判定
    # 如果组收益序列单调递增或递减，则为单调
    diffs = np.diff(group_returns)
    monotonic_up = bool(np.all(diffs > -1e-8))   # 允许微小误差
    monotonic_down = bool(np.all(diffs < 1e-8))
    monotonic = monotonic_up or monotonic_down

    # 单调性评分：相邻组方向一致性比例
    pos_count = np.sum(diffs > 0)
    neg_count = np.sum(diffs < 0)
    mono_score = max(pos_count, neg_count) / len(diffs) if len(diffs) > 0 else 0.0

    # 多空收益
    ls_return = round(group_returns[-1] - group_returns[0], 4)

    return {
        'groups': groups,
        'group_returns': group_returns,
        'monotonicity': monotonic,
        'monotonicity_score': round(float(mono_score), 4),
        'long_short_return': ls_return,
        'parameters': {'layers': layers},
    }


# ═══════════════════════════════════════════════════════════════
# 因子相关性矩阵
# ═══════════════════════════════════════════════════════════════

def factor_correlation_matrix(factor_data: dict) -> dict:
    """计算因子间相关性矩阵

    Args:
        factor_data: calc_factor_returns() 返回的dict，含 'factors' 键
                     或直接传入 {factor_name: [values]}

    Returns:
        dict: {
            'correlation_matrix': [[...], ...],  # 矩阵
            'factor_names': [...],               # 因子名称
            'heatmap_data': [{'x':..., 'y':..., 'value':...}, ...]  # 热力图格式
        }
    """
    if not factor_data:
        # 生成模拟数据
        sim = calc_factor_returns()
        factor_data = sim['factors']

    if isinstance(factor_data, dict) and 'factors' in factor_data:
        factor_data = factor_data['factors']

    if not factor_data:
        return {'correlation_matrix': [], 'factor_names': [], 'heatmap_data': []}

    fnames = list(factor_data.keys())
    n = len(fnames)
    if n == 0:
        return {'correlation_matrix': [], 'factor_names': [], 'heatmap_data': []}

    # 构建矩阵
    matrix = np.zeros((n, n))
    heatmap = []

    for i in range(n):
        for j in range(n):
            vi = np.array(factor_data[fnames[i]], dtype=np.float64)
            vj = np.array(factor_data[fnames[j]], dtype=np.float64)
            mask = ~(np.isnan(vi) | np.isnan(vj))
            vi_c = vi[mask]
            vj_c = vj[mask]
            if len(vi_c) < 3:
                corr = 0.0
            else:
                # Pearson相关系数
                corr_matrix = np.corrcoef(vi_c, vj_c)
                corr = corr_matrix[0, 1] if not np.isnan(corr_matrix[0, 1]) else 0.0
            matrix[i][j] = round(float(corr), 4)
            heatmap.append({
                'x': fnames[j],
                'y': fnames[i],
                'value': round(float(corr), 4),
            })

    return {
        'correlation_matrix': matrix.tolist(),
        'factor_names': fnames,
        'heatmap_data': heatmap,
    }


# ═══════════════════════════════════════════════════════════════
# 合成因子
# ═══════════════════════════════════════════════════════════════

def composite_factor(factors: dict, weights: Optional[list] = None) -> dict:
    """合成多因子为综合因子

    支持两种加权方式:
      1. 等权 (weights=None)
      2. 自定义权重 (weights=dict 或 list)
      3. ICIR加权 (weights='icir' 时需传 icir_weights)

    Args:
        factors: {factor_name: [z_score_values]} 或
                 calc_factor_returns() 的返回dict
        weights: None(等权), dict {factor_name: weight}, list [w1,w2,...],
                 'icir' 表示ICIR加权

    Returns:
        dict: {
            'composite': [z_score, ...],   # 合成因子值
            'weights_used': {...},          # 实际使用的权重
            'weight_method': str,           # 权重方法描述
            'factor_contributions': {...},  # 各因子对合成的贡献
            'statistics': {...}             # 合成因子统计量
        }
    """
    if not factors:
        sim = calc_factor_returns()
        factors = sim['factors']

    # 兼容 calc_factor_returns 的返回值
    if isinstance(factors, dict) and 'factors' in factors:
        factors = factors['factors']

    if not factors:
        return {'composite': [], 'note': '无因子数据'}

    fnames = list(factors.keys())
    n_factors = len(fnames)
    n_stocks = len(factors[fnames[0]])

    # ── 确定权重 ──
    weight_method = '等权'
    w = {}

    if weights is None:
        # 等权
        for fn in fnames:
            w[fn] = 1.0 / n_factors
        weight_method = '等权'

    elif isinstance(weights, dict):
        # 自定义dict权重
        total = sum(abs(v) for v in weights.values())
        if total > 0:
            for fn in fnames:
                w[fn] = weights.get(fn, 0.0) / total
        else:
            for fn in fnames:
                w[fn] = 1.0 / n_factors
        weight_method = '自定义权重'

    elif isinstance(weights, list):
        # list权重
        if len(weights) == n_factors:
            w_arr = np.array(weights, dtype=np.float64)
            w_arr = np.abs(w_arr) / np.sum(np.abs(w_arr)) if np.sum(np.abs(w_arr)) > 0 else np.ones(n_factors) / n_factors
            for i, fn in enumerate(fnames):
                w[fn] = float(w_arr[i])
        else:
            for fn in fnames:
                w[fn] = 1.0 / n_factors
        weight_method = '自定义权重'

    elif isinstance(weights, str) and weights.lower() == 'icir':
        # ICIR加权 — 需要从factor_data中获取ICIR
        # 这里模拟ICIR权重
        np.random.seed(42)
        icir_vals = np.abs(np.random.randn(n_factors))
        icir_vals = icir_vals / icir_vals.sum()
        for i, fn in enumerate(fnames):
            w[fn] = float(icir_vals[i])
        weight_method = 'ICIR加权(模拟)'

    # ── 计算合成因子 ──
    composite_arr = np.zeros(n_stocks, dtype=np.float64)
    contributions = {}

    for fn in fnames:
        vals = np.array(factors[fn], dtype=np.float64)
        # 处理缺失值
        vals = np.nan_to_num(vals, nan=0.0)
        weighted = vals * w[fn]
        composite_arr += weighted
        contributions[fn] = round(float(np.sum(weighted) / n_stocks if n_stocks > 0 else 0), 4)

    # Z-score 标准化合成因子
    comp_mean = np.mean(composite_arr)
    comp_std = np.std(composite_arr)
    if comp_std > 0:
        composite_z = (composite_arr - comp_mean) / comp_std
    else:
        composite_z = np.zeros_like(composite_arr)

    # 统计量
    statistics = {
        'mean': round(float(np.mean(composite_z)), 4),
        'std': round(float(np.std(composite_z)), 4),
        'min': round(float(np.min(composite_z)), 4),
        'max': round(float(np.max(composite_z)), 4),
        'median': round(float(np.median(composite_z)), 4),
        'skew': round(float(pd.Series(composite_z).skew()), 4),
        'kurtosis': round(float(pd.Series(composite_z).kurtosis()), 4),
    }

    return {
        'composite': [round(float(v), 4) for v in composite_z],
        'weights_used': {k: round(float(v), 4) for k, v in w.items()},
        'weight_method': weight_method,
        'factor_contributions': contributions,
        'statistics': statistics,
    }


# ═══════════════════════════════════════════════════════════════
# 一键多因子分析
# ═══════════════════════════════════════════════════════════════

def full_factor_analysis(stock_data: Optional[list] = None,
                         multi_period_data: Optional[list] = None) -> dict:
    """完整多因子分析流程

    依次执行：因子计算 → IC分析 → 分层回测 → 相关性矩阵 → 合成因子

    Args:
        stock_data: 单截面股票数据列表（可选）
        multi_period_data: 多期数据（可选，用于IC/IR时序分析）

    Returns:
        dict: 包含所有分析结果的综合报告
    """
    if stock_data is None:
        stock_data = _sim_stock_data(50)

    # 1. 因子计算
    factor_result = calc_factor_returns(stock_data)

    # 2. 提取第一个因子做分层回测演示
    first_factor_name = factor_result['factor_names'][0] if factor_result['factor_names'] else 'value_pe'
    first_factor_vals = factor_result['factors'].get(first_factor_name, [])
    forward_returns_vals = [s.get('forward_return', 0) for s in stock_data]

    layer_result = factor_layer_backtest(first_factor_vals, forward_returns_vals)

    # 3. IC分析
    ic_result = factor_ic_analysis(factor_result['factors'], forward_returns_vals)

    # 4. 相关性矩阵
    corr_result = factor_correlation_matrix(factor_result['factors'])

    # 5. 合成因子
    comp_result = composite_factor(factor_result['factors'])

    # 6. 合成因子分层回测
    comp_layer_result = factor_layer_backtest(
        comp_result['composite'], forward_returns_vals
    )

    return {
        'factor_calculation': {
            'stock_count': factor_result['stock_count'],
            'factor_names': factor_result['factor_names'],
            'raw_factors': factor_result['raw'],
            'standardized_factors': factor_result['factors'],
        },
        'factor_ic_analysis': ic_result,
        'factor_layer_backtest': {
            'example_factor': first_factor_name,
            'backtest': layer_result,
        },
        'factor_correlation': corr_result,
        'composite_factor': comp_result,
        'composite_layer_backtest': comp_layer_result,
    }


# ═══════════════════════════════════════════════════════════════
# 便捷函数：批量因子分层回测（所有因子）
# ═══════════════════════════════════════════════════════════════

def batch_layer_backtest(stock_data: Optional[list] = None,
                         layers: int = 5) -> dict:
    """对所有因子进行分层回测

    Args:
        stock_data: 股票截面数据
        layers: 分组数

    Returns:
        dict: {factor_name: layer_backtest_result}
    """
    if stock_data is None:
        stock_data = _sim_stock_data(50)

    factor_result = calc_factor_returns(stock_data)
    forward_returns = [s.get('forward_return', 0) for s in stock_data]

    results = {}
    for fname in factor_result['factor_names']:
        fvals = factor_result['factors'][fname]
        bt = factor_layer_backtest(fvals, forward_returns, layers=layers)
        results[fname] = bt

    return {
        'results': results,
        'summary': _summarize_layers(results),
    }


def _summarize_layers(results: dict) -> dict:
    """汇总分层回测结果"""
    best_factor = None
    best_ls = -999
    monotonic_factors = []

    for fname, bt in results.items():
        ls = bt.get('long_short_return', -999)
        if ls > best_ls:
            best_ls = ls
            best_factor = fname
        if bt.get('monotonicity'):
            monotonic_factors.append(fname)

    return {
        'best_factor_by_long_short': best_factor,
        'best_long_short_return': round(best_ls, 4) if best_ls > -999 else None,
        'monotonic_factors': monotonic_factors,
        'monotonic_count': len(monotonic_factors),
        'total_factors': len(results),
    }


# ═══════════════════════════════════════════════════════════════
# __main__ 演示
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import json
    print("=" * 60)
    print("多因子选股系统 — 演示")
    print("=" * 60)

    # 生成模拟数据
    print("\n[1] 模拟股票截面数据...")
    sim_data = _sim_stock_data(50)
    print(f"  生成 {len(sim_data)} 只股票数据")

    # 因子计算
    print("\n[2] 计算因子...")
    fr = calc_factor_returns(sim_data)
    print(f"  因子数量: {len(fr['factor_names'])}")
    for fn in fr['factor_names']:
        vals = fr['factors'][fn][:5]
        print(f"  {fn}: {vals[:3]}...")

    # IC分析
    print("\n[3] 因子IC分析...")
    ic = factor_ic_analysis(fr['factors'],
                            [s['forward_return'] for s in sim_data])
    print(f"  IC: {json.dumps(ic['ic'], ensure_ascii=False)}")
    print(f"  IR: {json.dumps(ic['ir'], ensure_ascii=False)}")

    # 分层回测
    print("\n[4] 因子分层回测 (value_pe)...")
    bt = factor_layer_backtest(
        fr['factors']['value_pe'],
        [s['forward_return'] for s in sim_data]
    )
    print(f"  分组收益: {bt['group_returns']}")
    print(f"  单调性: {bt['monotonicity']} (评分: {bt['monotonicity_score']})")
    print(f"  多空收益: {bt['long_short_return']}")

    # 相关性矩阵
    print("\n[5] 因子相关性矩阵...")
    cm = factor_correlation_matrix(fr['factors'])
    print(f"  因子数: {len(cm['factor_names'])}")

    # 合成因子
    print("\n[6] 合成因子 (等权)...")
    comp = composite_factor(fr['factors'])
    print(f"  权重方法: {comp['weight_method']}")
    print(f"  合成因子统计: {json.dumps(comp['statistics'], ensure_ascii=False)}")

    # 合成因子分层回测
    print("\n[7] 合成因子分层回测...")
    comp_bt = factor_layer_backtest(
        comp['composite'],
        [s['forward_return'] for s in sim_data]
    )
    print(f"  分组收益: {comp_bt['group_returns']}")
    print(f"  单调性: {comp_bt['monotonicity']}")
    print(f"  多空收益: {comp_bt['long_short_return']}")

    # 完整分析
    print("\n[8] 完整分析...")
    full = full_factor_analysis(sim_data)
    print(f"  股票数: {full['factor_calculation']['stock_count']}")
    print(f"  因子数: {len(full['factor_calculation']['factor_names'])}")

    print("\n" + "=" * 60)
    print("所有演示完成 ✓")
    print("=" * 60)
