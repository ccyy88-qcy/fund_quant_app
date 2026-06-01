"""
波动率策略模块
- 历史波动率计算 (5/10/20/60日)
- HV分位数 (滚动N日)
- 波动率均值回归信号
- 波动率锥 (volatility cone)
- 信号历史回测
"""
import numpy as np
import pandas as pd
from typing import Optional, List, Union


def calc_hv(
    df: pd.DataFrame,
    periods: Optional[List[int]] = None,
    price_col: str = 'close'
) -> dict:
    """
    计算历史波动率 (Historical Volatility)
    参数:
        df: DataFrame, 需含 price_col 列
        periods: 周期列表, 默认 [5, 10, 20, 60]
        price_col: 价格列名
    返回:
        dict: {period: Series列表(rv值list), 'dates': dates列表}
    """
    if periods is None:
        periods = [5, 10, 20, 60]
    prices = df[price_col].values
    log_ret = np.diff(np.log(prices))
    dates = df.index[1:].tolist()
    result = {}
    for p in periods:
        if len(log_ret) < p:
            rv = [np.nan] * len(log_ret)
        else:
            rv_list = []
            for i in range(len(log_ret)):
                if i < p - 1:
                    rv_list.append(np.nan)
                else:
                    rv_list.append(float(np.std(log_ret[i - p + 1:i + 1], ddof=1) * np.sqrt(252)))
            rv = rv_list
        result[str(p)] = rv
    return {
        'dates': [str(d) for d in dates],
        'hv': result
    }


def calc_hv_percentile(
    df: pd.DataFrame,
    period: int = 20,
    rolling_window: int = 252,
    price_col: str = 'close'
) -> dict:
    """
    计算HV分位数 (滚动N日)
    参数:
        df: DataFrame
        period: HV计算周期
        rolling_window: 滚动窗口
        price_col: 价格列
    返回:
        dict: {dates, hv, percentile}
    """
    prices = df[price_col].values
    log_ret = np.diff(np.log(prices))
    hv_list = []
    for i in range(len(log_ret)):
        if i < period - 1:
            hv_list.append(np.nan)
        else:
            hv_list.append(float(np.std(log_ret[i - period + 1:i + 1], ddof=1) * np.sqrt(252)))
    hv_arr = np.array(hv_list)
    pct_list = []
    for i in range(len(hv_arr)):
        if i < rolling_window or np.isnan(hv_arr[i]):
            pct_list.append(np.nan)
        else:
            window = hv_arr[i - rolling_window:i]
            valid = window[~np.isnan(window)]
            if len(valid) == 0:
                pct_list.append(np.nan)
            else:
                p = float(np.sum(valid < hv_arr[i]) / len(valid))
                pct_list.append(round(p, 4))
    dates = df.index[1:].tolist()
    return {
        'dates': [str(d) for d in dates],
        'hv': [round(x, 4) if not np.isnan(x) else None for x in hv_list],
        'hv_percentile': [round(x, 4) if not np.isnan(x) else None for x in pct_list]
    }


def calc_vol_mean_reversion_signal(
    df: pd.DataFrame,
    period: int = 20,
    rolling_window: int = 252,
    long_threshold: float = 0.2,
    short_threshold: float = 0.8,
    price_col: str = 'close'
) -> dict:
    """
    波动率均值回归信号
    HV分位数 < long_threshold -> 做多波动率 (买入)
    HV分位数 > short_threshold -> 做空波动率 (卖出)
    返回:
        dict: {dates, hv, percentile, signal}
            signal: 1做多波动率, -1做空波动率, 0无信号
    """
    hvp = calc_hv_percentile(df, period, rolling_window, price_col)
    dates = hvp['dates']
    pct_arr = hvp['hv_percentile']
    signals = []
    for p in pct_arr:
        if p is None:
            signals.append(0)
        elif p < long_threshold:
            signals.append(1)
        elif p > short_threshold:
            signals.append(-1)
        else:
            signals.append(0)
    return {
        'dates': dates,
        'hv': hvp['hv'],
        'hv_percentile': pct_arr,
        'signal': signals
    }


def calc_volatility_cone(
    df: pd.DataFrame,
    periods: Optional[List[int]] = None,
    percentile_levels: Optional[List[float]] = None,
    price_col: str = 'close'
) -> dict:
    """
    波动率锥 (Volatility Cone)
    不同持有周期下的波动率分位数分布
    参数:
        df: DataFrame
        periods: 周期列表, 默认 [5, 10, 20, 40, 60, 120]
        percentile_levels: 分位数水平, 默认 [0.05, 0.25, 0.50, 0.75, 0.95]
        price_col: 价格列
    返回:
        dict: {period: {percentile: value, ...}, ...}
    """
    if periods is None:
        periods = [5, 10, 20, 40, 60, 120]
    if percentile_levels is None:
        percentile_levels = [0.05, 0.25, 0.50, 0.75, 0.95]
    prices = df[price_col].values
    log_ret = np.diff(np.log(prices))
    cone = {}
    for p in periods:
        if len(log_ret) < p:
            cone[str(p)] = {str(round(lv * 100, 0)): None for lv in percentile_levels}
            continue
        hv_list = []
        for i in range(len(log_ret) - p + 1):
            hv = np.std(log_ret[i:i + p], ddof=1) * np.sqrt(252 / p) * np.sqrt(252)
            hv_list.append(hv)
        # 这里使用年化波动率: std * sqrt(252/p) * sqrt(252) = std * 252/sqrt(p) ... 
        # 更正: 日收益率年化: std(log_ret_window) * sqrt(252)
        # 对于p日收益率年化: std(log_ret_window) * sqrt(252/p) 这是错误的
        # 实际上HV(p日窗口) = std_of_p_daily_returns * sqrt(252) 然后乘以 sqrt(252/p) 
        # 重新算:
        hv_list2 = []
        for i in range(len(log_ret) - p + 1):
            hv = np.std(log_ret[i:i + p], ddof=1) * np.sqrt(252)
            hv_list2.append(hv)
        valid = [x for x in hv_list2 if not np.isnan(x)]
        if not valid:
            cone[str(p)] = {str(int(lv * 100)): None for lv in percentile_levels}
        else:
            vals = np.percentile(valid, [lv * 100 for lv in percentile_levels])
            cone[str(p)] = {
                str(int(percentile_levels[i] * 100)): round(float(vals[i]), 4)
                for i in range(len(percentile_levels))
            }
    return cone


def backtest_vol_signal(
    df: pd.DataFrame,
    period: int = 20,
    rolling_window: int = 252,
    long_threshold: float = 0.2,
    short_threshold: float = 0.8,
    price_col: str = 'close',
    transaction_cost: float = 0.001
) -> dict:
    """
    波动率信号历史回测
    假设: 做多波动率=买入标的, 做空波动率=空仓/做空
    返回: dict
    """
    sig_data = calc_vol_mean_reversion_signal(df, period, rolling_window, long_threshold, short_threshold, price_col)
    signals = sig_data['signal']
    prices = df[price_col].values
    # 对齐信号索引 (log_ret 比价格少1)
    # 信号基于 log_ret 索引, 交易价格用对应日期
    # 信号 indices: 0..len(signals)-1, 对应价格 indices: 1..len(prices)-1
    trades = []
    position = 0  # 0:空仓, 1:多头, -1:空头
    entry_price = None
    entry_date = None
    entry_idx = None
    win_count = 0
    loss_count = 0
    total_return = 1.0
    returns_list = []
    signal_dates = sig_data['dates']
    for i, sig in enumerate(signals):
        if sig is None or sig == 0:
            if position != 0:
                # 平仓
                exit_price = prices[i + 1]
                ret = (exit_price / entry_price - 1) * position - transaction_cost
                total_return *= (1 + ret)
                returns_list.append(ret)
                if ret > 0:
                    win_count += 1
                else:
                    loss_count += 1
                trades.append({
                    'entry_date': str(entry_date),
                    'exit_date': signal_dates[i],
                    'entry_price': round(float(entry_price), 4),
                    'exit_price': round(float(exit_price), 4),
                    'direction': 'long' if position == 1 else 'short',
                    'return': round(float(ret), 4)
                })
                position = 0
                entry_price = None
                entry_date = None
            continue
        if position == 0:
            position = sig
            entry_price = prices[i + 1]
            entry_date = signal_dates[i]
            entry_idx = i
        elif position != sig:
            # 反向信号 -> 平仓再开仓
            exit_price = prices[i + 1]
            ret = (exit_price / entry_price - 1) * position - transaction_cost
            total_return *= (1 + ret)
            returns_list.append(ret)
            if ret > 0:
                win_count += 1
            else:
                loss_count += 1
            trades.append({
                'entry_date': str(entry_date),
                'exit_date': signal_dates[i],
                'entry_price': round(float(entry_price), 4),
                'exit_price': round(float(exit_price), 4),
                'direction': 'long' if position == 1 else 'short',
                'return': round(float(ret), 4)
            })
            position = sig
            entry_price = prices[i + 1]
            entry_date = signal_dates[i]
    # 最后一笔持仓在最后一日平仓
    if position != 0:
        exit_price = prices[-1]
        ret = (exit_price / entry_price - 1) * position - transaction_cost
        total_return *= (1 + ret)
        returns_list.append(ret)
        if ret > 0:
            win_count += 1
        else:
            loss_count += 1
        trades.append({
            'entry_date': str(entry_date),
            'exit_date': str(df.index[-1]),
            'entry_price': round(float(entry_price), 4),
            'exit_price': round(float(exit_price), 4),
            'direction': 'long' if position == 1 else 'short',
            'return': round(float(ret), 4)
        })
    total_trades = len(trades)
    win_rate = round(win_count / total_trades, 4) if total_trades > 0 else 0.0
    avg_win = round(np.mean([t['return'] for t in trades if t['return'] > 0]), 4) if win_count > 0 else 0.0
    avg_loss = round(np.mean([t['return'] for t in trades if t['return'] <= 0]), 4) if loss_count > 0 else 0.0
    profit_factor = round(abs(sum(t['return'] for t in trades if t['return'] > 0) /
                             sum(t['return'] for t in trades if t['return'] < 0)), 4) if loss_count > 0 else float('inf')
    sharpe = round(np.mean(returns_list) / np.std(returns_list, ddof=1) * np.sqrt(252), 4) if len(returns_list) > 1 and np.std(returns_list, ddof=1) > 0 else 0.0
    return {
        'total_return': round(float(total_return - 1), 4),
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate': win_rate,
        'avg_win_pct': avg_win,
        'avg_loss_pct': avg_loss,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe,
        'trades': trades
    }
