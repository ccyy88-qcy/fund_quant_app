"""信号判定引擎 — MA10+MA60规则 + 估值豁免"""
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from .indicators import calc_ma
from .risk_metrics import current_drawdown


def calc_signal_v4(kline_data: list, pe_pct: Optional[float] = None,
                   pb_pct: Optional[float] = None,
                   is_fund: bool = False) -> dict:
    """基于MA10+MA60规则的信号判定（v4版）

    规则要点：
    - 估值低位（PE/PB≤30%）禁止卖出
    - PE≥70%或PB≥70%可止盈
    - 所有卖出标注类型（止盈/止损）
    - 5档估值评级
    """
    if not kline_data or len(kline_data) < 20:
        return {
            'signal': '数据不足', 'detail': '数据不足(需≥20根K线)',
            'type': 'hold', 'color': '#9E9E9E',
            'pe_rating': _get_pe_rating(pe_pct),
            'pb_rating': _get_pe_rating(pb_pct),
        }

    closes = np.array([float(d['close']) for d in kline_data if float(d.get('close', 0)) > 0])
    volumes = np.array([float(d.get('volume', 0)) for d in kline_data])
    highs = np.array([float(d['high']) for d in kline_data])

    closes_s = pd.Series(closes)

    # 计算均线
    ma10 = calc_ma(closes_s, 10).iloc[-1]
    ma60 = calc_ma(closes_s, 60).iloc[-1]
    current_price = closes[-1]

    # 价格相对MA10位置
    pos_above = current_price > ma10
    ma10_above_ma60 = ma10 > ma60

    # 量比
    vol_5d = np.mean(volumes[-5:]) if len(volumes) >= 5 else 0
    vol_20d = np.mean(volumes[-20:]) if len(volumes) >= 20 else vol_5d
    vol_ratio = round(vol_5d / vol_20d, 2) if vol_20d > 0 else 0

    # 近60日回落
    recent_high = np.max(highs[-60:]) if len(highs) >= 60 else np.max(highs)
    drop_from_high = round((recent_high - current_price) / recent_high * 100, 2)

    # 估值判断
    is_exempt = (pe_pct is not None and pe_pct <= 30) or (pb_pct is not None and pb_pct <= 30)

    # 信号判定
    buy_conditions = 0
    if (pe_pct is not None and pe_pct <= 30) or (pb_pct is not None and pb_pct <= 30):
        buy_conditions += 1
    if pos_above and ma10_above_ma60:
        buy_conditions += 1
    if vol_ratio >= 1.0 or vol_ratio == 0:  # 无量能数据(场外基金)默认满足
        buy_conditions += 1

    sell_reason = None
    sell_type = None

    if not is_exempt:
        # 条件1：估值止盈
        if (pe_pct is not None and pe_pct >= 70) or (pb_pct is not None and pb_pct >= 70):
            sell_reason = '高估止盈'
            sell_type = '止盈'
        # 条件2：趋势减仓
        if not sell_reason and ((pe_pct is not None and pe_pct >= 50) or (pb_pct is not None and pb_pct >= 50)):
            if not pos_above and not ma10_above_ma60:
                sell_reason = '趋势减仓'
                sell_type = '止损'
        # 条件3：高位回落
        if not sell_reason and drop_from_high >= 10 and ((pe_pct is not None and pe_pct >= 50) or (pb_pct is not None and pb_pct >= 50)):
            sell_reason = '高位回落止盈'
            sell_type = '止盈'

    # 信号输出
    if sell_reason:
        signal = f'卖出·{sell_reason}'
        signal_type = 'sell'
        color = '#F44336'
    elif buy_conditions >= 3:
        signal = '低估买入' if is_exempt else '趋势买入'
        signal_type = 'buy'
        color = '#4CAF50'
    elif is_exempt and buy_conditions >= 1:
        signal = '持有·估值低位'
        signal_type = 'hold'
        color = '#FF9800'
    elif buy_conditions >= 2:
        signal = '持有·部分达标'
        signal_type = 'hold'
        color = '#FF9800'
    else:
        signal = '观望·条件不足'
        signal_type = 'wait'
        color = '#9E9E9E'

    return {
        'signal': signal,
        'type': signal_type,
        'color': color,
        'detail': f"价格{'≥' if pos_above else '<'}MA10 | MA10{'≥' if ma10_above_ma60 else '<'}MA60 | 量比{vol_ratio} | 回落{drop_from_high}%",
        'price': round(float(current_price), 4),
        'ma10': round(float(ma10), 4),
        'ma60': round(float(ma60), 4),
        'pos_above_ma10': bool(pos_above),
        'ma10_above_ma60': bool(ma10_above_ma60),
        'vol_ratio': vol_ratio,
        'drop_from_high': drop_from_high,
        'pe_rating': _get_pe_rating(pe_pct),
        'pb_rating': _get_pe_rating(pb_pct),
        'is_exempt': is_exempt,
    }


def run_backtest(kline_data: list, pe_pct_history: list = None) -> dict:
    """历史回测：逐日判定信号，统计绩效"""
    if not kline_data or len(kline_data) < 60:
        return {'error': '数据不足(需≥60根K线)'}

    closes = np.array([float(d['close']) for d in kline_data])
    dates = [d['day'] for d in kline_data]
    closes_s = pd.Series(closes)

    # 逐日信号
    trades = []
    position = 0  # 0=空仓, 1=持有
    entry_price = 0
    entry_date = ''
    trade_records = []
    signals_over_time = []

    ma10 = calc_ma(closes_s, 10)
    ma60 = calc_ma(closes_s, 60)

    for i in range(60, len(closes)):
        current_price = closes[i]
        current_ma10 = ma10.iloc[i]
        current_ma60 = ma60.iloc[i]

        pos_above = current_price > current_ma10
        cross = current_ma10 > current_ma60

        # 模拟信号（简化版，不含估值）
        buy_signal = pos_above and cross
        sell_signal = not pos_above and not cross

        signals_over_time.append({
            'date': dates[i],
            'price': round(float(current_price), 4),
            'ma10': round(float(current_ma10), 4),
            'ma60': round(float(current_ma60), 4),
            'signal': 'buy' if buy_signal and not position else ('sell' if sell_signal and position else ''),
        })

        if buy_signal and position == 0:
            position = 1
            entry_price = current_price
            entry_date = dates[i]
        elif sell_signal and position == 1:
            ret = (current_price - entry_price) / entry_price * 100
            trade_records.append({
                'entry_date': entry_date,
                'exit_date': dates[i],
                'entry_price': round(float(entry_price), 4),
                'exit_price': round(float(current_price), 4),
                'return': round(float(ret), 2),
            })
            position = 0

    # 计算绩效
    if not trade_records:
        return {'trades': [], 'metrics': {'total_trades': 0}, 'signals': signals_over_time}

    returns = [t['return'] for t in trade_records]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]

    metrics = {
        'total_trades': len(trade_records),
        'win_rate': round(len(wins) / len(returns) * 100, 2) if returns else 0,
        'avg_win': round(np.mean(wins), 2) if wins else 0,
        'avg_loss': round(np.mean(losses), 2) if losses else 0,
        'profit_loss_ratio': round(abs(np.mean(wins) / np.mean(losses)), 2) if wins and losses else 0,
        'total_return': round(sum(returns), 2),
        'max_drawdown': round(_calc_backtest_dd(trade_records), 2),
    }

    return {'trades': trade_records, 'metrics': metrics, 'signals': signals_over_time}


def _calc_backtest_dd(trades: list) -> float:
    """计算回测最大回撤"""
    if not trades:
        return 0
    equity = [100]
    for t in trades:
        equity.append(equity[-1] * (1 + t['return'] / 100))
    peak = np.maximum.accumulate(equity)
    dd = (np.array(equity) - peak) / peak
    return float(np.min(dd) * 100)


def _get_pe_rating(pct: Optional[float]) -> str:
    """估值评级"""
    if pct is None:
        return 'N/A'
    if pct <= 15:
        return '极度低估'
    elif pct <= 30:
        return '低估'
    elif pct <= 50:
        return '中性'
    elif pct <= 70:
        return '高估'
    else:
        return '极度高估'
