"""AI智能分析引擎 — 综合技术面/估值/动量/风险评分 + 综合评级 + 投资建议"""
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List

from .indicators import calc_ma, calc_rsi, calc_macd, calc_bollinger
from .risk_metrics import max_drawdown, annual_volatility


# ─── 辅助：归一化工具 ───

def _normalize(val, ref_low=0, ref_high=100, clip=True):
    """将val映射到0-100区间（ref_low对应0分，ref_high对应100分）"""
    if ref_high == ref_low:
        return 50.0
    score = (val - ref_low) / (ref_high - ref_low) * 100
    if clip:
        score = np.clip(score, 0, 100)
    return round(float(score), 4)


# ═══════════════════════════════════════════════
# 1. 综合技术面评分
# ═══════════════════════════════════════════════

def calc_technical_score(
    df: pd.DataFrame,
    ma_periods: Optional[list] = None
) -> Dict[str, Any]:
    """
    综合技术面评分（0-100分），权重：
      MA位置 30% | RSI 25% | MACD 20% | 布林带 15% | 成交量 10%
    参数:
      df: 需包含 close, high, low, volume 列
      ma_periods: 均线列表，默认 [5,10,20,60]
    返回:
      { "total_score": float, "details": { ... }, "weights": { ... } }
    """
    if ma_periods is None:
        ma_periods = [5, 10, 20, 60]
    close = df['close'].values
    vol = df['volume'].values
    n = len(df)

    weights = {'ma': 0.30, 'rsi': 0.25, 'macd': 0.20, 'bollinger': 0.15, 'volume': 0.10}

    # ── MA位置评分 ──
    # 价格越靠近短期MA(5)上方得分越高
    ma5 = calc_ma(df['close'], 5).values
    if n > 5 and not np.isnan(ma5[-1]):
        # (close/ma5 - 1)，正偏离在+10%内线性评分
        ma_dev = (close[-1] / ma5[-1]) - 1.0
        ma_score = _normalize(ma_dev, -0.05, 0.10)  # -5%偏离=0分，+10%偏离=100分
    else:
        ma_score = 50.0

    # ── RSI评分 ──
    rsi_series = calc_rsi(df['close'], 14)
    rsi_val = rsi_series.values[-1] if n > 14 and not np.isnan(rsi_series.values[-1]) else 50.0
    # RSI: 30以下超卖高分，70以上超买低分
    if rsi_val <= 30:
        rsi_score = 100.0
    elif rsi_val >= 70:
        rsi_score = 0.0
    else:
        # 30-70之间线性：30=100分, 70=0分
        rsi_score = round((70 - rsi_val) / 40 * 100, 4)

    # ── MACD评分 ──
    dif, dea, macd = calc_macd(df['close'])
    if n > 26 and not np.isnan(macd.values[-1]):
        macd_val = macd.values[-1]
        macd_hist_prev = macd.values[-2] if n > 27 and not np.isnan(macd.values[-2]) else 0
        # MACD柱为正+发散给高分
        macd_score = 50.0
        if macd_val > 0:
            macd_score += 25.0
        if macd_val > macd_hist_prev:
            macd_score += 25.0
        macd_score = np.clip(macd_score, 0, 100)
    else:
        macd_score = 50.0

    # ── 布林带评分 ──
    upper, mid, lower = calc_bollinger(df['close'], 20, 2)
    if n > 20 and not np.isnan(upper.values[-1]) and not np.isnan(lower.values[-1]):
        last_close = close[-1]
        # 在下轨附近→高分(超卖), 上轨附近→低分(超买)
        bb_width = upper.values[-1] - lower.values[-1]
        if bb_width > 0:
            pos_in_band = (last_close - lower.values[-1]) / bb_width  # 0~1
            bb_score = round((1.0 - pos_in_band) * 100, 4)
        else:
            bb_score = 50.0
    else:
        bb_score = 50.0

    # ── 成交量评分 ──
    if n > 20:
        vol_ma5 = np.mean(vol[-5:]) if n >= 5 else np.mean(vol)
        vol_ma20 = np.mean(vol[-20:])
        if vol_ma20 > 0:
            vol_ratio = vol_ma5 / vol_ma20
            # 量比1.5以上放量上涨积极，0.5以下缩量低迷
            vol_score = _normalize(vol_ratio, 0.3, 2.0)
        else:
            vol_score = 50.0
    else:
        vol_score = 50.0

    total = round(
        ma_score * weights['ma']
        + rsi_score * weights['rsi']
        + macd_score * weights['macd']
        + bb_score * weights['bollinger']
        + vol_score * weights['volume'],
        4
    )

    return {
        "total_score": total,
        "details": {
            "ma_score": round(ma_score, 4),
            "rsi_score": round(rsi_score, 4),
            "macd_score": round(macd_score, 4),
            "bollinger_score": round(bb_score, 4),
            "volume_score": round(vol_score, 4),
        },
        "weights": weights,
    }


# ═══════════════════════════════════════════════
# 2. 综合估值评分
# ═══════════════════════════════════════════════

def calc_valuation_score(
    pe_percentile: Optional[float] = None,
    pb_percentile: Optional[float] = None,
    pe_weight: float = 0.5,
    pb_weight: float = 0.5,
) -> Dict[str, Any]:
    """
    综合估值评分（0-100分），越低分越高估值安全。
    分位值越低（历史低位），估值越安全→分数越高。
    分位值越高（历史高位），估值越危险→分数越低。
    参数:
      pe_percentile: PE历史分位值 0-100（如 20.5 表示20.5%分位）
      pb_percentile: PB历史分位值 0-100
      pe_weight, pb_weight: PE/PB权重
    返回:
      { "valuation_score": float, "details": {...} }
    """
    if pe_percentile is None and pb_percentile is None:
        return {"valuation_score": 50.0, "details": {"pe_score": 50.0, "pb_score": 50.0}, "msg": "无估值数据"}

    # 分位值越低分越高: score = 100 - percentile
    pe_score = 50.0
    if pe_percentile is not None:
        pe_score = round(100.0 - float(pe_percentile), 4)

    pb_score = 50.0
    if pb_percentile is not None:
        pb_score = round(100.0 - float(pb_percentile), 4)

    # 加权平均
    w_sum = 0
    if pe_percentile is not None:
        w_sum += pe_weight
    if pb_percentile is not None:
        w_sum += pb_weight
    if w_sum == 0:
        total = 50.0
    else:
        total = round((pe_score * (pe_weight if pe_percentile is not None else 0)
                       + pb_score * (pb_weight if pb_percentile is not None else 0)) / w_sum, 4)

    pe_pctl = round(float(pe_percentile), 4) if pe_percentile is not None else None
    pb_pctl = round(float(pb_percentile), 4) if pb_percentile is not None else None

    return {
        "valuation_score": total,
        "details": {
            "pe_score": round(pe_score, 4),
            "pb_score": round(pb_score, 4),
            "pe_percentile": pe_pctl,
            "pb_percentile": pb_pctl,
        },
    }


# ═══════════════════════════════════════════════
# 3. 多维度动量评分
# ═══════════════════════════════════════════════

def calc_momentum_score(
    df: pd.DataFrame,
    short_period: int = 5,
    mid_period: int = 20,
    long_period: int = 60,
    short_weight: float = 0.3,
    mid_weight: float = 0.4,
    long_weight: float = 0.3,
) -> Dict[str, Any]:
    """
    多维度动量评分（0-100分）。
    动量 = 当前价格 / N日前价格 - 1，再映射到0-100。
    参数:
      df: 含close列
      short_period, mid_period, long_period: 短/中/长期窗口
      short_weight, mid_weight, long_weight: 权重
    返回:
      { "momentum_score": float, "details": {...}, "weights": {...} }
    """
    close = df['close'].values
    n = len(close)

    def _period_momentum(p: int) -> float:
        if n <= p:
            return 50.0
        ret = (close[-1] / close[-1 - p]) - 1.0
        # 月化处理使不同周期可比
        annualized = (1 + ret) ** (250 / p) - 1
        # -50%~+100% 映射到0-100
        return _normalize(annualized, -0.50, 1.00)

    short_mom = _period_momentum(short_period)
    mid_mom = _period_momentum(mid_period)
    long_mom = _period_momentum(long_period)

    total = round(
        short_mom * short_weight
        + mid_mom * mid_weight
        + long_mom * long_weight,
        4
    )

    return {
        "momentum_score": total,
        "details": {
            "short_period": short_period,
            "mid_period": mid_period,
            "long_period": long_period,
            "short_momentum": round(short_mom, 4),
            "mid_momentum": round(mid_mom, 4),
            "long_momentum": round(long_mom, 4),
        },
        "weights": {
            "short_weight": short_weight,
            "mid_weight": mid_weight,
            "long_weight": long_weight,
        },
    }


# ═══════════════════════════════════════════════
# 4. 风险评分
# ═══════════════════════════════════════════════

def calc_risk_score(
    df: pd.DataFrame,
    alpha: float = 0.95,
    trading_days: int = 250,
) -> Dict[str, Any]:
    """
    风险评分（0-100分，越高代表风险越大）。
    综合：波动率(40%) + 最大回撤(35%) + VaR(25%)
    参数:
      df: 含close列
      alpha: VaR置信度
      trading_days: 年化交易日
    返回:
      { "risk_score": float, "details": {...} }
    """
    close = df['close'].values
    n = len(close)

    # ── 波动率评分 ──
    ann_vol = annual_volatility(df['close'], trading_days)
    if ann_vol is None:
        vol_score = 50.0
    else:
        # 年化波动率 5%~60% 映射到0-100分（越低越好）
        vol_score = 100.0 - _normalize(ann_vol, 5.0, 60.0)

    # ── 最大回撤评分 ──
    mdd = max_drawdown(df['close'])
    if mdd is None:
        dd_score = 50.0
    else:
        # 最大回撤 -5%~-60% 映射（负数，绝对值越大分越低）
        dd_score = 100.0 - _normalize(abs(mdd), 5.0, 60.0)

    # ── VaR评分 ──
    if n >= 20:
        daily_ret = pd.Series(close).pct_change().dropna().values
        if len(daily_ret) >= 20:
            var = np.percentile(daily_ret, (1 - alpha) * 100)  # 负值
            var_ann = var * np.sqrt(trading_days) * 100  # 年化百分比
            var_score = 100.0 - _normalize(abs(var_ann), 5.0, 60.0)
        else:
            var_score = 50.0
    else:
        var_score = 50.0

    weights = {'volatility': 0.40, 'drawdown': 0.35, 'var': 0.25}
    total = round(
        vol_score * weights['volatility']
        + dd_score * weights['drawdown']
        + var_score * weights['var'],
        4
    )

    return {
        "risk_score": total,
        "details": {
            "volatility_score": round(vol_score, 4),
            "drawdown_score": round(dd_score, 4),
            "var_score": round(var_score, 4),
            "annual_volatility": round(ann_vol, 4) if ann_vol is not None else None,
            "max_drawdown": round(mdd, 4) if mdd is not None else None,
            "var_annual_pct": round(float(var_ann), 4) if 'var_ann' in locals() else None,
        },
        "weights": weights,
    }


# ═══════════════════════════════════════════════
# 5. 综合评级
# ═══════════════════════════════════════════════

def calc_comprehensive_rating(
    df: pd.DataFrame,
    pe_percentile: Optional[float] = None,
    pb_percentile: Optional[float] = None,
    tech_weight: float = 0.35,
    valuation_weight: float = 0.25,
    momentum_weight: float = 0.20,
    risk_weight: float = 0.20,
) -> Dict[str, Any]:
    """
    综合评级：S/A/B/C/D五档，含评分明细。
    综合分 = 技术面*0.35 + 估值*0.25 + 动量*0.20 + (100-风险)*0.20
    评级标准:
      S: >=85, A: >=70, B: >=55, C: >=40, D: <40
    返回:
      { "rating": str, "composite_score": float, "details": {...} }
    """
    tech = calc_technical_score(df)
    val = calc_valuation_score(pe_percentile, pb_percentile)
    mom = calc_momentum_score(df)
    risk = calc_risk_score(df)

    tech_s = tech['total_score']
    val_s = val['valuation_score']
    mom_s = mom['momentum_score']
    # 风险分取反（低风险=高评分）
    risk_safe = 100.0 - risk['risk_score']

    composite = round(
        tech_s * tech_weight
        + val_s * valuation_weight
        + mom_s * momentum_weight
        + risk_safe * risk_weight,
        4
    )

    # 评级
    if composite >= 85:
        rating = 'S'
    elif composite >= 70:
        rating = 'A'
    elif composite >= 55:
        rating = 'B'
    elif composite >= 40:
        rating = 'C'
    else:
        rating = 'D'

    return {
        "rating": rating,
        "composite_score": composite,
        "details": {
            "technical_score": round(tech_s, 4),
            "valuation_score": round(val_s, 4),
            "momentum_score": round(mom_s, 4),
            "risk_safety_score": round(risk_safe, 4),
            "risk_score": round(risk['risk_score'], 4),
        },
        "weights": {
            "technical": tech_weight,
            "valuation": valuation_weight,
            "momentum": momentum_weight,
            "risk_safety": risk_weight,
        },
        "sub_scores": {
            "technical": tech,
            "valuation": val,
            "momentum": mom,
            "risk": risk,
        },
    }


# ═══════════════════════════════════════════════
# 6. 投资建议
# ═══════════════════════════════════════════════

def calc_investment_advice(
    rating_result: Dict[str, Any],
    current_position_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    基于综合评分给出操作建议（仓位+方向+逻辑）。
    参数:
      rating_result: calc_comprehensive_rating() 的返回值
      current_position_pct: 当前仓位百分比
    返回:
      { "action": str, "position_advice": str, "direction": str, "logic": str }
    """
    score = rating_result.get('composite_score', 50)
    rating = rating_result.get('rating', 'B')
    tech = rating_result.get('details', {}).get('technical_score', 50)
    val = rating_result.get('details', {}).get('valuation_score', 50)
    mom = rating_result.get('details', {}).get('momentum_score', 50)
    risk_safe = rating_result.get('details', {}).get('risk_safety_score', 50)

    pos = current_position_pct if current_position_pct is not None else 50.0

    # ── 方向判断 ──
    if score >= 70:
        direction = "做多"
    elif score >= 45:
        direction = "中性偏多" if mom > 50 else "中性偏空"
    elif score >= 30:
        direction = "偏空"
    else:
        direction = "做空/回避"

    # ── 仓位建议 ──
    if score >= 85:
        target_pos = 90
        pos_advice = "重仓(80-100%)"
    elif score >= 70:
        target_pos = 65
        pos_advice = "中仓(50-80%)"
    elif score >= 55:
        target_pos = 40
        pos_advice = "轻仓(20-50%)"
    elif score >= 40:
        target_pos = 20
        pos_advice = "观察仓(<20%)"
    else:
        target_pos = 0
        pos_advice = "空仓观望"

    action = "加仓" if target_pos > pos + 10 else ("减仓" if target_pos < pos - 10 else "持有")

    # ── 逻辑说明 ──
    logic_parts = []
    if tech >= 70:
        logic_parts.append(f"技术面偏强({tech}分)")
    elif tech <= 40:
        logic_parts.append(f"技术面偏弱({tech}分)")
    else:
        logic_parts.append(f"技术面中性({tech}分)")

    if val >= 70:
        logic_parts.append(f"估值安全({val}分)")
    elif val <= 40:
        logic_parts.append(f"估值偏高({val}分)")
    else:
        logic_parts.append(f"估值适中({val}分)")

    if risk_safe >= 70:
        logic_parts.append("风险可控")
    elif risk_safe <= 40:
        logic_parts.append("风险偏高")
    else:
        logic_parts.append("风险适中")

    logic = f"综合评级{rating}({score}分)，{'、'.join(logic_parts)}。建议{pos_advice}，{direction}方向。"

    return {
        "action": action,
        "position_advice": pos_advice,
        "target_position_pct": target_pos,
        "direction": direction,
        "logic": logic,
        "current_position_pct": pos,
        "rating": rating,
        "composite_score": score,
    }


# ═══════════════════════════════════════════════
# 7. 一键基金分析报告
# ═══════════════════════════════════════════════

def generate_full_report(
    df: pd.DataFrame,
    pe_percentile: Optional[float] = None,
    pb_percentile: Optional[float] = None,
    current_position_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    一键生成完整分析报告：整合技术面、估值、动量、风险、评级、投资建议。
    参数:
      df: k线DataFrame（需含 close, high, low, volume）
      pe_percentile: PE历史分位
      pb_percentile: PB历史分位
      current_position_pct: 当前仓位
    返回:
      { "report": {...} }
    """
    # 1. 综合评级（内含所有子评分）
    rating = calc_comprehensive_rating(df, pe_percentile, pb_percentile)

    # 2. 投资建议
    advice = calc_investment_advice(rating, current_position_pct)

    # 3. 提取关键数值摘要
    tech_detail = rating.get('sub_scores', {}).get('technical', {}).get('details', {})
    risk_detail = rating.get('sub_scores', {}).get('risk', {}).get('details', {})

    report = {
        "report_time": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        "basic_info": {
            "data_points": len(df),
            "latest_close": round(float(df['close'].iloc[-1]), 4) if len(df) > 0 else None,
            "latest_date": str(df.index[-1]) if hasattr(df, 'index') and len(df.index) > 0 else None,
        },
        "technical_analysis": {
            "score": rating.get('details', {}).get('technical_score'),
            "ma_score": tech_detail.get('ma_score'),
            "rsi_score": tech_detail.get('rsi_score'),
            "macd_score": tech_detail.get('macd_score'),
            "bollinger_score": tech_detail.get('bollinger_score'),
            "volume_score": tech_detail.get('volume_score'),
        },
        "valuation_analysis": {
            "score": rating.get('details', {}).get('valuation_score'),
            "pe_percentile": pe_percentile,
            "pb_percentile": pb_percentile,
        },
        "momentum_analysis": rating.get('sub_scores', {}).get('momentum', {}),
        "risk_analysis": {
            "risk_score": risk_detail.get('volatility_score'),
            "annual_volatility": risk_detail.get('annual_volatility'),
            "max_drawdown": risk_detail.get('max_drawdown'),
            "var_annual_pct": risk_detail.get('var_annual_pct'),
        },
        "comprehensive_rating": {
            "rating": rating.get('rating'),
            "composite_score": rating.get('composite_score'),
        },
        "investment_advice": advice,
    }

    return {"report": report}
