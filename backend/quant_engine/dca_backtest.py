"""智能定投回测引擎 — 定期定额/均线/估值定投 + 目标止盈/移动止盈 + 策略对比"""
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple


# ═══════════════════════════════════════════════
# 1. 定期定额定投
# ═══════════════════════════════════════════════

def dca_fixed_amount(
    nav_series: pd.Series,
    frequency_days: int = 1,
    amount_per_period: float = 1000.0,
    start_idx: int = 0,
    end_idx: Optional[int] = None,
) -> Dict[str, Any]:
    """
    定期定额定投回测。
    参数:
      nav_series: 净值序列（每日）
      frequency_days: 定投间隔天数
      amount_per_period: 每期定投金额
      start_idx: 开始定投的索引位置
      end_idx: 结束定投的索引位置（None=全部）
    返回:
      { "total_invest": float, "total_shares": float, "final_value": float,
        "total_return_pct": float, "annual_return_pct": float,
        "avg_cost": float, "current_nav": float, "nav_curve": [...],
        "investment_log": [...] }
    """
    values = nav_series.values
    n = len(values)
    if end_idx is None or end_idx > n:
        end_idx = n
    if start_idx >= end_idx:
        return {"error": "start_idx >= end_idx"}

    total_shares = 0.0
    total_invest = 0.0
    nav_curve = []       # 每日总市值
    invest_dates = []    # 定投日期日志

    for i in range(n):
        nav = values[i]
        # 定投日：从start_idx开始，间隔frequency_days天
        if i >= start_idx and i < end_idx and (i - start_idx) % frequency_days == 0:
            shares_bought = amount_per_period / nav
            total_shares += shares_bought
            total_invest += amount_per_period
            invest_dates.append({
                "date_idx": i,
                "nav": round(float(nav), 4),
                "invest_amount": round(amount_per_period, 4),
                "shares_bought": round(shares_bought, 4),
                "cumulative_shares": round(total_shares, 4),
                "cumulative_invest": round(total_invest, 4),
            })

        current_value = total_shares * nav
        nav_curve.append(round(float(current_value), 4))

    final_nav = float(values[-1])
    final_value = float(total_shares * final_nav)
    total_return_pct = ((final_value - total_invest) / total_invest * 100) if total_invest > 0 else 0.0
    years = (end_idx - start_idx) / 250.0
    annual_return_pct = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    avg_cost = (total_invest / total_shares) if total_shares > 0 else 0.0

    return {
        "strategy": "定期定额定投",
        "params": {
            "frequency_days": frequency_days,
            "amount_per_period": amount_per_period,
        },
        "total_invest": round(total_invest, 4),
        "total_shares": round(total_shares, 4),
        "final_value": round(final_value, 4),
        "total_return_pct": round(total_return_pct, 4),
        "annual_return_pct": round(annual_return_pct, 4),
        "avg_cost": round(avg_cost, 4),
        "current_nav": round(final_nav, 4),
        "nav_curve": nav_curve,
        "investment_log": invest_dates,
    }


# ═══════════════════════════════════════════════
# 2. 均线定投
# ═══════════════════════════════════════════════

def dca_ma_strategy(
    nav_series: pd.Series,
    ma_period: int = 20,
    base_amount: float = 1000.0,
    frequency_days: int = 1,
    threshold_pct: float = 5.0,
    multiplier: float = 2.0,
    start_idx: int = 0,
    end_idx: Optional[int] = None,
) -> Dict[str, Any]:
    """
    均线定投：价格低于MA均线threshold_pct%时加大定投金额。
    当 (close/ma - 1) < -threshold_pct/100 时，定投金额 = base_amount * multiplier
    否则 = base_amount * 1.0
    参数:
      nav_series: 净值序列
      ma_period: 均线周期
      base_amount: 基准定投金额
      frequency_days: 定投间隔
      threshold_pct: 偏离阈值百分比
      multiplier: 低于阈值时的倍数
    返回: 同dca_fixed_amount
    """
    values = nav_series.values
    ma = nav_series.rolling(window=ma_period).mean().values
    n = len(values)
    if end_idx is None or end_idx > n:
        end_idx = n
    if start_idx >= end_idx:
        return {"error": "start_idx >= end_idx"}

    total_shares = 0.0
    total_invest = 0.0
    nav_curve = []
    invest_log = []

    for i in range(n):
        nav = values[i]
        if i >= start_idx and i < end_idx and (i - start_idx) % frequency_days == 0:
            # 计算均线偏离
            if i >= ma_period and not np.isnan(ma[i]):
                deviation = (nav / ma[i]) - 1.0
                if deviation < -threshold_pct / 100.0:
                    invest_amount = base_amount * multiplier
                else:
                    invest_amount = base_amount
            else:
                invest_amount = base_amount

            shares_bought = invest_amount / nav
            total_shares += shares_bought
            total_invest += invest_amount
            invest_log.append({
                "date_idx": i,
                "nav": round(float(nav), 4),
                "ma": round(float(ma[i]), 4) if i < ma_period or np.isnan(ma[i]) else round(float(ma[i]), 4),
                "invest_amount": round(invest_amount, 4),
                "deviation_pct": round(float(deviation * 100), 4) if 'deviation' in dir() and i >= ma_period and not np.isnan(ma[i]) else None,
                "shares_bought": round(shares_bought, 4),
            })

        current_value = total_shares * nav
        nav_curve.append(round(float(current_value), 4))

    final_nav = float(values[-1])
    final_value = float(total_shares * final_nav)
    total_return_pct = ((final_value - total_invest) / total_invest * 100) if total_invest > 0 else 0.0
    years = (end_idx - start_idx) / 250.0
    annual_return_pct = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    avg_cost = (total_invest / total_shares) if total_shares > 0 else 0.0

    return {
        "strategy": "均线定投",
        "params": {
            "ma_period": ma_period,
            "base_amount": base_amount,
            "frequency_days": frequency_days,
            "threshold_pct": threshold_pct,
            "multiplier": multiplier,
        },
        "total_invest": round(total_invest, 4),
        "total_shares": round(total_shares, 4),
        "final_value": round(final_value, 4),
        "total_return_pct": round(total_return_pct, 4),
        "annual_return_pct": round(annual_return_pct, 4),
        "avg_cost": round(avg_cost, 4),
        "current_nav": round(final_nav, 4),
        "nav_curve": nav_curve,
        "investment_log": invest_log,
    }


# ═══════════════════════════════════════════════
# 3. 估值定投
# ═══════════════════════════════════════════════

def dca_valuation_strategy(
    nav_series: pd.Series,
    percentile_series: pd.Series,
    base_amount: float = 1000.0,
    frequency_days: int = 1,
    lower_threshold: float = 30.0,
    upper_threshold: float = 70.0,
    add_multiplier: float = 2.0,
    reduce_multiplier: float = 0.5,
    enable_take_profit: bool = False,
    take_profit_target: float = 20.0,
    start_idx: int = 0,
    end_idx: Optional[int] = None,
) -> Dict[str, Any]:
    """
    估值定投：PE/PB分位低于阈值时加仓，高于阈值时减仓/止盈。
    分位值 < lower_threshold: 加仓 (base * add_multiplier)
    分位值 > upper_threshold: 减仓 (base * reduce_multiplier) 或触发止盈
    参数:
      nav_series: 净值序列
      percentile_series: 对应的估值分位值序列（0-100）
      base_amount: 基准定投金额
      frequency_days: 定投间隔
      lower_threshold: 加仓阈值（分位低于此值加仓）
      upper_threshold: 减仓阈值（分位高于此值减仓）
      add_multiplier: 加仓倍数
      reduce_multiplier: 减仓比例
      enable_take_profit: 是否启用止盈
      take_profit_target: 止盈目标收益率(%)
    返回: 同dca_fixed_amount，加上止盈触发记录
    """
    values = nav_series.values
    pcts = percentile_series.values
    n = len(values)
    if end_idx is None or end_idx > n:
        end_idx = n
    if start_idx >= end_idx:
        return {"error": "start_idx >= end_idx"}

    total_shares = 0.0
    total_invest = 0.0
    total_sold_value = 0.0
    nav_curve = []
    invest_log = []
    take_profit_events = []

    for i in range(n):
        nav = values[i]
        if i >= start_idx and i < end_idx and (i - start_idx) % frequency_days == 0:
            pct_val = pcts[i] if i < len(pcts) and not np.isnan(pcts[i]) else 50.0

            if pct_val < lower_threshold:
                invest_amount = base_amount * add_multiplier
            elif pct_val > upper_threshold:
                invest_amount = base_amount * reduce_multiplier
                # 止盈检查
                if enable_take_profit and total_invest > 0 and total_shares > 0:
                    unrealized_return = (nav * total_shares - total_invest) / total_invest * 100
                    if unrealized_return >= take_profit_target:
                        sold_value = total_shares * nav
                        total_sold_value += sold_value
                        take_profit_events.append({
                            "date_idx": i,
                            "nav": round(float(nav), 4),
                            "shares_sold": round(total_shares, 4),
                            "sold_value": round(sold_value, 4),
                            "return_pct": round(unrealized_return, 4),
                        })
                        total_shares = 0.0  # 清仓
                        invest_amount = 0.0  # 止盈后不投
            else:
                invest_amount = base_amount

            if invest_amount > 0:
                shares_bought = invest_amount / nav
                total_shares += shares_bought
                total_invest += invest_amount
                invest_log.append({
                    "date_idx": i,
                    "nav": round(float(nav), 4),
                    "percentile": round(float(pct_val), 4),
                    "invest_amount": round(invest_amount, 4),
                    "shares_bought": round(shares_bought, 4),
                    "total_shares": round(total_shares, 4),
                })

        current_value = total_shares * nav + total_sold_value
        nav_curve.append(round(float(current_value), 4))

    final_nav = float(values[-1])
    final_value = float(total_shares * final_nav + total_sold_value)
    total_return_pct = ((final_value - total_invest) / total_invest * 100) if total_invest > 0 else 0.0
    years = (end_idx - start_idx) / 250.0
    annual_return_pct = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    avg_cost = (total_invest / total_shares) if total_shares > 0 else 0.0

    return {
        "strategy": "估值定投",
        "params": {
            "base_amount": base_amount,
            "frequency_days": frequency_days,
            "lower_threshold": lower_threshold,
            "upper_threshold": upper_threshold,
            "add_multiplier": add_multiplier,
            "reduce_multiplier": reduce_multiplier,
            "enable_take_profit": enable_take_profit,
            "take_profit_target": take_profit_target,
        },
        "total_invest": round(total_invest, 4),
        "total_shares": round(total_shares, 4),
        "final_value": round(final_value, 4),
        "total_return_pct": round(total_return_pct, 4),
        "annual_return_pct": round(annual_return_pct, 4),
        "avg_cost": round(avg_cost, 4),
        "current_nav": round(final_nav, 4),
        "nav_curve": nav_curve,
        "investment_log": invest_log,
        "take_profit_events": take_profit_events,
        "total_sold_value": round(total_sold_value, 4),
    }


# ═══════════════════════════════════════════════
# 4. 目标止盈
# ═══════════════════════════════════════════════

def dca_target_take_profit(
    nav_series: pd.Series,
    base_dca_func: callable,
    target_return: float = 20.0,
    **dca_kwargs,
) -> Dict[str, Any]:
    """
    目标止盈定投：在基础定投策略上叠加目标止盈（达到目标收益自动卖出）。
    参数:
      nav_series: 净值序列
      base_dca_func: 基础定投函数（dca_fixed_amount / dca_ma_strategy / dca_valuation_strategy）
      target_return: 目标收益率(%)
      **dca_kwargs: 传递给基础定投函数的参数
    返回:
      { "strategy": "目标止盈-{基础策略}", "total_return_pct": float, ... }
    """
    # 先用基础策略跑一次获取投资日志
    base_result = base_dca_func(nav_series=nav_series, **dca_kwargs)

    values = nav_series.values
    n = len(values)
    invest_log = base_result.get('investment_log', [])

    # 模拟带止盈的执行
    total_shares = 0.0
    total_invest = 0.0
    total_sold_value = 0.0
    nav_curve = []
    tp_events = []

    # 构建定投日索引集
    invest_idx_set = {e['date_idx'] for e in invest_log}

    for i in range(n):
        nav = values[i]
        # 定投日
        if i in invest_idx_set:
            invest_info = [e for e in invest_log if e['date_idx'] == i]
            if invest_info:
                amount = invest_info[0].get('invest_amount', 1000)
            else:
                amount = 1000
            shares_bought = amount / nav
            total_shares += shares_bought
            total_invest += amount

        # 止盈检查
        if total_invest > 0 and total_shares > 0:
            unrealized_return = (nav * total_shares + total_sold_value - total_invest) / total_invest * 100
            if unrealized_return >= target_return:
                sold_value = total_shares * nav
                total_sold_value += sold_value
                tp_events.append({
                    "date_idx": i,
                    "nav": round(float(nav), 4),
                    "shares_sold": round(total_shares, 4),
                    "sold_value": round(sold_value, 4),
                    "return_pct": round(unrealized_return, 4),
                })
                total_shares = 0.0

        current_value = total_shares * nav + total_sold_value
        nav_curve.append(round(float(current_value), 4))

    final_nav = float(values[-1])
    final_value = float(total_shares * final_nav + total_sold_value)
    total_return_pct = ((final_value - total_invest) / total_invest * 100) if total_invest > 0 else 0.0
    years = n / 250.0
    annual_return_pct = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    avg_cost = (total_invest / total_shares) if total_shares > 0 else 0.0

    return {
        "strategy": f"目标止盈-{base_result.get('strategy', '定投')}",
        "target_return": target_return,
        "params": base_result.get('params', dca_kwargs),
        "total_invest": round(total_invest, 4),
        "total_shares": round(total_shares, 4),
        "final_value": round(final_value, 4),
        "total_return_pct": round(total_return_pct, 4),
        "annual_return_pct": round(annual_return_pct, 4),
        "avg_cost": round(avg_cost, 4),
        "current_nav": round(final_nav, 4),
        "nav_curve": nav_curve,
        "take_profit_events": tp_events,
        "total_sold_value": round(total_sold_value, 4),
    }


# ═══════════════════════════════════════════════
# 5. 移动止盈
# ═══════════════════════════════════════════════

def dca_trailing_stop_profit(
    nav_series: pd.Series,
    base_dca_func: callable,
    trailing_drawdown: float = 10.0,
    **dca_kwargs,
) -> Dict[str, Any]:
    """
    移动止盈定投：从最高点回落X%时止盈。
    参数:
      nav_series: 净值序列
      base_dca_func: 基础定投函数
      trailing_drawdown: 回落百分比触发止盈
    返回: 同dca_target_take_profit
    """
    base_result = base_dca_func(nav_series=nav_series, **dca_kwargs)
    values = nav_series.values
    n = len(values)
    invest_log = base_result.get('investment_log', [])
    invest_idx_set = {e['date_idx'] for e in invest_log}

    total_shares = 0.0
    total_invest = 0.0
    total_sold_value = 0.0
    nav_curve = []
    tp_events = []
    peak_value = 0.0

    for i in range(n):
        nav = values[i]
        if i in invest_idx_set:
            invest_info = [e for e in invest_log if e['date_idx'] == i]
            amount = invest_info[0].get('invest_amount', 1000) if invest_info else 1000
            shares_bought = amount / nav
            total_shares += shares_bought
            total_invest += amount

        current_portfolio = total_shares * nav + total_sold_value
        if current_portfolio > peak_value:
            peak_value = current_portfolio

        # 移动止盈检查
        if total_invest > 0 and total_shares > 0 and peak_value > total_invest:
            drawdown_from_peak = (peak_value - current_portfolio) / peak_value * 100
            if drawdown_from_peak >= trailing_drawdown:
                sold_value = total_shares * nav
                total_sold_value += sold_value
                tp_events.append({
                    "date_idx": i,
                    "nav": round(float(nav), 4),
                    "shares_sold": round(total_shares, 4),
                    "sold_value": round(sold_value, 4),
                    "drawdown_from_peak": round(drawdown_from_peak, 4),
                    "peak_value": round(peak_value, 4),
                })
                total_shares = 0.0

        nav_curve.append(round(float(current_portfolio), 4))

    final_nav = float(values[-1])
    final_value = float(total_shares * final_nav + total_sold_value)
    total_return_pct = ((final_value - total_invest) / total_invest * 100) if total_invest > 0 else 0.0
    years = n / 250.0
    annual_return_pct = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    avg_cost = (total_invest / total_shares) if total_shares > 0 else 0.0

    return {
        "strategy": f"移动止盈-{base_result.get('strategy', '定投')}",
        "trailing_drawdown": trailing_drawdown,
        "params": base_result.get('params', dca_kwargs),
        "total_invest": round(total_invest, 4),
        "total_shares": round(total_shares, 4),
        "final_value": round(final_value, 4),
        "total_return_pct": round(total_return_pct, 4),
        "annual_return_pct": round(annual_return_pct, 4),
        "avg_cost": round(avg_cost, 4),
        "current_nav": round(final_nav, 4),
        "nav_curve": nav_curve,
        "take_profit_events": tp_events,
        "total_sold_value": round(total_sold_value, 4),
    }


# ═══════════════════════════════════════════════
# 6. 定投策略对比
# ═══════════════════════════════════════════════

def compare_dca_strategies(
    nav_series: pd.Series,
    percentile_series: Optional[pd.Series] = None,
    base_amount: float = 1000.0,
    frequency_days: int = 1,
    start_idx: int = 0,
    end_idx: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    同条件下多种定投策略对比。
    对比策略：定期定额、均线定投、估值定投、目标止盈、移动止盈
    返回各策略的收益率/胜率/最大回撤/夏普比率等。
    """
    from .risk_metrics import max_drawdown, sharpe_ratio

    results = []

    # 1. 定期定额
    r1 = dca_fixed_amount(nav_series, frequency_days, base_amount, start_idx, end_idx)
    r1_mdd = max_drawdown(pd.Series(r1.get('nav_curve', [1])))
    results.append({
        "strategy": r1['strategy'],
        "total_return_pct": r1['total_return_pct'],
        "annual_return_pct": r1['annual_return_pct'],
        "max_drawdown_pct": round(r1_mdd, 4) if r1_mdd is not None else 0.0,
        "total_invest": r1['total_invest'],
        "final_value": r1['final_value'],
        "sharpe_ratio": None,  # 复利曲线非对称，夏普参考意义有限
        "avg_cost": r1['avg_cost'],
        "win_rate": None,
        "take_profit_count": 0,
    })

    # 2. 均线定投
    r2 = dca_ma_strategy(nav_series, 20, base_amount, frequency_days, 5.0, 2.0, start_idx, end_idx)
    r2_mdd = max_drawdown(pd.Series(r2.get('nav_curve', [1])))
    results.append({
        "strategy": r2['strategy'],
        "total_return_pct": r2['total_return_pct'],
        "annual_return_pct": r2['annual_return_pct'],
        "max_drawdown_pct": round(r2_mdd, 4) if r2_mdd is not None else 0.0,
        "total_invest": r2['total_invest'],
        "final_value": r2['final_value'],
        "avg_cost": r2['avg_cost'],
        "take_profit_count": 0,
    })

    # 3. 估值定投
    if percentile_series is not None:
        r3 = dca_valuation_strategy(
            nav_series, percentile_series, base_amount, frequency_days,
            30.0, 70.0, 2.0, 0.5, False, 20.0, start_idx, end_idx,
        )
        r3_mdd = max_drawdown(pd.Series(r3.get('nav_curve', [1])))
        results.append({
            "strategy": r3['strategy'],
            "total_return_pct": r3['total_return_pct'],
            "annual_return_pct": r3['annual_return_pct'],
            "max_drawdown_pct": round(r3_mdd, 4) if r3_mdd is not None else 0.0,
            "total_invest": r3['total_invest'],
            "final_value": r3['final_value'],
            "avg_cost": r3['avg_cost'],
            "take_profit_count": len(r3.get('take_profit_events', [])),
        })

    # 4. 目标止盈（基于定期定额）
    r4 = dca_target_take_profit(
        nav_series, dca_fixed_amount, 20.0,
        frequency_days=frequency_days, amount_per_period=base_amount,
        start_idx=start_idx, end_idx=end_idx,
    )
    r4_mdd = max_drawdown(pd.Series(r4.get('nav_curve', [1])))
    results.append({
        "strategy": r4['strategy'],
        "total_return_pct": r4['total_return_pct'],
        "annual_return_pct": r4['annual_return_pct'],
        "max_drawdown_pct": round(r4_mdd, 4) if r4_mdd is not None else 0.0,
        "total_invest": r4['total_invest'],
        "final_value": r4['final_value'],
        "avg_cost": r4['avg_cost'],
        "take_profit_count": len(r4.get('take_profit_events', [])),
    })

    # 5. 移动止盈（基于定期定额）
    r5 = dca_trailing_stop_profit(
        nav_series, dca_fixed_amount, 10.0,
        frequency_days=frequency_days, amount_per_period=base_amount,
        start_idx=start_idx, end_idx=end_idx,
    )
    r5_mdd = max_drawdown(pd.Series(r5.get('nav_curve', [1])))
    results.append({
        "strategy": r5['strategy'],
        "total_return_pct": r5['total_return_pct'],
        "annual_return_pct": r5['annual_return_pct'],
        "max_drawdown_pct": round(r5_mdd, 4) if r5_mdd is not None else 0.0,
        "total_invest": r5['total_invest'],
        "final_value": r5['final_value'],
        "avg_cost": r5['avg_cost'],
        "take_profit_count": len(r5.get('take_profit_events', [])),
    })

    return results


# ═══════════════════════════════════════════════
# 7. 定投收益曲线
# ═══════════════════════════════════════════════

def dca_equity_curve(
    nav_series: pd.Series,
    strategies: Optional[List[Dict]] = None,
    start_idx: int = 0,
    end_idx: Optional[int] = None,
) -> Dict[str, Any]:
    """
    定投收益曲线（多策略对比曲线）。
    参数:
      nav_series: 净值序列
      strategies: 策略配置列表 [{"name": str, "func": callable, "kwargs": dict}, ...]
                  None则生成默认3种策略曲线
      start_idx, end_idx: 索引范围
    返回:
      { "nav_series": [...], "strategies": { "策略名": [...曲线值...], ... },
        "return_series": { "策略名": [...累计收益率...], ... } }
    """
    values = nav_series.values
    n = len(values)
    if end_idx is None or end_idx > n:
        end_idx = n

    if strategies is None:
        strategies = [
            {"name": "定期定额", "func": dca_fixed_amount, "kwargs": {
                "frequency_days": 1, "amount_per_period": 1000,
                "start_idx": start_idx, "end_idx": end_idx,
            }},
            {"name": "均线定投(MA20)", "func": dca_ma_strategy, "kwargs": {
                "ma_period": 20, "base_amount": 1000, "frequency_days": 1,
                "threshold_pct": 5.0, "multiplier": 2.0,
                "start_idx": start_idx, "end_idx": end_idx,
            }},
            {"name": "移动止盈(回落10%)", "func": dca_trailing_stop_profit, "kwargs": {
                "base_dca_func": dca_fixed_amount, "trailing_drawdown": 10.0,
                "frequency_days": 1, "amount_per_period": 1000,
                "start_idx": start_idx, "end_idx": end_idx,
            }},
        ]

    curves = {}
    return_curves = {}
    for s in strategies:
        result = s["func"](nav_series=nav_series, **s["kwargs"])
        nav_curve = result.get('nav_curve', [])

        # 补齐长度
        if len(nav_curve) < n:
            nav_curve = [0.0] * (n - len(nav_curve)) + nav_curve

        curves[s["name"]] = [round(float(v), 4) for v in nav_curve]

        # 累计收益率曲线
        total_invest = result.get('total_invest', 1)
        if total_invest > 0:
            return_curve = [(v / (total_invest * (i + 1) / n) - 1) * 100
                            if i > 0 else 0.0
                            for i, v in enumerate(nav_curve)]
        else:
            return_curve = [0.0] * len(nav_curve)
        return_curves[s["name"]] = [round(float(v), 4) for v in return_curve]

    return {
        "nav_series": [round(float(v), 4) for v in values],
        "strategies_curves": curves,
        "return_curves": return_curves,
        "strategy_count": len(strategies),
    }
