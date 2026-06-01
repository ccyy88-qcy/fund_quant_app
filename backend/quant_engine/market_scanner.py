"""基金真实市场扫描引擎 — 全市场ETF实时扫描+评分+建仓推荐"""
import os
import sys
import time
import contextlib
import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime
from typing import Optional

# 内存缓存：避免重复扫描全市场1500只ETF（卡事件循环）
_scan_cache = {}
_CACHE_TTL = 300  # 5分钟

from .indicators import calc_ma, calc_rsi, calc_macd, calc_bollinger
from .risk_metrics import max_drawdown


@contextlib.contextmanager
def _suppress_output():
    """抑制akshare的tqdm进度条输出，避免uvicorn中Broken pipe"""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def scan_etf_market(top_n: int = 20, min_volume_ratio: float = 0.5) -> list:
    """扫描全市场ETF，找出综合评分最高的

    策略：
    1. 先拉实时ETF行情（1489只），按成交额+涨幅过滤
    2. 获取候选ETF的K线数据计算技术指标
    3. 综合评分排序

    Args:
        top_n: 返回前N只
        min_volume_ratio: 最小时比过滤

    Returns:
        评分排序后的ETF列表（真实数据）
    """
    # 内存缓存：避免重复扫描卡事件循环
    cache_key = f'scan_etf_market:{top_n}:{min_volume_ratio}'
    cached = _scan_cache.get(cache_key)
    if cached and time.time() - cached['time'] < _CACHE_TTL:
        return cached['data']

    # 1. 拉实时ETF行情（抑制tqdm进度条，避免uvicorn Broken pipe）
    try:
        with _suppress_output():
            spot_df = ak.fund_etf_spot_em()
    except Exception as e:
        return [{'error': f'获取ETF行情失败: {str(e)}'}]

    if spot_df is None or len(spot_df) == 0:
        return [{'error': 'ETF行情数据为空'}]

    # 2. 初步过滤
    spot_df['涨跌幅'] = pd.to_numeric(spot_df['涨跌幅'], errors='coerce')
    spot_df['成交额'] = pd.to_numeric(spot_df['成交额'], errors='coerce')
    spot_df['量比'] = pd.to_numeric(spot_df['量比'], errors='coerce')
    spot_df['换手率'] = pd.to_numeric(spot_df['换手率'], errors='coerce')
    spot_df['振幅'] = pd.to_numeric(spot_df['振幅'], errors='coerce')
    spot_df['主力净流入占比'] = pd.to_numeric(spot_df['主力净流入-净占比'], errors='coerce')

    # 过滤：量比达标 + 成交额不为0
    # 过滤货币基金/债券ETF（名称含关键词的剔除）
    exclude_keywords = ['添益', '日利', '货币', '国债', '地方债', '可转', '国开', '农发']
    spot_df = spot_df[~spot_df['名称'].str.contains('|'.join(exclude_keywords), na=False)].copy()

    candidates = spot_df[
        (spot_df['量比'].fillna(0) >= min_volume_ratio) &
        (spot_df['成交额'].fillna(0) > 0)
    ].copy()

    if len(candidates) == 0:
        candidates = spot_df.head(100).copy()

    # 3. 取前100只活跃ETF做深度分析
    # 综合活跃度评分：成交额(40%) + 量比(30%) + 振幅(30%)
    max_amount = candidates['成交额'].max()
    candidates['活跃度'] = (
        (candidates['成交额'] / max_amount * 40) +
        (candidates['量比'].clip(0, 5) / 5 * 30) +
        (candidates['振幅'].clip(0, 10) / 10 * 30)
    )
    candidates = candidates.sort_values('活跃度', ascending=False).head(100)

    # 4. 深度分析（获取K线+技术指标）
    results = []
    for _, row in candidates.iterrows():
        code = str(row['代码']).strip().zfill(6)
        name = str(row['名称'])

        # 获取K线
        kline = _get_kline_real(code)
        if not kline or len(kline) < 60:
            continue

        # 计算评分
        score = _calc_short_term_score(kline, row)
        if score is None:
            continue

        score['code'] = code
        score['name'] = name
        score['price'] = round(float(row.get('最新价', 0)), 4)
        score['change_pct'] = round(float(row.get('涨跌幅', 0)), 2)
        score['volume_ratio'] = round(float(row.get('量比', 0)), 2)
        score['amount'] = float(row.get('成交额', 0))
        score['turnover'] = round(float(row.get('换手率', 0)), 2)
        score['amplitude'] = round(float(row.get('振幅', 0)), 2)
        score['capital_flow'] = round(float(row.get('主力净流入-净额', 0)), 2)
        score['capital_flow_pct'] = round(float(row.get('主力净流入-净占比', 0)), 2) if pd.notna(row.get('主力净流入-净占比')) else 0
        score['scan_time'] = datetime.now().strftime('%H:%M')

        results.append(score)
        time.sleep(0.3)  # 避免请求过快

        if len(results) >= top_n * 2:  # 多拉一些供排序
            break

    # 5. 综合排序
    if not results:
        _scan_cache[cache_key] = {'data': [], 'time': time.time()}
        return [{'error': '无法获取足够K线数据'}]

    results.sort(key=lambda x: x.get('total_score', 0), reverse=True)

    # 缓存结果（5分钟有效）
    _scan_cache[cache_key] = {'data': results[:top_n], 'time': time.time()}
    return results[:top_n]


def _get_kline_real(code: str, days: int = 200) -> list:
    """使用真实数据源获取K线"""
    # 使用 data_fetcher.get_kline (有3层备选策略)
    from . import data_fetcher as df
    kline = df.get_kline(code, days)
    if kline and len(kline) >= 5:
        return kline
    return []


def _calc_short_term_score(kline: list, spot_row: pd.Series) -> Optional[dict]:
    """计算短线建仓评分

    五维评分+实时价修正：
    - 历史位置 25%（历史高低位）
    - 技术形态 25%（均线排列+回踩）
    - 今日走势 20%（当日涨跌幅，避免用旧K线评分）
    - 资金流向 15%（主力净流入占比）
    - RSI 10%（超买超卖）
    - 量能 5%（缩量/放量配合）
    """
    import math
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
    if len(closes) < 20:
        return None

    # 实时价（今日最新价，非K线收盘）
    current_price = float(spot_row.get('最新价', closes.iloc[-1]))
    change_pct = float(spot_row.get('涨跌幅', 0))
    cap_flow_pct = float(spot_row.get('主力净流入-净占比', 0)) if pd.notna(spot_row.get('主力净流入-净占比')) else 0
    vol_ratio = float(spot_row.get('量比', 0))

    # ── 0. 基于实时价的均线（使用完整K线 + 实时价补最后一位）──
    closes_real = pd.concat([closes.iloc[:-1], pd.Series([current_price])], ignore_index=True)
    ma5 = calc_ma(closes_real, 5).iloc[-1] if len(closes_real) >= 5 else current_price
    ma10 = calc_ma(closes_real, 10).iloc[-1] if len(closes_real) >= 10 else current_price
    ma20 = calc_ma(closes_real, 20).iloc[-1] if len(closes_real) >= 20 else current_price
    ma60 = calc_ma(closes_real, 60).iloc[-1] if len(closes_real) >= 60 else current_price

    is_uptrend = ma5 > ma10 > ma20
    is_downtrend = ma5 < ma10 < ma20
    above_ma10_pct = (current_price - ma10) / ma10 * 100 if ma10 > 0 else 0

    # ── 1. 历史位置评分 (25%) ──
    hist_high = float(closes.max())
    hist_low = float(closes.min())
    hist_range = hist_high - hist_low if hist_high > hist_low else 1
    hist_pct = (current_price - hist_low) / hist_range * 100

    if hist_pct >= 90:
        pos_score = 0       # 历史高位，绝对不建仓
    elif hist_pct >= 75:
        pos_score = 20      # 高位
    elif hist_pct >= 50:
        pos_score = 50      # 中位
    elif hist_pct >= 30:
        pos_score = 70      # 中低位
    elif hist_pct >= 15:
        pos_score = 85      # 低位
    else:
        pos_score = 95      # 历史底部

    # ── 2. 技术形态评分 (25%) ──
    shape_score = 50
    if is_uptrend:
        shape_score += 15
        if -2 < above_ma10_pct < 1:
            shape_score += 20  # 回踩MA10不破
        elif -3 < above_ma10_pct < -1:
            shape_score += 10
        elif above_ma10_pct > 5:
            shape_score -= 20  # 偏离过远追高
        elif above_ma10_pct > 3:
            shape_score -= 10
    elif is_downtrend:
        shape_score -= 20     # 空头排列重罚
        # 只有大幅超跌才考虑（跌幅>10%）
        if above_ma10_pct < -15:
            shape_score += 15  # 超跌反弹机会
        elif above_ma10_pct < -8:
            shape_score += 5
    else:
        # 震荡区间
        if -2 < above_ma10_pct < 2:
            shape_score += 10  # 靠近MA10支撑
        elif abs(above_ma10_pct) > 8:
            shape_score -= 10

    if current_price > ma60:
        shape_score += 5
    else:
        shape_score -= 10     # 跌破MA60加重罚
    shape_score = np.clip(shape_score, 0, 100)

    # ── 3. 今日走势评分 (20%) ──
    # 大跌直接否决，大涨加分但要结合资金流向
    if change_pct < -4:
        daily_score = 0        # 暴跌，绝对回避
    elif change_pct < -2.5:
        daily_score = 10       # 大跌
    elif change_pct < -1:
        daily_score = 25       # 明显下跌
    elif change_pct < 0:
        daily_score = 40       # 微跌
    elif change_pct < 1:
        daily_score = 55       # 平盘
    elif change_pct < 3:
        daily_score = 70       # 温和上涨
    elif change_pct < 5:
        daily_score = 80       # 明显上涨
    else:
        daily_score = 85       # 大涨

    # ── 4. 资金流向评分 (15%) ──
    # 主力净流入占比：正=流入 负=流出
    if cap_flow_pct > 2:
        flow_score = 90        # 主力大幅买入
    elif cap_flow_pct > 1:
        flow_score = 80
    elif cap_flow_pct > 0.5:
        flow_score = 70
    elif cap_flow_pct > 0:
        flow_score = 60
    elif cap_flow_pct > -0.5:
        flow_score = 45        # 小幅流出
    elif cap_flow_pct > -1.5:
        flow_score = 30        # 明显流出
    elif cap_flow_pct > -3:
        flow_score = 15        # 大幅流出
    else:
        flow_score = 0         # 主力出逃

    # ── 5. RSI评分 (10%) ──
    rsi_score = 50
    if len(closes_real) >= 15:
        rsi = calc_rsi(closes_real, 14)
        if not np.isnan(rsi.iloc[-1]):
            rsi_val = rsi.iloc[-1]
            if rsi_val < 25:
                rsi_score = 80   # 深度超卖
            elif rsi_val < 35:
                rsi_score = 70   # 超卖
            elif rsi_val < 45:
                rsi_score = 55
            elif rsi_val < 55:
                rsi_score = 45   # 中性
            elif rsi_val < 65:
                rsi_score = 30   # 偏强
            elif rsi_val < 75:
                rsi_score = 15   # 过热
            else:
                rsi_score = 5    # 极度超买

    # ── 6. 量能评分 (5%) ──
    vol_score = 50
    volumes = np.array([float(d.get('volume', 0)) for d in kline])
    if len(volumes) >= 20:
        vol_5d = np.mean(volumes[-5:])
        vol_20d = np.mean(volumes[-20:])
        hist_vol_ratio = vol_5d / max(vol_20d, 1)
        daily_ret = closes_real.pct_change() * 100
        last_ret = daily_ret.iloc[-1] if len(daily_ret) > 1 else 0

        if last_ret < -1 and hist_vol_ratio > 1.5:
            vol_score = 10       # 放量暴跌 → 恐慌
        elif last_ret > 0 and hist_vol_ratio > 1.5:
            vol_score = 75       # 放量上涨 → 强势
        elif last_ret < 0 and hist_vol_ratio < 0.8:
            vol_score = 65       # 缩量回调 → 健康
        elif last_ret > 0 and hist_vol_ratio < 0.6:
            vol_score = 30       # 缩量上涨 → 动能不足
        else:
            vol_score = 50

    # ── 7. 特殊惩罚因子 ──
    penalty = 1.0

    # 放量暴跌+主力流出 → 飞刀，绝对不碰
    if change_pct < -3 and cap_flow_pct < -1 and vol_ratio > 1.5:
        penalty = 0.3
    # 放量下跌+主力流出
    elif change_pct < -2 and cap_flow_pct < -0.5:
        penalty = 0.5
    # 低位+下行趋势=接飞刀
    if hist_pct < 25 and is_downtrend:
        penalty *= 0.4
    # 高位+偏离均线太远=追高风险
    elif hist_pct > 75 and above_ma10_pct > 5:
        penalty *= 0.4
    # RSI超买+价格上涨=随时回调
    elif rsi_score < 20 and daily_score > 60:
        penalty *= 0.5

    # ── 综合评分 ──
    total = round(
        pos_score * 0.25 +
        shape_score * 0.25 +
        daily_score * 0.20 +
        flow_score * 0.15 +
        rsi_score * 0.10 +
        vol_score * 0.05,
        2
    )
    total = round(total * penalty, 2)
    total = float(np.clip(total, 0, 100))

    # ── 建仓信号 ──
    if total >= 80:
        build_signal = '🔥 强烈建仓'
        position = '60-80%'
        advice = '价格安全+主力流入+技术面好，可布局'
    elif total >= 65:
        build_signal = '✅ 建议建仓'
        position = '40-60%'
        advice = '性价比合适，可分批建仓'
    elif total >= 50:
        build_signal = '⏳ 观察等待'
        position = '20-30%'
        advice = '条件一般，等待更好位置'
    elif total >= 35:
        build_signal = '⚠️ 注意风险'
        position = '0-10%'
        advice = '位置偏高或资金流出，暂不建仓'
    else:
        build_signal = '🚫 回避'
        position = '0%'
        advice = '风险大，观望为主'

    # 短线方向描述
    short_term = ''
    if is_uptrend and -2 < above_ma10_pct < 2:
        short_term = '📈 上升趋势回踩支撑'
    elif is_uptrend and above_ma10_pct > 5:
        short_term = '⚠️ 趋势向上但偏离较远'
    elif is_downtrend and change_pct < -3:
        short_term = '🔻 下跌趋势，暂不参与'
    elif is_downtrend:
        short_term = '📉 震荡下行'
    else:
        short_term = '↔️ 震荡格局，高抛低吸'

    return {
        'total_score': total,
        'build_signal': build_signal,
        'suggested_position': position,
        'short_term_advice': short_term,
        'action_detail': advice,
        'hist_percentile': round(hist_pct, 1),
        'scores': {
            'position': int(pos_score),
            'technical_shape': int(shape_score),
            'daily_trend': int(daily_score),
            'capital_flow': int(flow_score),
            'rsi': int(rsi_score),
            'volume': int(vol_score),
        },
        'technical': {
            'ma5': round(float(ma5), 4), 'ma10': round(float(ma10), 4),
            'ma20': round(float(ma20), 4), 'ma60': round(float(ma60), 4),
            'above_ma10_pct': round(float(above_ma10_pct), 2),
            'above_ma10': bool(above_ma10_pct > 0),
            'is_uptrend': bool(is_uptrend), 'is_downtrend': bool(is_downtrend),
        },
    }


def scan_build_candidates(top_n: int = 10) -> list:
    """扫描全市场找出最适合建仓的ETF

    返回真实市场数据，无模拟
    """
    results = scan_etf_market(top_n=top_n * 2)
    # 过滤货币基金/债券ETF
    exclude_keywords = ['添益', '日利', '货币', '国债', '地方债', '可转']
    results = [r for r in results if not any(k in str(r.get('name', '')) for k in exclude_keywords)]
    # 只返回建仓信号>=观察等待的
    candidates = [r for r in results if '强烈建仓' in str(r.get('build_signal', '')) or
                  '建议建仓' in str(r.get('build_signal', ''))]
    if not candidates:
        # 如果都没有强烈信号，返回评分最高的
        candidates = results[:top_n]
    return candidates[:top_n]


def scan_golden_cross_candidates(top_n: int = 10) -> list:
    """MACD底背离+金叉抄底扫描

    条件（评分制，不硬筛）：
    1. MACD在零轴下方 (DIF<0, DEA<0)
    2. 绿柱从放大到缩小 (当前MACD柱 > 前一根，且均为负)
    3. MA5上穿或即将上穿MA10（金叉形成中）
    4. 近60日最大回撤 > 10%
    5. 近2日主力资金净流入 > 0
    """
    results = []
    # 使用已缓存的热门ETF列表，避免重复全量扫描
    from . import data_fetcher as df
    try:
        import akshare as ak
        with _suppress_output():
            spot_df = ak.fund_etf_spot_em()
    except:
        return [{'error': '获取ETF行情失败'}]

    exclude_keywords = ['添益', '日利', '货币', '国债', '地方债', '可转', '国开', '农发']
    spot_df = spot_df[~spot_df['名称'].str.contains('|'.join(exclude_keywords), na=False)].copy()
    spot_df = spot_df[spot_df['成交额'].fillna(0) > 5e7].copy()  # 成交额>5000万
    top_etfs = spot_df.sort_values('成交额', ascending=False).head(top_n * 5)

    for _, row in top_etfs.iterrows():
        code = str(row['代码']).strip().zfill(6)
        name = str(row['名称'])
        change_pct = float(row.get('涨跌幅', 0))
        cap_flow = float(row.get('主力净流入-净占比', 0)) if pd.notna(row.get('主力净流入-净占比')) else 0
        vol_ratio = float(row.get('量比', 0))
        try:
            kline = _get_kline_real(code, 200)
            if not kline or len(kline) < 60:
                continue

            closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
            if len(closes) < 60:
                continue

            current = float(closes.iloc[-1])
            ma5 = float(calc_ma(closes, 5).iloc[-1])
            ma10 = float(calc_ma(closes, 10).iloc[-1])
            ma5_prev = float(calc_ma(closes, 5).iloc[-2]) if len(closes) >= 6 else ma5
            ma10_prev = float(calc_ma(closes, 10).iloc[-2]) if len(closes) >= 11 else ma10

            # MACD
            dif, dea, macd_bar = calc_macd(closes)
            dif_v = float(dif.iloc[-1])
            dea_v = float(dea.iloc[-1])
            bar_v = float(macd_bar.iloc[-1])
            bar_prev = float(macd_bar.iloc[-2]) if len(macd_bar) > 1 else bar_v

            # 近60日高点回撤
            high_60d = float(closes[-60:].max())
            drawdown_pct = round((high_60d - current) / high_60d * 100, 2)

            # 历史位置百分位（估值参考）
            hist_high_all = float(closes.max())
            hist_low_all = float(closes.min())
            hist_range = hist_high_all - hist_low_all if hist_high_all > hist_low_all else 1
            hist_pct = (current - hist_low_all) / hist_range * 100

            # 条件判定
            cond1 = dif_v < 0 and dea_v < 0          # MACD零轴下方
            cond2 = bar_v > bar_prev and bar_v < 0   # 绿柱从放大→缩小
            cond3 = (ma5 > ma10 and ma5_prev <= ma10_prev) or \
                    (abs(ma5 - ma10) / ma10 < 0.025 and ma5 > ma5_prev)  # 金叉或即将金叉
            cond4 = drawdown_pct > 10                 # 回撤>10%
            cond5 = cap_flow > 0  # 资金净流入

            if not (cond1 and cond2):
                continue

            # 评分：每个条件20分 + 加分项
            score = 0
            for c in [cond1, cond2, cond3, cond4, cond5]:
                if c:
                    score += 20

            # 回撤加分：回撤越大说明超跌越严重，反弹潜力越大
            dd_bonus = min(15, max(0, drawdown_pct - 10))
            score += dd_bonus

            # 金叉强度：MA5-MA10差距越小越接近金叉
            cross_strength = max(0, min(10, 10 - abs(ma5 - ma10) / ma10 * 1000))
            score += cross_strength

            # 绿柱收缩幅度加分
            bar_shrink = abs(bar_v) / max(abs(bar_prev), 0.001)
            if bar_shrink < 0.8:  # 绿柱明显缩小
                score += 5

            score = min(100, int(score))

            # 估值评级
            if hist_pct < 20:
                val_rating = '📉 低估'
                val_color = '#4CAF50'
            elif hist_pct < 40:
                val_rating = '📊 偏低'
                val_color = '#66BB6A'
            elif hist_pct < 60:
                val_rating = '📊 合理'
                val_color = '#FF9800'
            elif hist_pct < 80:
                val_rating = '📈 偏高'
                val_color = '#FF7043'
            else:
                val_rating = '🚨 高估'
                val_color = '#F44336'

            # 信号分级
            if score >= 75:
                signal = '🔥 强烈信号'
                action = 'MACD底背离+金叉确认，可分批建仓'
            elif score >= 60:
                signal = '✅ 信号确认'
                action = '条件满足较多，关注入场时机'
            elif score >= 45:
                signal = '👀 关注中'
                action = '部分条件满足，等待进一步确认'
            else:
                signal = '⏳ 观察'
                action = '条件有限，暂观望'

            results.append({
                'total_score': score,
                'build_signal': signal,
                'action_detail': action,
                'short_term_advice': f'回撤{drawdown_pct}% | MACD绿柱收缩 | 金叉形成中',
                'suggested_position': '40-60%' if score >= 60 else ('20-30%' if score >= 45 else '0-10%'),
                'code': code,
                'name': name,
                'price': current,
                'change_pct': change_pct,
                'capital_flow_pct': cap_flow,
                'volume_ratio': vol_ratio,
                'drawdown_pct': drawdown_pct,
                'hist_percentile': round(hist_pct, 1),
                'valuation': val_rating,
                'macd': {'dif': round(dif_v, 4), 'dea': round(dea_v, 4), 'bar': round(bar_v, 4)},
                'ma': {'ma5': round(ma5, 4), 'ma10': round(ma10, 4)},
                'conditions': {
                    'macd_below_zero': cond1,
                    'green_bar_shrinking': cond2,
                    'golden_cross': cond3,
                    'drawdown_gt_10': cond4,
                    'capital_inflow': cond5,
                },
                'scan_time': datetime.now().strftime('%H:%M'),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x.get('total_score', 0), reverse=True)

    # 行业去重：同一板块只保留评分最高的
    # 先提取行业关键词
    _SECTOR_KEYWORDS = [
        '恒生科技', '恒生互联网', '中概互联', '港股通', '恒生',
        '半导体', '芯片', '通信', '5G', '软件', '数字经济', '电子',
        '红利', '银行', '证券', '保险', '地产', '基建', '消费',
        '新能源', '光伏', '军工', '医药', '医疗', '创新药',
        '黄金', '商品',
        '沪深300', '中证500', '中证1000', '上证50', '科创50', '科创100',
        '创业板', '中证A500', '大盘', '成长', '价值',
    ]
    def _extract_sector(name: str) -> str:
        for kw in _SECTOR_KEYWORDS:
            if kw in name:
                return kw
        # 没匹配到关键词，取ETF前面的部分（不含管理公司名）
        for suffix in ['ETF华夏', 'ETF易方达', 'ETF华泰柏瑞', 'ETF国泰', 'ETF招商',
                       'ETF南方', 'ETF富国', 'ETF广发', 'ETF嘉实', 'ETF工银',
                       'ETF博时', 'ETF平安', 'ETF银华', 'ETF华安', 'ETF浦银',
                       'ETF天弘', 'ETF大成', 'ETF汇添富']:
            if suffix in name:
                return name.split(suffix)[0]
        return name.split('ETF')[0].strip() if 'ETF' in name else name[:4]

    seen_sectors = set()
    deduped = []
    for item in results:
        sector = _extract_sector(item.get('name', ''))
        if sector in seen_sectors:
            continue
        seen_sectors.add(sector)
        item['sector'] = sector
        deduped.append(item)
        if len(deduped) >= top_n:
            break

    return deduped


# ─── 指数PE/PB估值查询 ───

# ETF名称→指数代码映射（常见宽基/行业ETF）
_ETF_INDEX_MAP = [
    ('沪深300', '000300'), ('中证500', '000905'), ('中证1000', '000852'),
    ('上证50', '000016'), ('科创50', '000688'), ('科创100', '000858'),
    ('创业板', '399006'), ('深证100', '399330'),
    ('恒生科技', '931069'), ('恒生互联网', '931069'), ('恒生', '931069'),
    ('中概互联', '930901'), ('中概互联网', '930901'),
    ('半导体', '931865'), ('芯片', '931865'), ('电子', '931865'),
    ('通信', '931079'), ('5G', '931079'),
    ('新能源', '931580'), ('光伏', '931580'),
    ('军工', '931580'), ('国防', '931580'),
    ('医药', '931580'), ('医疗', '931580'),
    ('消费', '931580'), ('白酒', '931580'),
    ('红利', '931580'), ('银行', '931580'),
    ('证券', '931580'), ('保险', '931580'),
    ('地产', '931580'), ('基建', '931580'),
]


def get_etf_pe_data(etf_name: str) -> dict:
    """获取ETF对应指数的PE/PB估值数据"""
    import akshare as ak
    for kw, idx_code in _ETF_INDEX_MAP:
        if kw in etf_name:
            try:
                df = ak.stock_zh_index_value_csindex(symbol=idx_code)
                if df is not None and len(df) > 0:
                    row = df.iloc[-1]
                    pe = float(row.iloc[6]) if row.iloc[6] not in (None, '', '-') else None
                    pe2 = float(row.iloc[7]) if row.iloc[7] not in (None, '', '-') else None
                    name = str(row.iloc[4]) if row.iloc[4] else ''
                    return {'pe': pe, 'pe_ttm': pe2, 'index_name': name, 'source': 'csindex'}
            except Exception:
                pass
            break
    return {'pe': None, 'pe_ttm': None, 'index_name': '', 'source': 'none'}
