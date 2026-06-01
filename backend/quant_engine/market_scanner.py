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
    """计算短线评分 — 核心逻辑：位置第一，趋势第二

    基本原则：
    - 价格在历史高位 → 不推荐建仓（追高风险大）
    - 价格在历史低位/回踩支撑 → 加分（盈亏比好）
    - 均线多头排列+价格回踩MA10/MA20 → 最佳短线买点
    - RSI超买 → 减分，超卖 → 加分
    """
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
    if len(closes) < 20:
        return None

    current_price = float(closes.iloc[-1])

    # ── 1. 历史位置评分 (40%) ──
    hist_high = float(closes.max())
    hist_low = float(closes.min())
    hist_range = hist_high - hist_low if hist_high > hist_low else 1
    hist_pct = (current_price - hist_low) / hist_range * 100  # 0=最低 100=最高

    if hist_pct >= 95:
        position_score = 0    # 历史最高附近 → 绝对不能建仓
    elif hist_pct >= 85:
        position_score = 15   # 高位 → 风险大
    elif hist_pct >= 70:
        position_score = 35   # 中高位 → 谨慎
    elif hist_pct >= 50:
        position_score = 55   # 中位 → 中性
    elif hist_pct >= 30:
        position_score = 70   # 中低位 → 相对安全
    elif hist_pct >= 15:
        position_score = 85   # 低位 → 布局机会
    else:
        position_score = 95   # 历史底部 → 绝佳建仓区

    # 距离历史高点越近越危险
    dist_from_high = (hist_high - current_price) / hist_high * 100
    if dist_from_high < 3:
        position_score -= 20  # 离顶部太近
    elif dist_from_high < 8:
        position_score -= 10

    # ── 2. 技术形态评分 (35%) ──
    ma5 = calc_ma(closes, 5).iloc[-1] if len(closes) >= 5 else current_price
    ma10 = calc_ma(closes, 10).iloc[-1] if len(closes) >= 10 else current_price
    ma20 = calc_ma(closes, 20).iloc[-1] if len(closes) >= 20 else current_price
    ma60 = calc_ma(closes, 60).iloc[-1] if len(closes) >= 60 else current_price

    shape_score = 50

    # 均线排列方向
    is_uptrend = ma5 > ma10 > ma20  # 多头排列
    is_downtrend = ma5 < ma10 < ma20  # 空头排列

    # 价格相对MA位置（回踩还是偏离）
    above_ma10_pct = (current_price - ma10) / ma10 * 100

    if is_uptrend:
        shape_score += 15  # 趋势向上加分
        # 回踩MA10不破 → 最佳短线买点
        if -2 < above_ma10_pct < 1:
            shape_score += 25
        # 回踩MA20不破 → 次佳买点
        elif -3 < above_ma10_pct < -1:
            shape_score += 15
        # 偏离MA10太远 → 追高
        elif above_ma10_pct > 5:
            shape_score -= 15
        elif above_ma10_pct > 3:
            shape_score -= 5
    elif is_downtrend:
        shape_score -= 10  # 趋势向下减分
        # 超跌反弹机会
        if above_ma10_pct < -10:
            shape_score += 10  # 超跌
        elif above_ma10_pct < -5:
            shape_score += 5
    else:
        # 震荡市，靠近均线支撑加分
        if -2 < above_ma10_pct < 2:
            shape_score += 10

    # 价格在MA60上方加分（中长期趋势好）
    if current_price > ma60:
        shape_score += 5
    else:
        shape_score -= 5

    # ── 3. RSI评分 (15%) ──
    rsi_score = 50
    if len(closes) >= 15:
        rsi = calc_rsi(closes, 14)
        if not np.isnan(rsi.iloc[-1]):
            rsi_val = rsi.iloc[-1]
            if 30 <= rsi_val <= 45:
                rsi_score = 85  # 超卖区但不极端 → 买入机会
            elif rsi_val < 30:
                rsi_score = 75  # 超卖 → 反弹机会
            elif 45 < rsi_val < 55:
                rsi_score = 60  # 中性偏多
            elif 55 <= rsi_val <= 65:
                rsi_score = 45  # 偏强但不极端
            elif 65 < rsi_val <= 75:
                rsi_score = 25  # 偏热
            else:
                rsi_score = 10  # RSI>75 超买，回避

    # ── 4. 量能评分 (10%) ──
    vol_score = 50
    volumes = np.array([float(d.get('volume', 0)) for d in kline])
    if len(volumes) >= 20:
        vol_5d = np.mean(volumes[-5:])
        vol_20d = np.mean(volumes[-20:])
        vol_ratio = vol_5d / max(vol_20d, 1)
        daily_ret = closes.pct_change() * 100

        last_ret = daily_ret.iloc[-1] if len(daily_ret) > 1 else 0

        # 缩量回调 → 健康（洗盘）
        if last_ret < 0 and vol_ratio < 0.8:
            vol_score = 75
        # 放量上涨 → 强势
        elif last_ret > 0 and vol_ratio > 1.5:
            vol_score = 65
        # 放量下跌 → 恐慌
        elif last_ret < -1 and vol_ratio > 1.5:
            vol_score = 20
        # 缩量上涨 → 动能不足
        elif last_ret > 0 and vol_ratio < 0.6:
            vol_score = 35
        else:
            vol_score = 50

    # ── 综合评分 ──
    # 权重：位置40% + 形态35% + RSI 15% + 量能10%
    total = round(position_score * 0.40 + shape_score * 0.35 +
                  rsi_score * 0.15 + vol_score * 0.10, 2)

    # 额外惩罚/奖励
    # 低位+下行趋势=接飞刀（大幅减分）
    if hist_pct < 20 and is_downtrend:
        total *= 0.4  # 下降趋势中的低位不是底，是接飞刀
    # 低位+上行趋势=最佳买点（大幅加分）
    elif hist_pct < 40 and is_uptrend:
        total = min(100, total * 1.2)  # 底部反转，加分
    # 高位+追涨=危险
    elif position_score < 20 and above_ma10_pct > 3:
        total *= 0.5

    # 建仓信号
    if total >= 75:
        build_signal = '🔥 强烈建仓'
        position = '60-80%'
        advice = '价格位置安全+技术形态好，可重仓布局'
    elif total >= 60:
        build_signal = '✅ 建议建仓'
        position = '40-60%'
        advice = '性价比合适，可分批建仓'
    elif total >= 45:
        build_signal = '⏳ 观察等待'
        position = '20-30%'
        advice = '条件一般，等更好位置再入场'
    elif total >= 30:
        build_signal = '⚠️ 注意风险'
        position = '0-10%'
        advice = '位置偏高或形态转弱，暂不建仓'
    else:
        build_signal = '🚫 回避'
        position = '0%'
        advice = '风险大，观望为主'

    # 短线方向
    short_term = ''
    if is_uptrend and -2 < above_ma10_pct < 2:
        short_term = '📈 上升趋势回踩支撑，持有1-4周'
    elif is_uptrend and above_ma10_pct > 5:
        short_term = '⚠️ 趋势向上但偏离较远，等回踩再入'
    elif is_downtrend and above_ma10_pct < -8:
        short_term = '📉 超跌反弹机会，短线快进快出'
    elif is_downtrend:
        short_term = '📉 下降趋势，不建议参与'
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
            'position': round(position_score, 2),
            'technical_shape': round(shape_score, 2),
            'rsi': round(rsi_score, 2),
            'volume': round(vol_score, 2),
        },
        'technical': {
            'ma5': round(float(ma5), 4),
            'ma10': round(float(ma10), 4),
            'ma20': round(float(ma20), 4),
            'ma60': round(float(ma60), 4),
            'above_ma10_pct': round(float(above_ma10_pct), 2),
            'above_ma10': bool(current_price > ma10),
            'is_uptrend': bool(is_uptrend),
            'is_downtrend': bool(is_downtrend),
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
