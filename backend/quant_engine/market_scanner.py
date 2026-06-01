"""基金真实市场扫描引擎 — 全市场ETF实时扫描+评分+建仓推荐"""
import time
import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime
from typing import Optional

from .indicators import calc_ma, calc_rsi, calc_macd, calc_bollinger
from .risk_metrics import max_drawdown


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
    # 1. 拉实时ETF行情
    try:
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
        score['capital_flow_pct'] = round(float(row.get('主力净流入-净占比', 0)), 2)
        score['scan_time'] = datetime.now().strftime('%H:%M')

        results.append(score)
        time.sleep(0.3)  # 避免请求过快

        if len(results) >= top_n * 2:  # 多拉一些供排序
            break

    # 5. 综合排序
    if not results:
        return [{'error': '无法获取足够K线数据'}]

    results.sort(key=lambda x: x.get('total_score', 0), reverse=True)

    return results[:top_n]


def _get_kline_real(code: str, days: int = 200) -> list:
    """使用真实数据源获取K线"""
    import httpx
    import json

    # 优先新浪财经ETF K线
    try:
        prefix = "sh" if code.startswith("51") or code.startswith("56") else "sz"
        url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={prefix}{code}&scale=240&datalen={days}'
        resp = httpx.get(url, timeout=10)
        data = json.loads(resp.text)
        if data and len(data) > 5:
            kline = []
            for d in data:
                kline.append({
                    'day': str(d['day'])[:10],
                    'open': float(d['open']),
                    'high': float(d['high']),
                    'low': float(d['low']),
                    'close': float(d['close']),
                    'volume': float(d.get('volume', 0)),
                })
            return kline
    except:
        pass

    # 备选：东方财富
    try:
        df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date="20250101", adjust="qfq")
        if df is not None and len(df) > 10:
            kline = []
            for _, r in df.iterrows():
                kline.append({
                    'day': str(r['日期'])[:10],
                    'open': float(r['开盘']),
                    'high': float(r['最高']),
                    'low': float(r['最低']),
                    'close': float(r['收盘']),
                    'volume': float(r.get('成交量', 0)),
                })
            return kline[-days:]
    except:
        pass

    return []


def _calc_short_term_score(kline: list, spot_row: pd.Series) -> Optional[dict]:
    """计算短线评分（聚焦1天-3月）"""
    closes = pd.Series([float(d['close']) for d in kline if float(d.get('close', 0)) > 0])
    if len(closes) < 20:
        return None

    current_price = float(closes.iloc[-1])

    # ── 短线技术评分 (50%) ──
    tech_score = 50

    # MA位置
    ma5 = calc_ma(closes, 5).iloc[-1] if len(closes) >= 5 else current_price
    ma10 = calc_ma(closes, 10).iloc[-1] if len(closes) >= 10 else current_price
    ma20 = calc_ma(closes, 20).iloc[-1] if len(closes) >= 20 else current_price
    ma60 = calc_ma(closes, 60).iloc[-1] if len(closes) >= 60 else current_price

    # 均线多头排列加分
    if current_price > ma5 > ma10 > ma20:
        tech_score += 20  # 强势多头
    elif current_price > ma10 > ma20:
        tech_score += 10
    elif current_price < ma20 and current_price > ma60:
        tech_score -= 5  # 震荡
    elif current_price < ma60:
        tech_score -= 15  # 弱势

    # 短线突破
    above_ma5 = (current_price - ma5) / ma5 * 100
    if -1 < above_ma5 < 3:
        tech_score += 10  # 回踩MA5不破
    elif above_ma5 > 5:
        tech_score -= 5  # 偏离MA5太远

    # RSI
    if len(closes) >= 15:
        rsi = calc_rsi(closes, 14)
        if not np.isnan(rsi.iloc[-1]):
            rsi_val = rsi.iloc[-1]
            if 40 < rsi_val < 60:
                tech_score += 10  # RSI中性偏强
            elif rsi_val >= 70:
                tech_score -= 10  # 超买
            elif rsi_val <= 30:
                tech_score += 15  # 超卖反弹机会
            elif rsi_val <= 40:
                tech_score += 5

    # MACD
    if len(closes) >= 26:
        dif, dea, macd_bar = calc_macd(closes)
        if not np.isnan(macd_bar.iloc[-1]):
            if macd_bar.iloc[-1] > 0 and macd_bar.iloc[-2] <= 0:
                tech_score += 15  # MACD翻红（短线买入信号）
            elif macd_bar.iloc[-1] > 0:
                tech_score += 5
            elif macd_bar.iloc[-1] < 0 and macd_bar.iloc[-2] >= 0:
                tech_score -= 10  # MACD翻绿
            # MACD柱加长
            if len(macd_bar) >= 3:
                if macd_bar.iloc[-1] > macd_bar.iloc[-2] > macd_bar.iloc[-3]:
                    tech_score += 5

    # 量能评分 (30%)
    vol_score = 50
    volumes = np.array([float(d.get('volume', 0)) for d in kline])
    if len(volumes) >= 20:
        vol_5d = np.mean(volumes[-5:])
        vol_20d = np.mean(volumes[-20:])
        vol_ratio = vol_5d / max(vol_20d, 1)

        if vol_ratio > 2:
            vol_score = 85  # 显著放量
        elif vol_ratio > 1.5:
            vol_score = 70
        elif vol_ratio > 1.0:
            vol_score = 55
        elif vol_ratio > 0.6:
            vol_score = 35
        else:
            vol_score = 20

        # 价量配合
        daily_ret = closes.pct_change() * 100
        if len(daily_ret) > 1:
            last_ret = daily_ret.iloc[-1]
            if last_ret > 0 and vol_ratio > 1.2:
                vol_score += 10  # 价涨量增
            elif last_ret < 0 and vol_ratio > 1.5:
                vol_score -= 15  # 价跌量增

    # 资金面评分 (20%)
    cap_score = 50
    flow_pct = float(spot_row.get('主力净流入-净占比', 0))
    if flow_pct > 2:
        cap_score = 80
    elif flow_pct > 0.5:
        cap_score = 65
    elif flow_pct > -0.5:
        cap_score = 50
    elif flow_pct > -2:
        cap_score = 35
    else:
        cap_score = 20

    # 综合评分
    total = round(tech_score * 0.50 + vol_score * 0.30 + cap_score * 0.20, 2)

    # 建仓信号
    if total >= 75:
        build_signal = '🔥 强烈建仓'
        position = '60-80%'
    elif total >= 60:
        build_signal = '✅ 建议建仓'
        position = '40-60%'
    elif total >= 45:
        build_signal = '⏳ 观察等待'
        position = '20-30%'
    elif total >= 30:
        build_signal = '⚠️ 注意风险'
        position = '0-10%'
    else:
        build_signal = '🚫 回避'
        position = '0%'

    # 短线持有建议
    if tech_score >= 65:
        short_term = '短线看多，持有1-2周观察'
    elif tech_score >= 45:
        short_term = '震荡格局，短线波段操作'
    else:
        short_term = '短线偏弱，暂不参与'

    return {
        'total_score': total,
        'build_signal': build_signal,
        'suggested_position': position,
        'short_term_advice': short_term,
        'scores': {
            'technical': round(tech_score, 2),
            'volume': round(vol_score, 2),
            'capital_flow': round(cap_score, 2),
        },
        'technical': {
            'ma5': round(float(ma5), 4),
            'ma10': round(float(ma10), 4),
            'ma20': round(float(ma20), 4),
            'ma60': round(float(ma60), 4),
            'above_ma5_pct': round(float(above_ma5), 2),
            'above_ma5': current_price > ma5,
            'above_ma10': current_price > ma10,
            'above_ma20': current_price > ma20,
            'above_ma60': current_price > ma60,
        },
    }


def scan_build_candidates(top_n: int = 10) -> list:
    """扫描全市场找出最适合建仓的ETF

    返回真实市场数据，无模拟
    """
    results = scan_etf_market(top_n=top_n * 2)
    # 只返回建仓信号>=观察等待的
    candidates = [r for r in results if '强烈建仓' in str(r.get('build_signal', '')) or
                  '建议建仓' in str(r.get('build_signal', ''))]
    if not candidates:
        # 如果都没有强烈信号，返回评分最高的
        candidates = results[:top_n]
    return candidates[:top_n]
