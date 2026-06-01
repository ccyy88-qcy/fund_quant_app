"""自定义策略回测引擎 — 任意规则组合 + 参数优化 + 绩效归因"""
import numpy as np
import pandas as pd
from itertools import product
from typing import Optional, Callable
from .indicators import calc_ma, calc_rsi, calc_macd, calc_bollinger, calc_cci
from .risk_metrics import max_drawdown, sharpe_ratio, annual_return

# ─── 策略信号函数库 ───

def _ma_cross_signal(df: pd.DataFrame, fast: int = 10, slow: int = 60) -> np.ndarray:
    """MA交叉信号: 快线上穿慢线=1, 下穿=-1, 否则=0"""
    ma_fast = calc_ma(df['close'], fast)
    ma_slow = calc_ma(df['close'], slow)
    diff = ma_fast - ma_slow
    signal = np.zeros(len(df))
    for i in range(1, len(diff)):
        if not np.isnan(diff.iloc[i]) and not np.isnan(diff.iloc[i-1]):
            if diff.iloc[i] > 0 and diff.iloc[i-1] <= 0:
                signal[i] = 1
            elif diff.iloc[i] < 0 and diff.iloc[i-1] >= 0:
                signal[i] = -1
    return signal

def _rsi_threshold_signal(df: pd.DataFrame, period: int = 14, oversold: float = 30, overbought: float = 70) -> np.ndarray:
    """RSI阈值信号: 上穿超卖线=1, 下穿超买线=-1"""
    rsi = calc_rsi(df['close'], period)
    signal = np.zeros(len(df))
    for i in range(1, len(rsi)):
        if not np.isnan(rsi.iloc[i]) and not np.isnan(rsi.iloc[i-1]):
            if rsi.iloc[i-1] <= oversold and rsi.iloc[i] > oversold:
                signal[i] = 1
            elif rsi.iloc[i-1] >= overbought and rsi.iloc[i] < overbought:
                signal[i] = -1
    return signal

def _bollinger_signal(df: pd.DataFrame, period: int = 20, std: int = 2) -> np.ndarray:
    """布林带信号: 价格下穿下轨=1, 上穿上轨=-1"""
    upper, mid, lower = calc_bollinger(df['close'], period, std)
    close = df['close']
    signal = np.zeros(len(df))
    for i in range(1, len(close)):
        if i < period: continue
        if not np.isnan(close.iloc[i]) and not np.isnan(lower.iloc[i]):
            if close.iloc[i-1] <= lower.iloc[i-1] and close.iloc[i] > lower.iloc[i]:
                signal[i] = 1
        if not np.isnan(close.iloc[i]) and not np.isnan(upper.iloc[i]):
            if close.iloc[i-1] >= upper.iloc[i-1] and close.iloc[i] < upper.iloc[i]:
                signal[i] = -1
    return signal

def _macd_signal(df: pd.DataFrame) -> np.ndarray:
    """MACD金叉死叉信号: DIF上穿DEA=1, 下穿=-1"""
    dif, dea, _ = calc_macd(df['close'])
    signal = np.zeros(len(df))
    for i in range(1, len(dif)):
        if not np.isnan(dif.iloc[i]) and not np.isnan(dea.iloc[i]) and not np.isnan(dif.iloc[i-1]) and not np.isnan(dea.iloc[i-1]):
            if dif.iloc[i-1] <= dea.iloc[i-1] and dif.iloc[i] > dea.iloc[i]:
                signal[i] = 1
            elif dif.iloc[i-1] >= dea.iloc[i-1] and dif.iloc[i] < dea.iloc[i]:
                signal[i] = -1
    return signal

def _price_volume_signal(df: pd.DataFrame, price_up_pct: float = 3.0, vol_factor: float = 1.5) -> np.ndarray:
    """量价齐升信号: 涨幅>X%且成交量>Y倍均值=1"""
    close = df['close']
    volume = df['volume']
    vol_mean = volume.rolling(20).mean()
    returns = close.pct_change() * 100
    signal = np.zeros(len(df))
    for i in range(1, len(close)):
        if not np.isnan(returns.iloc[i]) and vol_mean.iloc[i] > 0:
            if returns.iloc[i] > price_up_pct and volume.iloc[i] > vol_mean.iloc[i] * vol_factor:
                signal[i] = 1
            elif returns.iloc[i] < -price_up_pct and volume.iloc[i] > vol_mean.iloc[i] * vol_factor:
                signal[i] = -1
    return signal

# 策略信号注册表
STRATEGY_SIGNAL_MAP = {
    'ma_cross': _ma_cross_signal,
    'rsi_threshold': _rsi_threshold_signal,
    'bollinger': _bollinger_signal,
    'macd': _macd_signal,
    'price_volume': _price_volume_signal,
}


# ─── 策略定义 ───

def describe_strategy(strategy_type: str = None) -> dict:
    """返回策略类型说明和参数规则"""
    strategies = {
        'ma_cross': {
            'name': 'MA交叉策略',
            'desc': '快线上穿慢线买入，下穿卖出',
            'params': {'fast': (5, 30, 5), 'slow': (20, 120, 10)},
            'defaults': {'fast': 10, 'slow': 60},
        },
        'rsi_threshold': {
            'name': 'RSI阈值策略',
            'desc': 'RSI上穿超卖线买入，下穿超买线卖出',
            'params': {'period': (5, 30, 1), 'oversold': (10, 40, 5), 'overbought': (60, 90, 5)},
            'defaults': {'period': 14, 'oversold': 30, 'overbought': 70},
        },
        'bollinger': {
            'name': '布林带反转策略',
            'desc': '价格下穿下轨买入，上穿上轨卖出',
            'params': {'period': (10, 50, 5), 'std': (1, 3, 0.5)},
            'defaults': {'period': 20, 'std': 2},
        },
        'macd': {
            'name': 'MACD策略',
            'desc': 'DIF上穿DEA买入，下穿卖出',
            'params': {},
            'defaults': {},
        },
        'price_volume': {
            'name': '量价策略',
            'desc': '放量上涨买入，放量下跌卖出',
            'params': {'price_up_pct': (1, 5, 0.5), 'vol_factor': (1.0, 3.0, 0.5)},
            'defaults': {'price_up_pct': 3.0, 'vol_factor': 1.5},
        },
        'combined': {
            'name': '组合策略',
            'desc': '多策略信号加权合成',
            'params': {},
            'defaults': {},
        },
    }
    if strategy_type:
        return strategies.get(strategy_type, {})
    return strategies


def _get_signal_func(strategy_type: str, params: dict) -> Callable:
    """获取信号函数，应用参数"""
    base_func = STRATEGY_SIGNAL_MAP.get(strategy_type)
    if base_func is None:
        return None

    def wrapped(df: pd.DataFrame) -> np.ndarray:
        # 过滤参数中存在的参数
        import inspect
        sig = inspect.signature(base_func)
        valid_params = {k: v for k, v in params.items() if k in sig.parameters}
        return base_func(df, **valid_params)

    return wrapped


def run_custom_strategy(kline_data: list, strategy_type: str = 'ma_cross',
                        params: dict = None) -> dict:
    """执行自定义策略回测

    Args:
        kline_data: K线数据 [{day, open, high, low, close, volume}, ...]
        strategy_type: 策略类型 ma_cross/rsi_threshold/bollinger/macd/price_volume/combined
        params: 策略参数

    Returns:
        回测结果 {trades, metrics, equity_curve, signals}
    """
    if not kline_data or len(kline_data) < 60:
        return {'error': '数据不足(需≥60根K线)'}

    df = pd.DataFrame(kline_data)
    strategies = describe_strategy()
    defaults = strategies.get(strategy_type, {}).get('defaults', {})

    if params is None:
        params = {}
    merged_params = {**defaults, **params}

    # 生成信号
    if strategy_type == 'combined':
        # 组合策略：params 包含 sub_strategies 列表
        sub_strategies = merged_params.get('sub_strategies', ['ma_cross', 'rsi_threshold'])
        weights = merged_params.get('weights', [1.0 / len(sub_strategies)] * len(sub_strategies))
        combined = np.zeros(len(df))
        for i, sub_type in enumerate(sub_strategies):
            sub_params = merged_params.get(f'params_{i}', {})
            func = _get_signal_func(sub_type, sub_params)
            if func:
                combined += func(df) * weights[i]
        raw_signals = np.sign(combined)
    else:
        func = _get_signal_func(strategy_type, merged_params)
        if func is None:
            return {'error': f'未知策略类型: {strategy_type}'}
        raw_signals = func(df)

    # 执行交易
    closes = df['close'].values
    dates = df['day'].values if 'day' in df.columns else np.arange(len(df))
    trades = []
    equity = [100.0]
    equity_dates = [str(dates[0])]
    position = 0
    entry_price = 0
    entry_date = ''

    for i in range(1, len(raw_signals)):
        sig = raw_signals[i]
        equity_dates.append(str(dates[i]))

        if position == 0 and sig == 1:
            position = 1
            entry_price = float(closes[i])
            entry_date = str(dates[i])
        elif position == 1 and sig == -1:
            ret = (float(closes[i]) - entry_price) / entry_price * 100
            trades.append({
                'entry_date': entry_date,
                'exit_date': str(dates[i]),
                'entry_price': round(float(entry_price), 4),
                'exit_price': round(float(closes[i]), 4),
                'return': round(float(ret), 2),
            })
            equity.append(equity[-1] * (1 + ret / 100))
            position = 0
        else:
            if position == 0:
                equity.append(equity[-1])
            else:
                unrealized = (float(closes[i]) - entry_price) / entry_price * 100
                equity.append(equity[-1] * (1 + 0 / 100))  # 未实现不纳入

    # 平最后一笔
    if position == 1:
        ret = (float(closes[-1]) - entry_price) / entry_price * 100
        trades.append({
            'entry_date': entry_date,
            'exit_date': str(dates[-1]),
            'entry_price': round(float(entry_price), 4),
            'exit_price': round(float(closes[-1]), 4),
            'return': round(float(ret), 2),
        })
        equity.append(equity[-1] * (1 + ret / 100))

    # 转为等长equity_curve
    equity_curve = []
    eq_idx = 0
    for i in range(len(dates)):
        if position == 0:
            hold_price = float(closes[i])
        else:
            hold_price = float(closes[i])
        if eq_idx < len(equity) - 1:
           pass
        equity_curve.append({
            'date': str(dates[i]),
            'equity': round(equity[min(eq_idx, len(equity)-1)], 4),
        })
        # move equity index only on trades
    # Rebuild equity correctly
    equity_pos = 100.0
    equity_curve = [{'date': str(dates[0]), 'equity': 100.0}]
    trade_idx = 0
    for i in range(1, len(dates)):
        if trade_idx < len(trades) and str(dates[i]) == trades[trade_idx]['exit_date']:
            equity_pos = equity_pos * (1 + trades[trade_idx]['return'] / 100)
            trade_idx += 1
        equity_curve.append({'date': str(dates[i]), 'equity': round(equity_pos, 4)})

    # 绩效指标
    metrics = {}
    if trades:
        returns_arr = np.array([t['return'] for t in trades])
        wins = returns_arr[returns_arr > 0]
        losses = returns_arr[returns_arr < 0]

        series = pd.Series([e['equity'] for e in equity_curve])
        metrics = {
            'total_trades': len(trades),
            'win_rate': round(len(wins) / len(returns_arr) * 100, 2) if len(returns_arr) > 0 else 0,
            'avg_win': round(float(np.mean(wins)), 2) if len(wins) > 0 else 0,
            'avg_loss': round(float(np.mean(losses)), 2) if len(losses) > 0 else 0,
            'profit_loss_ratio': round(float(abs(np.mean(wins) / np.mean(losses))), 2) if len(wins) > 0 and len(losses) > 0 else 0,
            'total_return': round(float((equity_curve[-1]['equity'] - 100) / 100 * 100), 2),
            'max_drawdown': round(float(max_drawdown(series) or 0), 2),
            'annual_return': round(float(annual_return(series) or 0), 2),
            'sharpe': round(float(sharpe_ratio(series) or 0), 2),
        }

    return {
        'strategy': strategy_type,
        'params': merged_params,
        'trades': trades,
        'metrics': metrics,
        'equity_curve': equity_curve[-200:],  # 最多200点
    }


# ─── 参数优化（网格搜索） ───

def optimize_params(kline_data: list, strategy_type: str = 'ma_cross',
                    param_ranges: dict = None, objective: str = 'sharpe') -> dict:
    """参数网格优化

    Args:
        kline_data: K线数据
        strategy_type: 策略类型
        param_ranges: 参数搜索范围 {param: [v1, v2, v3, ...]}
        objective: 优化目标 sharpe/total_return/win_rate/profit_loss_ratio/calmar

    Returns:
        最佳参数 + 所有组合结果
    """
    if not kline_data or len(kline_data) < 60:
        return {'error': '数据不足(需≥60根K线)'}

    strategies = describe_strategy()
    defaults = strategies.get(strategy_type, {}).get('defaults', {})
    default_ranges = strategies.get(strategy_type, {}).get('params', {})

    if param_ranges is None:
        param_ranges = {}
        for param, (low, high, step) in default_ranges.items():
            if isinstance(step, float):
                count = min(10, int((high - low) / step) + 1)
                param_ranges[param] = [round(low + i * step, 1) for i in range(count)]
            else:
                param_ranges[param] = list(range(low, high + step, step))

    # 生成参数组合
    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    combinations = list(product(*param_values))

    results = []
    best_score = -float('inf')
    best_params = None
    best_result = None

    for combo in combinations:
        params = dict(zip(param_names, combo))
        result = run_custom_strategy(kline_data, strategy_type, {**defaults, **params})
        if 'error' in result:
            continue

        metrics = result.get('metrics', {})
        if objective == 'sharpe':
            score = metrics.get('sharpe', -999)
        elif objective == 'total_return':
            score = metrics.get('total_return', -999)
        elif objective == 'win_rate':
            score = metrics.get('win_rate', -999)
        elif objective == 'profit_loss_ratio':
            score = metrics.get('profit_loss_ratio', -999)
        elif objective == 'calmar':
            dd = metrics.get('max_drawdown', 100)
            ret = metrics.get('total_return', -999)
            score = ret / abs(dd) if dd != 0 else -999
        else:
            score = metrics.get('sharpe', -999)

        results.append({
            'params': params,
            'metrics': metrics,
            'score': round(float(score), 4) if score != -999 else -999,
        })

        if score > best_score:
            best_score = score
            best_params = params
            best_result = result

    # 排序
    results.sort(key=lambda x: x['score'], reverse=True)

    return {
        'strategy': strategy_type,
        'objective': objective,
        'param_ranges': param_ranges,
        'total_combinations': len(combinations),
        'best_params': best_params,
        'best_score': round(float(best_score), 4) if best_score != -float('inf') else None,
        'best_result': best_result,
        'top_results': results[:20],  # 前20个
    }


# ─── Brinson绩效归因 ───

def brinson_attribution(portfolio_returns: list, benchmark_returns: list,
                        sector_weights_portfolio: dict, sector_weights_benchmark: dict,
                        sector_returns: dict) -> dict:
    """Brinson绩效归因分析

    分解超额收益为：
    - 配置效应（Asset Allocation）：行业配置权重差异
    - 选股效应（Stock Selection）：行业内选股能力
    - 交互效应（Interaction）：权重与选股的交互

    Args:
        portfolio_returns: 组合收益率序列 [0.01, -0.005, ...]
        benchmark_returns: 基准收益率序列
        sector_weights_portfolio: {行业: 权重} 0-1
        sector_weights_benchmark: {行业: 权重} 0-1
        sector_returns: {行业: 收益率}

    Returns:
        归因结果
    """
    if not portfolio_returns or not benchmark_returns:
        return {'error': '数据不足'}

    total_return = (np.prod([1 + r for r in portfolio_returns]) - 1) * 100
    bench_return = (np.prod([1 + r for r in benchmark_returns]) - 1) * 100
    excess = round(total_return - bench_return, 4)

    # Brinson分解
    allocation_effect = 0
    selection_effect = 0
    interaction_effect = 0
    details = []

    all_sectors = set(list(sector_weights_portfolio.keys()) + list(sector_weights_benchmark.keys()))

    for sector in all_sectors:
        wp = sector_weights_portfolio.get(sector, 0)
        wb = sector_weights_benchmark.get(sector, 0)
        rp = sector_returns.get(sector, 0)
        rb = sector_returns.get(sector, 0)  # 无行业基准收益率时使用自身

        # 配置效应: (Wp - Wb) * Rb
        alloc = (wp - wb) * rb * 100
        # 选股效应: Wb * (Rp - Rb)
        select = wb * (rp - rb) * 100
        # 交互效应: (Wp - Wb) * (Rp - Rb)
        interact = (wp - wb) * (rp - rb) * 100

        allocation_effect += alloc
        selection_effect += select
        interaction_effect += interact

        details.append({
            'sector': sector,
            'portfolio_weight': round(wp, 4),
            'benchmark_weight': round(wb, 4),
            'sector_return': round(rp, 4),
            'allocation_effect': round(alloc, 4),
            'selection_effect': round(select, 4),
            'interaction_effect': round(interact, 4),
        })

    return {
        'total_return': round(total_return, 4),
        'benchmark_return': round(bench_return, 4),
        'excess_return': round(excess, 4),
        'allocation_effect': round(allocation_effect, 4),
        'selection_effect': round(selection_effect, 4),
        'interaction_effect': round(interaction_effect, 4),
        'details': details,
    }


# ─── 多标的并行回测 ───

def multi_asset_backtest(assets_kline: dict, strategy_type: str = 'ma_cross',
                         params: dict = None) -> dict:
    """多标的并行回测

    Args:
        assets_kline: {code: kline_data}
        strategy_type: 策略类型
        params: 策略参数

    Returns:
        各标的结果汇总
    """
    results = {}
    summary_metrics = {
        'total_trades': 0, 'win_rate_avg': 0, 'total_return_avg': 0,
        'max_drawdown_avg': 0, 'sharpe_avg': 0, 'count': 0,
    }

    for code, kline in assets_kline.items():
        result = run_custom_strategy(kline, strategy_type, params)
        results[code] = result
        if 'metrics' in result and result['metrics']:
            m = result['metrics']
            summary_metrics['total_trades'] += m.get('total_trades', 0)
            summary_metrics['win_rate_avg'] += m.get('win_rate', 0)
            summary_metrics['total_return_avg'] += m.get('total_return', 0)
            summary_metrics['max_drawdown_avg'] += m.get('max_drawdown', 0)
            summary_metrics['sharpe_avg'] += m.get('sharpe', 0)
            summary_metrics['count'] += 1

    count = summary_metrics['count']
    if count > 0:
        summary_metrics['win_rate_avg'] = round(summary_metrics['win_rate_avg'] / count, 2)
        summary_metrics['total_return_avg'] = round(summary_metrics['total_return_avg'] / count, 2)
        summary_metrics['max_drawdown_avg'] = round(summary_metrics['max_drawdown_avg'] / count, 2)
        summary_metrics['sharpe_avg'] = round(summary_metrics['sharpe_avg'] / count, 2)

    return {
        'strategy': strategy_type,
        'params': params,
        'results': results,
        'summary': summary_metrics,
    }
