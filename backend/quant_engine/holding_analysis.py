"""持有期收益分析 — 建议持有多久能赚钱"""
import numpy as np
import pandas as pd
from datetime import datetime


def calc_holding_period_analysis(kline_data: list) -> dict:
    """持有期收益分析

    计算不同持有期的收益统计，给出最优持有推荐

    Args:
        kline_data: K线数据 [{day, close, ...}, ...]

    Returns:
        各持有期分析 + 推荐
    """
    if not kline_data or len(kline_data) < 20:
        return {'error': '数据不足(需≥20根K线)'}

    closes = pd.Series([float(d['close']) for d in kline_data if float(d.get('close', 0)) > 0])
    dates = [d['day'] for d in kline_data if float(d.get('close', 0)) > 0]
    daily_ret = closes.pct_change()

    if len(closes) < 60:
        return {'error': '数据不足(需≥60个交易日)'}

    # 定义持有期（交易日）
    periods = {
        '1周': 5,
        '2周': 10,
        '1月': 21,
        '2月': 42,
        '3月': 63,
        '6月': 126,
        '1年': 252,
        '2年': 504,
    }

    results = []
    buy_signals = []  # 买点记录

    for label, days in periods.items():
        if len(closes) <= days:
            continue

        # 滚动持有期收益
        fwd_ret = closes.shift(-days) / closes - 1
        fwd_ret = fwd_ret[:-days]  # 去掉末尾无法计算的

        if len(fwd_ret) < 5:
            continue

        fwd_ret_pct = fwd_ret * 100

        # 统计
        mean_ret = float(fwd_ret_pct.mean())
        median_ret = float(fwd_ret_pct.median())
        std_ret = float(fwd_ret_pct.std())
        min_ret = float(fwd_ret_pct.min())
        max_ret = float(fwd_ret_pct.max())

        # 胜率
        win_rate = float((fwd_ret_pct > 0).mean() * 100)

        # 盈亏比
        wins = fwd_ret_pct[fwd_ret_pct > 0]
        losses = fwd_ret_pct[fwd_ret_pct < 0]
        avg_win = float(wins.mean()) if len(wins) > 0 else 0
        avg_loss = float(losses.mean()) if len(losses) > 0 else 0
        pl_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0

        # 夏普（持有期）
        sharpe = round(mean_ret / std_ret, 2) if std_ret > 0 else 0

        # 最佳入场时机（回看过去N次，看什么位置买最好）
        best_entry = _find_best_entry(closes, days)

        results.append({
            'period': label,
            'trading_days': days,
            'avg_return': round(mean_ret, 2),
            'median_return': round(median_ret, 2),
            'std_return': round(std_ret, 2),
            'min_return': round(min_ret, 2),
            'max_return': round(max_ret, 2),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_loss_ratio': pl_ratio,
            'sharpe': sharpe,
            'best_entry_advice': best_entry,
        })

        # 记录买点信号
        best_fwd = fwd_ret_pct
        for i in range(min(10, len(closes) - days)):
            idx = -(i + 1)
            if idx >= -len(best_fwd):
                buy_signals.append({
                    'date': dates[idx] if idx < len(dates) else '',
                    'buy_price': round(float(closes.iloc[idx]), 4),
                    'holding_days': days,
                    'return_pct': round(float(best_fwd.iloc[idx]), 2),
                })

    if not results:
        return {'error': '数据不足无法分析'}

    # 找出最优持有期（综合胜率+收益+夏普）
    best_period = None
    best_score = -999
    for r in results:
        # 评分：胜率(40%) + 夏普(30%) + 平均收益(30%)
        wr = r['win_rate']
        sp = max(0, r['sharpe'])
        ar = max(0, r['avg_return'])
        score = wr * 0.4 + sp * 20 * 0.3 + ar * 0.3
        if score > best_score:
            best_score = score
            best_period = r

    # 最近建议
    current_price = float(closes.iloc[-1])
    last_date = dates[-1] if dates else ''

    summary = {
        'current_price': current_price,
        'last_date': last_date,
        'total_history_days': len(closes),
        'analysis_start_date': dates[0] if dates else '',
    }

    # 买入持有vs择时对比
    buy_hold_return = round((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0] * 100, 2)

    return {
        'summary': summary,
        'periods_analysis': results,
        'best_period': best_period,
        'buy_hold_return': buy_hold_return,
        'recent_signals': buy_signals,
        'recommendation': {
            'optimal_holding': best_period['period'] if best_period else 'N/A',
            'optimal_win_rate': best_period['win_rate'] if best_period else 0,
            'optimal_avg_return': best_period['avg_return'] if best_period else 0,
            'advice': _generate_advice(best_period, buy_hold_return),
        },
    }


def _find_best_entry(closes: pd.Series, hold_days: int) -> str:
    """找历史最佳入场时机特征"""
    if len(closes) < hold_days * 2:
        return '无足够数据'

    fwd = closes.shift(-hold_days) / closes - 1
    fwd_valid = fwd.dropna()

    if len(fwd_valid) < 10:
        return '无足够数据'

    # 找收益最高的10%买入点特征
    threshold = fwd_valid.quantile(0.9)
    best_entries = fwd_valid[fwd_valid >= threshold]

    # 这些买点对应的价格位置
    entry_indices = [closes.index.get_loc(idx) for idx in best_entries.index if idx in closes.index]
    if not entry_indices:
        return '特征不明显'

    # 看这些最佳买点发生在均线什么位置
    ma20 = closes.rolling(20).mean()
    ma60 = closes.rolling(60).mean()

    below_ma20 = 0
    below_ma60 = 0
    for idx in entry_indices[-20:]:  # 最近20个
        if idx < 60: continue
        price = closes.iloc[idx]
        if price < ma20.iloc[idx]:
            below_ma20 += 1
        if price < ma60.iloc[idx]:
            below_ma60 += 1

    total = min(len(entry_indices[-20:]), 20)
    if total == 0:
        return '数据不足'

    pct_below_ma20 = below_ma20 / total
    pct_below_ma60 = below_ma60 / total

    parts = []
    if pct_below_ma60 > 0.6:
        parts.append(f'MA60下方买入胜率({pct_below_ma60*100:.0f}%)')
    elif pct_below_ma20 > 0.5:
        parts.append(f'MA20下方买入胜率({pct_below_ma20*100:.0f}%)')
    else:
        parts.append('均线附近买入')

    return '建议' + '，'.join(parts)


def _generate_advice(best: dict, buy_hold: float) -> str:
    """生成持有建议"""
    if best is None:
        return '数据不足，无法给出建议'

    period = best['period']
    wr = best['win_rate']
    avg_ret = best['avg_return']
    pl = best['profit_loss_ratio']

    parts = [f'建议持有期: {period}']

    if wr >= 65:
        parts.append(f'历史胜率{wr:.0f}%较高')
    elif wr >= 50:
        parts.append(f'历史胜率{wr:.0f}%一般')
    else:
        parts.append(f'历史胜率{wr:.0f}%偏低，注意风险')

    if avg_ret > 0:
        parts.append(f'平均收益{avg_ret:.1f}%')
    else:
        parts.append(f'平均收益{avg_ret:.1f}%，同等期择时可能更好')

    if pl >= 2:
        parts.append(f'盈亏比{pl}优秀')
    elif pl >= 1:
        parts.append(f'盈亏比{pl}尚可')

    if buy_hold > 0 and best['avg_return'] > buy_hold / 10:
        parts.append('优于简单买入持有')
    elif buy_hold < 0:
        parts.append('整体趋势向下，建议短线操作')

    return '，'.join(parts)


def compare_holding_strategies(kline_data: list) -> dict:
    """对比不同持有策略的收益表现

    对比：不动持有vs定投vs择时(最优持有期)
    """
    if not kline_data or len(kline_data) < 60:
        return {'error': '数据不足'}

    closes = pd.Series([float(d['close']) for d in kline_data if float(d.get('close', 0)) > 0])

    # 买入持有
    buy_hold = round((closes.iloc[-1] / closes.iloc[0] - 1) * 100, 2)

    # 定投（等额周投）
    weekly_amount = 1000
    total_invested = 0
    total_shares = 0
    for i in range(0, len(closes), 5):  # 每5个交易日
        total_invested += weekly_amount
        total_shares += weekly_amount / closes.iloc[i]
    dca_value = round(total_shares * closes.iloc[-1], 2)
    dca_return = round((dca_value - total_invested) / total_invested * 100, 2)

    # 最优持有期滚动操作
    analysis = calc_holding_period_analysis(kline_data)
    best_period = analysis.get('best_period', {})
    best_trade_return = best_period.get('avg_return', 0) if best_period else 0

    return {
        'buy_hold_return': buy_hold,
        'dca_return': dca_return,
        'dca_final_value': dca_value,
        'dca_invested': int(total_invested),
        'optimal_hold_trade_return': best_trade_return,
        'optimal_hold_period': best_period.get('period', 'N/A') if best_period else 'N/A',
        'recommendation': '定投' if dca_return > buy_hold else ('持有不动' if buy_hold > dca_return else '择时操作'),
    }
