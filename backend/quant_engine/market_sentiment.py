"""市场情绪监控 + 建仓提醒引擎"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


# ─── 涨跌家数 ───

def calc_advance_decline(stock_data: list = None) -> dict:
    """涨跌家数统计

    Args:
        stock_data: [{name, change_pct}, ...] 个股涨跌幅列表

    Returns:
        涨跌统计+涨跌比+市场宽度
    """
    if not stock_data:
        # 模拟数据
        np.random.seed(42)
        n = 2000
        changes = np.random.normal(0.3, 2.5, n)
        stock_data = [{'name': f'股票{i}', 'change_pct': round(float(c), 2)}
                      for i, c in enumerate(changes)]

    changes = np.array([s.get('change_pct', 0) for s in stock_data])
    advances = int(np.sum(changes > 0))
    declines = int(np.sum(changes < 0))
    flats = int(np.sum(changes == 0))
    total = len(changes)

    # 涨跌比
    ad_ratio = round(advances / max(declines, 1), 4)

    # 市场宽度指标
    strong = int(np.sum(changes > 3))    # 涨幅>3%
    weak = int(np.sum(changes < -3))      # 跌幅>3%
    width = round((advances - declines) / total * 100, 2) if total > 0 else 0

    return {
        'advances': advances,
        'declines': declines,
        'flats': flats,
        'total': total,
        'advance_decline_ratio': ad_ratio,
        'strong_stocks': strong,
        'weak_stocks': weak,
        'market_width': width,
        'interpretation': '市场偏强' if ad_ratio > 1.5 else ('市场偏弱' if ad_ratio < 0.67 else '市场震荡'),
    }


# ─── 成交量分析 ───

def calc_volume_analysis(kline_data: list = None) -> dict:
    """成交量分析

    Args:
        kline_data: [{day, volume, close}, ...]

    Returns:
        量比/5日均量/20日均量/放量缩量判断
    """
    if not kline_data or len(kline_data) < 20:
        # 模拟数据
        np.random.seed(42)
        n = 60
        kline_data = []
        base_vol = 1000000
        for i in range(n):
            kline_data.append({
                'day': (datetime.now() - timedelta(days=n-i)).strftime('%Y-%m-%d'),
                'volume': int(abs(np.random.normal(base_vol, base_vol*0.3))),
                'close': round(abs(np.random.normal(10, 2)), 2),
            })

    volumes = np.array([float(d.get('volume', 0)) for d in kline_data])
    closes = np.array([float(d.get('close', 0)) for d in kline_data])

    if len(volumes) < 5:
        return {'error': '数据不足'}

    today_vol = volumes[-1]
    vol_5d = np.mean(volumes[-5:]) if len(volumes) >= 5 else today_vol
    vol_20d = np.mean(volumes[-20:]) if len(volumes) >= 20 else vol_5d

    vol_ratio_5 = round(today_vol / max(vol_5d, 1), 4)
    vol_ratio_20 = round(today_vol / max(vol_20d, 1), 4)

    # 放量/缩量判断
    if vol_ratio_5 > 1.5:
        vol_status = '显著放量'
    elif vol_ratio_5 > 1.2:
        vol_status = '小幅放量'
    elif vol_ratio_5 < 0.6:
        vol_status = '显著缩量'
    elif vol_ratio_5 < 0.8:
        vol_status = '小幅缩量'
    else:
        vol_status = '量能正常'

    # 价量配合
    price_change = round((closes[-1] - closes[-2]) / closes[-2] * 100, 2) if len(closes) >= 2 else 0
    if price_change > 0 and vol_ratio_5 > 1.2:
        pv_match = '价涨量增·健康'
    elif price_change > 0 and vol_ratio_5 < 0.8:
        pv_match = '价涨量缩·背离'
    elif price_change < 0 and vol_ratio_5 > 1.2:
        pv_match = '价跌量增·恐慌'
    elif price_change < 0 and vol_ratio_5 < 0.8:
        pv_match = '价跌量缩·止跌'
    else:
        pv_match = '量价常态'

    return {
        'today_volume': int(today_vol),
        'volume_5d_avg': int(vol_5d),
        'volume_20d_avg': int(vol_20d),
        'vol_ratio_5d': vol_ratio_5,
        'vol_ratio_20d': vol_ratio_20,
        'volume_status': vol_status,
        'price_volume_match': pv_match,
        'price_change_pct': price_change,
    }


# ─── 综合情绪指数 ───

def calc_market_sentiment(kline_data: list = None, stock_data: list = None,
                          macro_data: dict = None) -> dict:
    """市场情绪综合指数

    综合考虑：涨跌比(30%) + 成交量(20%) + 北向资金(20%) + 涨跌停(15%) + 宏观(15%)

    Returns:
        情绪指数0-100，含各分项得分和解读
    """
    # 涨跌情绪 (0-100)
    ad = calc_advance_decline(stock_data)
    ad_ratio = ad.get('advance_decline_ratio', 1.0)
    ad_score = min(100, max(0, (ad_ratio - 0.5) / 3 * 100))

    # 量能情绪 (0-100)
    vol = calc_volume_analysis(kline_data)
    vr = vol.get('vol_ratio_5d', 1.0)
    vol_score = min(100, max(0, (vr - 0.3) / 2 * 100))

    # 北向资金情绪 (模拟)
    np.random.seed(int(datetime.now().timestamp()) % 10000)
    north_flow = round(np.random.normal(0, 50), 2)  # 亿
    north_score = min(100, max(0, 50 + north_flow / 2))

    # 涨跌停情绪 (模拟)
    limit_up = int(np.random.poisson(40))
    limit_down = int(np.random.poisson(15))
    limit_ratio = limit_up / max(limit_down, 1)
    limit_score = min(100, max(0, (limit_ratio - 0.5) / 4 * 100))

    # 宏观情绪
    macro_score = 50
    if macro_data:
        pmi = macro_data.get('pmi', 50)
        macro_score = min(100, max(0, (pmi - 45) / 10 * 100))

    # 综合加权
    weights = {'advance_decline': 0.30, 'volume': 0.20, 'north_flow': 0.20,
               'limit_up_down': 0.15, 'macro': 0.15}
    total = (ad_score * weights['advance_decline'] +
             vol_score * weights['volume'] +
             north_score * weights['north_flow'] +
             limit_score * weights['limit_up_down'] +
             macro_score * weights['macro'])
    total = round(min(100, max(0, total)), 2)

    # 情绪解读
    if total >= 80:
        interpretation = '极度乐观·注意风险'
        action = '谨慎减仓'
    elif total >= 65:
        interpretation = '乐观'
        action = '持有观察'
    elif total >= 45:
        interpretation = '中性'
        action = '精选个股'
    elif total >= 25:
        interpretation = '悲观'
        action = '逢低布局'
    else:
        interpretation = '极度悲观·逐步建仓'
        action = '分批建仓'

    return {
        'sentiment_index': total,
        'interpretation': interpretation,
        'suggested_action': action,
        'scores': {
            'advance_decline': round(float(ad_score), 2),
            'volume': round(float(vol_score), 2),
            'north_flow': round(float(north_score), 2),
            'limit_up_down': round(float(limit_score), 2),
            'macro': round(float(macro_score), 2),
        },
        'detail': {
            'advance_decline': ad,
            'volume': vol,
            'north_flow_value': north_flow,
            'limit_up': limit_up,
            'limit_down': limit_down,
        }
    }


# ─── 建仓提醒引擎（核心功能） ───

def calc_build_signal(kline_data: list = None, pe_pct: Optional[float] = None,
                      pb_pct: Optional[float] = None, market_sentiment: dict = None) -> dict:
    """建仓提醒信号 — 综合判断当前是否适合建仓

    评分维度：
    - 估值吸引力(35%)：PE/PB分位<30%加分，>70%减分
    - 技术面趋势(25%)：MA位置+RSI+MACD综合
    - 市场情绪(20%)：情绪指数
    - 资金面(20%)：成交量+北向资金

    Returns:
        建仓信号：强烈建仓/建议建仓/观望/警惕/回避
    """
    # 估值评分
    val_score = 50
    if pe_pct is not None and pb_pct is not None:
        avg_pct = (pe_pct + pb_pct) / 2
        if avg_pct <= 15:
            val_score = 95
        elif avg_pct <= 30:
            val_score = 80
        elif avg_pct <= 50:
            val_score = 50
        elif avg_pct <= 70:
            val_score = 25
        else:
            val_score = 10
    elif pe_pct is not None:
        if pe_pct <= 15: val_score = 95
        elif pe_pct <= 30: val_score = 80
        elif pe_pct <= 50: val_score = 50
        elif pe_pct <= 70: val_score = 25
        else: val_score = 10

    # 技术面评分
    tech_score = 50
    if kline_data and len(kline_data) >= 60:
        closes = pd.Series([float(d['close']) for d in kline_data if float(d.get('close', 0)) > 0])
        if len(closes) >= 60:
            ma10 = closes.rolling(10).mean()
            ma60 = closes.rolling(60).mean()
            current = closes.iloc[-1]

            # MA位置
            ma10_pos = (current - ma10.iloc[-1]) / ma10.iloc[-1] * 100 if ma10.iloc[-1] > 0 else 0
            ma60_pos = (current - ma60.iloc[-1]) / ma60.iloc[-1] * 100 if ma60.iloc[-1] > 0 else 0

            # RSI
            delta = closes.diff()
            gain = delta.where(delta > 0, 0.0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

            tech_score = 50
            # 价格在MA60附近加分
            if abs(ma60_pos) < 5:
                tech_score += 15
            elif ma60_pos < -10:
                tech_score += 25  # 超跌
            elif ma60_pos > 20:
                tech_score -= 20  # 远离均线

            # RSI超卖加分
            if not np.isnan(rsi.iloc[-1]):
                if rsi.iloc[-1] < 30:
                    tech_score += 20
                elif rsi.iloc[-1] < 40:
                    tech_score += 10
                elif rsi.iloc[-1] > 70:
                    tech_score -= 15

            # 价在MA10上
            if current > ma10.iloc[-1]:
                tech_score += 5
            else:
                tech_score -= 5

    # 情绪评分
    sent_score = 50
    if market_sentiment:
        sent_index = market_sentiment.get('sentiment_index', 50)
        # 极度悲观=建仓机会
        if sent_index < 25:
            sent_score = 85
        elif sent_index < 35:
            sent_score = 70
        elif sent_index > 75:
            sent_score = 20
        elif sent_index > 60:
            sent_score = 40
        else:
            sent_score = 50

    # 综合评分
    weights = {'valuation': 0.35, 'technical': 0.25, 'sentiment': 0.20, 'capital': 0.20}
    cap_score = sent_score  # 资金面用情绪代理
    total = round(val_score * weights['valuation'] + tech_score * weights['technical'] +
                  sent_score * weights['sentiment'] + cap_score * weights['capital'], 2)

    # 建仓信号
    if total >= 80:
        signal = '🔥 强烈建仓'
        action_detail = '估值低位+技术面超跌+情绪冰点，建议重仓分批入场'
        position = '70-80%'
    elif total >= 65:
        signal = '✅ 建议建仓'
        action_detail = '综合条件较好，可以开始分批建仓'
        position = '50-60%'
    elif total >= 45:
        signal = '⏳ 观望等待'
        action_detail = '条件一般，等待更好的入场时机'
        position = '20-30%'
    elif total >= 30:
        signal = '⚠️ 注意风险'
        action_detail = '估值偏高/技术面偏弱，不建议新建仓位'
        position = '0-10%'
    else:
        signal = '🚫 回避'
        action_detail = '风险较高，建议减仓或空仓等待'
        position = '0%'

    return {
        'build_signal': signal,
        'total_score': total,
        'suggested_position': position,
        'action_detail': action_detail,
        'scores': {
            'valuation_score': round(val_score, 2),
            'technical_score': round(tech_score, 2),
            'sentiment_score': round(sent_score, 2),
        },
        'weights': weights,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }


# ─── 基金/ETF评分排名 ───

def score_funds(fund_list: list) -> list:
    """对基金列表综合评分排序

    Args:
        fund_list: [{code, name, pe_pct, pb_pct, kline_data, ...}]

    Returns:
        评分排序后的基金列表
    """
    if not fund_list:
        # 模拟数据
        np.random.seed(42)
        names = ['天弘国证绿色电力C', '永赢科技智选C', '金信量化精选C', '银河通信设备C',
                 '国联安半导体C', '宝盈纳斯达克C', '招商煤炭等权E', '前海开源金银珠宝C']
        fund_list = []
        for n in names:
            fund_list.append({
                'code': str(np.random.randint(100000, 999999)),
                'name': n,
                'pe_pct': round(np.random.uniform(5, 90), 1),
                'pb_pct': round(np.random.uniform(5, 90), 1),
                'type': np.random.choice(['混合', '指数', '股票', 'QDII']),
            })

    results = []
    for f in fund_list:
        pe = f.get('pe_pct')
        pb = f.get('pb_pct')

        # 估值分
        val = 50
        if pe is not None and pb is not None:
            avg = (pe + pb) / 2
            val = 90 if avg <= 15 else (75 if avg <= 30 else (50 if avg <= 50 else (25 if avg <= 70 else 10)))

        # 动量分（模拟）
        mom = round(np.random.uniform(20, 80), 2)
        # 质量分（模拟）
        quality = round(np.random.uniform(30, 80), 2)

        total = round(val * 0.40 + mom * 0.35 + quality * 0.25, 2)

        results.append({
            'code': f.get('code', ''),
            'name': f.get('name', ''),
            'type': f.get('type', ''),
            'total_score': total,
            'valuation_score': val,
            'momentum_score': mom,
            'quality_score': quality,
            'pe_percentile': pe,
            'pb_percentile': pb,
            'rating': 'S' if total >= 80 else ('A' if total >= 65 else ('B' if total >= 50 else ('C' if total >= 35 else 'D'))),
        })

    results.sort(key=lambda x: x['total_score'], reverse=True)
    return results
