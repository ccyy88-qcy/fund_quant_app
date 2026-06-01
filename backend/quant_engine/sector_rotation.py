"""行业轮动策略模块

功能：
- 宏观周期定位：基于PMI/CPI/利率判断经济周期阶段(复苏/过热/滞胀/衰退)
- 行业资金流向分析：主力净流入/流出、5日累计
- 行业景气度评分：综合价格动量(20%)+资金流向(30%)+估值分位(20%)+宏观匹配(30%)
- 轮动信号：超配/标配/低配建议，附带置信度
- 历史轮动回测：按期调仓的累积收益
"""
from typing import Any

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────
# 1. 宏观周期定位
# ──────────────────────────────────────────────

def macro_cycle_position(macro_data: dict) -> dict:
    """基于PMI/CPI/利率判断经济周期阶段，返回周期阶段+推荐配置

    Parameters
    ----------
    macro_data : dict
        必须包含键:
            - 'PMI' : float, 当前制造业PMI值
            - 'CPI' : float, 当前CPI同比(%)
            - 'rate' : float, 当前基准利率(%)
        可选键（用于趋势判定）:
            - 'PMI_trend' : str, 'up'|'down'|'stable'
            - 'CPI_trend' : str, 'up'|'down'|'stable'
            - 'rate_trend' : str, 'up'|'down'|'stable'

    Returns
    -------
    dict
        {
            'phase': str,           # 复苏/过热/滞胀/衰退
            'description': str,     # 文字描述
            'recommended_allocation': dict,  # 大类配置建议
            'sector_preference': list,       # 推荐行业方向
            'confidence': float,    # 置信度 [0,1]
            'indicators': dict,     # 各指标原始值
        }
    """
    # ── 提取指标 ──
    pmi = macro_data.get('PMI', 50.0)
    cpi = macro_data.get('CPI', 2.0)
    rate = macro_data.get('rate', 3.0)

    pmi_trend = macro_data.get('PMI_trend', _infer_trend(pmi, 50.0, 0.5))
    cpi_trend = macro_data.get('CPI_trend', _infer_trend(cpi, 2.0, 0.3))
    rate_trend = macro_data.get('rate_trend', _infer_trend(rate, 3.0, 0.25))

    # ── 模糊判定：先通过数值边界打分 ──
    # PMI>50 扩张，PMI<50 收缩
    # CPI 温和(1-3%) 正常，高(>3%) 通胀，低(<1%) 通缩
    # 利率趋势反映政策立场

    phase_scores = {
        '复苏': 0.0,   # PMI扩张↑ + CPI温和 + 利率低/降
        '过热': 0.0,   # PMI扩张↑ + CPI上行↑ + 利率升
        '滞胀': 0.0,   # PMI收缩↓ + CPI高↑ + 利率升
        '衰退': 0.0,   # PMI收缩↓ + CPI低↓ + 利率降
    }

    is_expanding = pmi > 50.0
    is_contracting = pmi < 50.0
    cpi_low = cpi < 1.5
    cpi_high = cpi > 3.0
    cpi_mild = 1.5 <= cpi <= 3.0

    # 复苏: 扩张+温和CPI+利率下行/低位
    if is_expanding and cpi_mild:
        phase_scores['复苏'] += 0.6
        if rate_trend in ('down', 'stable'):
            phase_scores['复苏'] += 0.3
    if is_expanding and cpi_low:
        phase_scores['复苏'] += 0.4  # 低通胀下的扩张也是复苏特征
        if rate_trend == 'down':
            phase_scores['复苏'] += 0.3

    # 过热: 扩张+高CPI+利率上行
    if is_expanding and cpi_high:
        phase_scores['过热'] += 0.6
        if rate_trend == 'up':
            phase_scores['过热'] += 0.3
    if is_expanding and cpi_mild and rate_trend == 'up':
        phase_scores['过热'] += 0.4  # 扩张+货币收紧先兆

    # 滞胀: 收缩+高CPI
    if is_contracting and cpi_high:
        phase_scores['滞胀'] += 0.7
        if rate_trend == 'up':
            phase_scores['滞胀'] += 0.2
    if pmi < 48.0 and cpi_high:  # 深度收缩+通胀
        phase_scores['滞胀'] += 0.1

    # 衰退: 收缩+低CPI+利率下行
    if is_contracting and cpi_low:
        phase_scores['衰退'] += 0.6
        if rate_trend == 'down':
            phase_scores['衰退'] += 0.3
    if is_contracting and cpi_mild and rate_trend == 'down':
        phase_scores['衰退'] += 0.4

    # 取最高分阶段
    sorted_phases = sorted(phase_scores.items(), key=lambda x: x[1], reverse=True)
    phase = sorted_phases[0][0]
    confidence = round(min(sorted_phases[0][1], 1.0), 4)

    # 若得分过于接近(差距<0.15)，降低置信度
    if len(sorted_phases) > 1:
        gap = sorted_phases[0][1] - sorted_phases[1][1]
        if gap < 0.15:
            confidence = round(confidence * 0.6, 4)

    # ── 各周期推荐配置 ──
    allocation_map = {
        '复苏': {
            '权益': 0.70, '债券': 0.20, '商品': 0.05, '现金': 0.05,
        },
        '过热': {
            '权益': 0.45, '债券': 0.15, '商品': 0.30, '现金': 0.10,
        },
        '滞胀': {
            '权益': 0.25, '债券': 0.35, '商品': 0.25, '现金': 0.15,
        },
        '衰退': {
            '权益': 0.30, '债券': 0.50, '商品': 0.05, '现金': 0.15,
        },
    }

    sector_pref_map = {
        '复苏': ['消费', '科技', '可选消费', '工业'],
        '过热': ['能源', '原材料', '金融', '工业'],
        '滞胀': ['公用事业', '能源', '医疗', '必需消费'],
        '衰退': ['公用事业', '医疗', '必需消费', '债券相关'],
    }

    descriptions = {
        '复苏': '经济扩张初期，PMI回升，通胀温和，利率低位。权益资产受益，周期/消费行业领先。',
        '过热': '经济强劲扩张，通胀上升，政策收紧。商品表现最佳，权益需精选。',
        '滞胀': '增长放缓叠加高通胀，类70年代格局。防御性行业和商品避险。',
        '衰退': '经济收缩，通胀回落，央行放水。债券为王，防御行业抗跌。',
    }

    result = {
        'phase': phase,
        'description': descriptions[phase],
        'recommended_allocation': allocation_map[phase],
        'sector_preference': sector_pref_map[phase],
        'confidence': float(confidence),
        'indicators': {
            'PMI': round(pmi, 2),
            'CPI': round(cpi, 2),
            'rate': round(rate, 2),
            'PMI_trend': pmi_trend,
            'CPI_trend': cpi_trend,
            'rate_trend': rate_trend,
        },
    }
    return result


def _infer_trend(value: float, baseline: float, threshold: float) -> str:
    """简单推断趋势方向（仅基于当前值与基准的偏离）"""
    diff = value - baseline
    if diff > threshold:
        return 'up'
    elif diff < -threshold:
        return 'down'
    return 'stable'


# ──────────────────────────────────────────────
# 2. 行业资金流向分析（辅助函数）
# ──────────────────────────────────────────────

def capital_flow_analysis(sector_data: list) -> list:
    """行业资金流向分析：主力净流入/流出、5日累计

    Parameters
    ----------
    sector_data : list[dict]
        每个元素为一个行业的数据:
            {
                'sector_name': str,          # 行业名称
                'main_net_inflow': float,    # 当日主力净流入(万元)
                'main_net_outflow': float,   # 当日主力净流出(万元)
                'inflow_5d': list[float],    # 近5日主力净流入序列
            }

    Returns
    -------
    list[dict]
        每条记录附加分析字段:
            - net_flow: 当日净流入-净流出
            - net_flow_5d_cum: 5日累计净流入
            - flow_trend: '流入加速'/'流入放缓'/'流出加速'/'流出放缓'/'平稳'
    """
    results = []
    for item in sector_data:
        name = item.get('sector_name', '未知')
        inflow = item.get('main_net_inflow', 0.0)
        outflow = item.get('main_net_outflow', 0.0)
        inflow_5d = item.get('inflow_5d', [])

        net_flow = round(inflow - outflow, 4)

        # 5日累计
        if inflow_5d and len(inflow_5d) > 0:
            net_flow_5d_cum = round(sum(inflow_5d), 4)
        else:
            net_flow_5d_cum = net_flow

        # 趋势判断
        if len(inflow_5d) >= 3:
            recent = np.mean(inflow_5d[-3:])
            earlier = np.mean(inflow_5d[:-3]) if len(inflow_5d) > 3 else 0.0
            if recent > 0 and earlier >= 0 and recent > earlier * 1.1:
                trend = '流入加速'
            elif recent > 0 and earlier > recent * 1.1:
                trend = '流入放缓'
            elif recent < 0 and earlier <= 0 and recent < earlier * 0.9:
                trend = '流出加速'
            elif recent < 0 and earlier < recent * 0.9:
                trend = '流出放缓'
            else:
                trend = '平稳'
        else:
            trend = '平稳'

        results.append({
            'sector_name': name,
            'net_flow': net_flow,
            'net_flow_5d_cum': net_flow_5d_cum,
            'flow_trend': trend,
            'main_net_inflow': inflow,
            'main_net_outflow': outflow,
            'inflow_5d': inflow_5d,
        })
    return results


# ──────────────────────────────────────────────
# 3. 行业景气度评分
# ──────────────────────────────────────────────

def sector_score(sector_data: list) -> list:
    """各行业综合评分排序

    评分维度权重：
        - 价格动量(20%)
        - 资金流向(30%)
        - 估值分位(20%)
        - 宏观匹配(30%)

    Parameters
    ----------
    sector_data : list[dict]
        每个元素需包含:
            {
                'sector_name': str,          # 行业名称
                'price_momentum': float,     # 价格动量得分 [0,100]
                'main_net_inflow': float,    # 主力净流入
                'main_net_outflow': float,   # 主力净流出
                'inflow_5d': list[float],    # 5日流入序列
                'valuation_percentile': float, # 估值分位 [0,100]
                'macro_match_score': float,  # 与当前宏观周期的匹配度 [0,100]
            }

    Returns
    -------
    list[dict]
        按综合评分降序排列，每条含:
            - sector_name
            - total_score: 综合评分 [0,100]
            - detail: 各维度得分明细
    """
    if not sector_data:
        return []

    # 提取各行业数据
    processed = []
    for item in sector_data:
        name = item.get('sector_name', '未知')

        # --- 价格动量 (权重20%) ---
        raw_momentum = item.get('price_momentum', 50.0)
        momentum_score = _normalize(raw_momentum, 0, 100)

        # --- 资金流向 (权重30%) ---
        inflow = item.get('main_net_inflow', 0.0)
        outflow = item.get('main_net_outflow', 0.0)
        inflow_5d = item.get('inflow_5d', [])

        net_flow_today = inflow - outflow
        net_flow_5d = sum(inflow_5d) if inflow_5d else net_flow_today

        # 将资金流映射到[0,100]：用正负号加权
        flow_score = _flow_to_score(net_flow_today, net_flow_5d)

        # --- 估值分位 (权重20%) ---
        raw_val = item.get('valuation_percentile', 50.0)
        # 估值分位越低越好（低估区域得分高）
        val_score = _normalize(100.0 - raw_val, 0, 100)

        # --- 宏观匹配 (权重30%) ---
        macro_match = item.get('macro_match_score', 50.0)
        macro_score = _normalize(macro_match, 0, 100)

        # --- 综合评分 ---
        total = (momentum_score * 0.20
                 + flow_score * 0.30
                 + val_score * 0.20
                 + macro_score * 0.30)
        total = round(total, 4)

        processed.append({
            'sector_name': name,
            'total_score': total,
            'detail': {
                'price_momentum': round(momentum_score, 2),
                'capital_flow': round(flow_score, 2),
                'valuation': round(val_score, 2),
                'macro_match': round(macro_score, 2),
            },
        })

    # 按总分降序
    processed.sort(key=lambda x: x['total_score'], reverse=True)
    return processed


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """将值线性映射到[0,100]并截断"""
    if max_val <= min_val:
        return 50.0
    clipped = np.clip(value, min_val, max_val)
    return float(round((clipped - min_val) / (max_val - min_val) * 100, 4))


def _flow_to_score(net_today: float, net_5d: float) -> float:
    """将资金流向转为[0,100]得分

    正流入→高分，负流出→低分。
    5日趋势加权：如果5日累计方向与当日一致则加强。
    """
    # 使用双曲正切将任意实数映射到[-1,1]
    # 缩放因子控制敏感度
    scale = max(abs(net_today), abs(net_5d), 1e6)

    if scale < 1e-6:
        return 50.0

    today_norm = net_today / scale
    cum_norm = net_5d / scale

    # 综合信号量: 当日占70%, 5日累计占30%
    combined = today_norm * 0.7 + cum_norm * 0.3
    combined = np.clip(combined, -1.0, 1.0)

    # tanh映射更平滑
    score = float(np.tanh(combined * 2.0))  # 放大后再tanh
    # 从[-1,1]映射到[0,100]
    return round((score + 1.0) / 2.0 * 100, 4)


# ──────────────────────────────────────────────
# 4. 轮动信号
# ──────────────────────────────────────────────

def rotation_signal(scores: list, top_n: int = 5) -> list:
    """根据行业评分生成轮动信号

    规则：
        - 排名前 top_n  → 超配
        - 排名中间档   → 标配
        - 排名后 top_n  → 低配
        - 置信度基于评分间距和绝对得分

    Parameters
    ----------
    scores : list[dict]
        sector_score() 的返回结果（已排序）
    top_n : int
        超配/低配的行业数量，默认5

    Returns
    -------
    list[dict]
        每条含:
            - sector_name
            - signal: '超配'|'标配'|'低配'
            - confidence: [0,1]
            - rank: 排名
            - score: 综合评分
    """
    if not scores:
        return []

    n = len(scores)
    if n == 0:
        return []

    # 确保 top_n 不超过合理范围
    top_n = min(top_n, max(1, n // 3))

    signals = []
    top_score = scores[0]['total_score']
    bottom_score = scores[-1]['total_score']
    score_range = top_score - bottom_score if top_score != bottom_score else 1.0

    for rank, item in enumerate(scores):
        name = item['sector_name']
        score = item['total_score']

        if rank < top_n:
            signal = '超配'
            # 置信度：基于与下一名的差距 + 绝对得分
            if rank + 1 < n:
                gap = score - scores[rank + 1]['total_score']
                gap_conf = min(abs(gap) / (score_range / n), 1.0)
            else:
                gap_conf = 1.0
            abs_conf = min(score / 100.0, 1.0)
            confidence = round(0.4 * abs_conf + 0.6 * gap_conf, 4)

        elif rank >= n - top_n:
            signal = '低配'
            if rank > 0:
                gap = scores[rank - 1]['total_score'] - score
                gap_conf = min(abs(gap) / (score_range / n), 1.0)
            else:
                gap_conf = 1.0
            abs_conf = 1.0 - min(score / 100.0, 1.0)
            confidence = round(0.4 * abs_conf + 0.6 * gap_conf, 4)

        else:
            signal = '标配'
            # 中间档置信度降低
            pos_in_mid = (rank - top_n) / max(n - 2 * top_n - 1, 1)
            confidence = round(0.5 * (1.0 - abs(pos_in_mid - 0.5) * 2), 4)

        confidence = float(np.clip(confidence, 0.0, 1.0))

        signals.append({
            'sector_name': name,
            'signal': signal,
            'confidence': confidence,
            'rank': rank + 1,
            'score': score,
        })

    return signals


# ──────────────────────────────────────────────
# 5. 历史轮动回测
# ──────────────────────────────────────────────

def rotation_backtest(sector_history: list, rebalance_interval: int = 20) -> dict:
    """按期调仓的行业轮动回测

    回测逻辑：
        1. 每 rebalance_interval 期重新评分排序
        2. 等权买入评分最高的 top_n 行业
        3. 计算累积收益、最大回撤、年化收益等

    Parameters
    ----------
    sector_history : list[list[dict]]
        历史数据序列，每个元素为一个时间切片上各行业数据。
        每个时间切片格式同 sector_score() 的输入。
        数据按时间递增排列。
    rebalance_interval : int
        调仓周期（多少个时间切片调一次仓），默认20

    Returns
    -------
    dict
        {
            'cumulative_return': float,   # 累计收益
            'annual_return': float,        # 年化收益
            'max_drawdown': float,         # 最大回撤
            'win_rate': float,             # 胜率（正收益期数占比）
            'total_periods': int,          # 总期数
            'trade_count': int,            # 调仓次数
            'nav_curve': list[float],      # 净值曲线
            'drawdown_curve': list[float], # 回撤曲线
            'rebalance_records': list[dict], # 每次调仓记录
        }
    """
    if not sector_history or len(sector_history) < 2:
        return {
            'cumulative_return': 0.0,
            'annual_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_periods': len(sector_history) if sector_history else 0,
            'trade_count': 0,
            'nav_curve': [1.0],
            'drawdown_curve': [0.0],
            'rebalance_records': [],
        }

    total_periods = len(sector_history)
    top_n = max(1, len(sector_history[0]) // 3)

    # 净值序列
    nav = 1.0
    nav_curve = [nav]
    max_nav = nav

    # 当前持仓: {sector_name: weight}
    holdings: dict[str, float] = {}
    rebalance_records = []

    for t in range(total_periods):
        slice_data = sector_history[t]

        # 是否调仓
        if t % rebalance_interval == 0 or t == 0:
            # 重新评分
            scored = sector_score(slice_data)
            if not scored:
                continue
            signals = rotation_signal(scored, top_n=top_n)

            # 超配行业等权建仓
            overweight = [s for s in signals if s['signal'] == '超配']
            if overweight:
                weight = round(1.0 / len(overweight), 6)
                new_holdings: dict[str, float] = {}
                for s in overweight:
                    new_holdings[s['sector_name']] = weight
                holdings = new_holdings

                rebalance_records.append({
                    'period': t,
                    'holdings': list(holdings.keys()),
                    'weights': [weight] * len(holdings),
                    'nav_before': round(nav, 4),
                })
            elif slice_data:
                # 没有超配信号，选评分最高top_n
                top_sectors = scored[:top_n]
                weight = round(1.0 / len(top_sectors), 6)
                holdings = {s['sector_name']: weight for s in top_sectors}
                rebalance_records.append({
                    'period': t,
                    'holdings': list(holdings.keys()),
                    'weights': [weight] * len(top_sectors),
                    'nav_before': round(nav, 4),
                })

        # 计算当期各行业收益率（用价格动量近似）
        if holdings and slice_data:
            sector_map = {s['sector_name']: s for s in slice_data}
            period_return = 0.0
            for sector_name, weight in holdings.items():
                if sector_name in sector_map:
                    # 用价格动量得分近似收益率（需从[0,100]映射到百分比变化）
                    mom = sector_map[sector_name].get('price_momentum', 50.0)
                    # 动量得分→收益率映射：(得分-50)/50 作为收益率近似
                    ret = (mom - 50.0) / 50.0 * 0.02  # 缩放因子2%
                    period_return += weight * ret
                # 未找到的行业视为0收益

            nav *= (1.0 + period_return)
            nav = round(nav, 6)

        nav_curve.append(nav)
        max_nav = max(max_nav, nav)

    # ── 计算回撤曲线 ──
    drawdown_curve = []
    peak = nav_curve[0]
    for v in nav_curve:
        peak = max(peak, v)
        dd = (v - peak) / peak if peak != 0 else 0.0
        drawdown_curve.append(round(dd, 6))
    max_drawdown = round(abs(min(drawdown_curve)), 4)

    # ── 累计收益 ──
    cumulative_return = round(nav_curve[-1] - 1.0, 4)

    # ── 年化收益（假设每期一个月，约12期/年） ──
    years = total_periods / 12.0
    if years > 0 and nav_curve[-1] > 0:
        annual_return = round(nav_curve[-1] ** (1.0 / years) - 1.0, 4)
    else:
        annual_return = 0.0

    # ── 胜率 ──
    if len(nav_curve) > 1:
        period_returns = [
            (nav_curve[i] - nav_curve[i - 1]) / nav_curve[i - 1]
            for i in range(1, len(nav_curve))
            if nav_curve[i - 1] != 0
        ]
        win_count = sum(1 for r in period_returns if r > 0)
        win_rate = round(win_count / len(period_returns), 4) if period_returns else 0.0
    else:
        win_rate = 0.0

    return {
        'cumulative_return': cumulative_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'total_periods': total_periods,
        'trade_count': len(rebalance_records),
        'nav_curve': [round(v, 6) for v in nav_curve],
        'drawdown_curve': drawdown_curve,
        'rebalance_records': rebalance_records,
    }


# ──────────────────────────────────────────────
# 快速演示入口
# ──────────────────────────────────────────────

if __name__ == '__main__':
    # ── 宏观周期演示 ──
    macro_data = {
        'PMI': 51.2,
        'CPI': 2.1,
        'rate': 3.0,
        'PMI_trend': 'up',
        'CPI_trend': 'stable',
        'rate_trend': 'stable',
    }
    pos = macro_cycle_position(macro_data)
    print('=== 宏观周期定位 ===')
    print(f"阶段: {pos['phase']}")
    print(f"置信度: {pos['confidence']}")
    print(f"推荐配置: {pos['recommended_allocation']}")
    print(f"推荐行业: {pos['sector_preference']}")
    print()

    # ── 行业评分演示 ──
    demo_sectors = [
        {
            'sector_name': '科技',
            'price_momentum': 75.0,
            'main_net_inflow': 50000,
            'main_net_outflow': 10000,
            'inflow_5d': [20000, 30000, 40000, 50000, 50000],
            'valuation_percentile': 45.0,
            'macro_match_score': 80.0,
        },
        {
            'sector_name': '消费',
            'price_momentum': 60.0,
            'main_net_inflow': 30000,
            'main_net_outflow': 15000,
            'inflow_5d': [10000, 15000, 20000, 25000, 30000],
            'valuation_percentile': 30.0,
            'macro_match_score': 70.0,
        },
        {
            'sector_name': '能源',
            'price_momentum': 45.0,
            'main_net_inflow': -5000,
            'main_net_outflow': 25000,
            'inflow_5d': [-10000, -8000, -5000, -2000, -5000],
            'valuation_percentile': 70.0,
            'macro_match_score': 40.0,
        },
        {
            'sector_name': '金融',
            'price_momentum': 55.0,
            'main_net_inflow': 10000,
            'main_net_outflow': 8000,
            'inflow_5d': [5000, 6000, 8000, 10000, 10000],
            'valuation_percentile': 20.0,
            'macro_match_score': 55.0,
        },
        {
            'sector_name': '医疗',
            'price_momentum': 50.0,
            'main_net_inflow': 8000,
            'main_net_outflow': 12000,
            'inflow_5d': [5000, 4000, 3000, 2000, 8000],
            'valuation_percentile': 55.0,
            'macro_match_score': 60.0,
        },
    ]

    print('=== 行业景气度评分 ===')
    scored = sector_score(demo_sectors)
    for s in scored:
        print(f"  {s['sector_name']:4s} | 总分: {s['total_score']:6.2f} | "
              f"动量:{s['detail']['price_momentum']:5.1f} "
              f"资金:{s['detail']['capital_flow']:5.1f} "
              f"估值:{s['detail']['valuation']:5.1f} "
              f"宏观:{s['detail']['macro_match']:5.1f}")
    print()

    print('=== 轮动信号 ===')
    signals = rotation_signal(scored, top_n=2)
    for s in signals:
        print(f"  {s['sector_name']:4s} | {s['signal']} | 置信度:{s['confidence']:.4f} | 排名:{s['rank']}")
    print()

    # ── 资金流向分析演示 ──
    print('=== 资金流向分析 ===')
    flow_result = capital_flow_analysis(demo_sectors)
    for f in flow_result:
        print(f"  {f['sector_name']:4s} | 净流入:{f['net_flow']:>8.0f} | 5日累计:{f['net_flow_5d_cum']:>8.0f} | 趋势:{f['flow_trend']}")
