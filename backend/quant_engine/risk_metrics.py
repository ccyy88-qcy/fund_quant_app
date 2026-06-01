"""风险/收益指标计算"""
import numpy as np
import pandas as pd

def annual_return(series: pd.Series, trading_days: int = 250) -> float:
    """年化收益率"""
    if len(series) < 2:
        return None
    total_return = series.iloc[-1] / series.iloc[0]
    years = len(series) / trading_days
    if years <= 0:
        return None
    return round((total_return ** (1 / years) - 1) * 100, 2)

def max_drawdown(series: pd.Series) -> float:
    """最大回撤（百分比）"""
    if len(series) < 2:
        return None
    peak = series.expanding().max()
    dd = (series - peak) / peak
    return round(float(dd.min() * 100), 2)

def current_drawdown(series: pd.Series) -> float:
    """当前回撤率"""
    if len(series) < 2:
        return None
    ath = series.max()
    current = series.iloc[-1]
    return round((current - ath) / ath * 100, 2)

def annual_volatility(series: pd.Series, trading_days: int = 250) -> float:
    """年化波动率（百分比）"""
    if len(series) < 5:
        return None
    daily_ret = series.pct_change().dropna()
    if len(daily_ret) < 2:
        return None
    return round(float(daily_ret.std() * np.sqrt(trading_days) * 100), 2)

def sharpe_ratio(series: pd.Series, risk_free: float = 2.5, trading_days: int = 250) -> float:
    """夏普比率"""
    ann_ret = annual_return(series, trading_days)
    ann_vol = annual_volatility(series, trading_days)
    if ann_ret is None or ann_vol is None or ann_vol == 0:
        return None
    return round((ann_ret - risk_free) / ann_vol, 2)

def win_rate(series: pd.Series) -> float:
    """日胜率（上涨天数占比）"""
    if len(series) < 2:
        return None
    daily_ret = series.pct_change().dropna()
    wins = (daily_ret > 0).sum()
    return round(wins / len(daily_ret) * 100, 2)

def profit_loss_ratio(series: pd.Series) -> float:
    """盈亏比"""
    if len(series) < 2:
        return None
    daily_ret = series.pct_change().dropna()
    gains = daily_ret[daily_ret > 0]
    losses = daily_ret[daily_ret < 0]
    if len(losses) == 0 or gains.mean() == 0:
        return None
    return round(float(gains.mean() / abs(losses.mean())), 2)

def calc_risk_metrics(series: pd.Series) -> dict:
    """计算全套风险/收益指标"""
    return {
        'annual_return': annual_return(series),
        'max_drawdown': max_drawdown(series),
        'current_drawdown': current_drawdown(series),
        'volatility': annual_volatility(series),
        'sharpe': sharpe_ratio(series),
        'win_rate': win_rate(series),
        'profit_loss_ratio': profit_loss_ratio(series),
    }
