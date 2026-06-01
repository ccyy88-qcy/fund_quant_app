"""K线形态识别 — 纯pandas向量化实现，15种经典形态"""
import numpy as np
import pandas as pd


def _body(open_, close_):
    """K线实体"""
    return close_ - open_

def _upper_shadow(high, open_, close_):
    """上影线"""
    return high - np.maximum(open_, close_)

def _lower_shadow(low, open_, close_):
    """下影线"""
    return np.minimum(open_, close_) - low

def _is_bullish(open_, close_):
    return close_ > open_

def _is_bearish(open_, close_):
    return close_ < open_

def detect_all(df: pd.DataFrame) -> pd.DataFrame:
    """识别全部15种形态，返回带形态标签的DataFrame"""
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    body = _body(o, c)
    upper = _upper_shadow(h, o, c)
    lower = _lower_shadow(l, o, c)
    total_range = h - l
    avg_body = body.abs().rolling(20).mean()
    avg_range = total_range.rolling(20).mean()

    patterns = pd.DataFrame(index=df.index)

    # 1. 锤子线
    patterns['hammer'] = (
        (total_range > avg_range * 1.5) &
        (lower >= body.abs() * 2) &
        (upper <= body.abs() * 0.3) &
        (_is_bearish(o, c) | (body.abs() < avg_body * 0.3))
    )

    # 2. 上吊线
    patterns['hanging_man'] = (
        (total_range > avg_range * 1.5) &
        (lower >= body.abs() * 2) &
        (upper <= body.abs() * 0.3) &
        (_is_bullish(o, c))
    ) & (df.index > 0)

    # 3. 十字星
    patterns['doji'] = body.abs() <= avg_body * 0.1

    # 4. 长实体
    patterns['long_body'] = body.abs() > avg_body * 1.5

    # 5. 纺锤线
    patterns['spinning_top'] = (
        (body.abs() <= avg_body * 0.8) &
        (upper > avg_body * 0.5) &
        (lower > avg_body * 0.5)
    )

    # 6. 看涨吞没
    c_o_shift = o.shift()
    c_c_shift = c.shift()
    patterns['bullish_engulfing'] = (
        _is_bearish(c_o_shift, c_c_shift) &
        _is_bullish(o, c) &
        (c > c_c_shift) & (o < c_o_shift)
    )

    # 7. 看跌吞没
    patterns['bearish_engulfing'] = (
        _is_bullish(c_o_shift, c_c_shift) &
        _is_bearish(o, c) &
        (c < c_c_shift) & (o > c_o_shift)
    )

    # 8. 看涨刺透
    patterns['piercing'] = (
        _is_bearish(c_o_shift, c_c_shift) &
        _is_bullish(o, c) &
        (c > (c_c_shift + c_o_shift) / 2) &
        (c < c_o_shift) &
        (o < c_c_shift)
    )

    # 9. 看跌乌云盖顶
    patterns['dark_cloud'] = (
        _is_bullish(c_o_shift, c_c_shift) &
        _is_bearish(o, c) &
        (c < (c_c_shift + c_o_shift) / 2) &
        (c > c_c_shift) &
        (o > c_c_shift)
    )

    # 10. 看涨启明星
    patterns['morning_star'] = (
        _is_bearish(c_o_shift.shift(), c_c_shift.shift()) &
        (body.shift().abs() <= avg_body * 0.3) &
        _is_bullish(o, c) &
        (c > (c_c_shift.shift() + c_o_shift.shift()) / 2)
    )

    # 11. 看跌黄昏星
    patterns['evening_star'] = (
        _is_bullish(c_o_shift.shift(), c_c_shift.shift()) &
        (body.shift().abs() <= avg_body * 0.3) &
        _is_bearish(o, c) &
        (c < (c_c_shift.shift() + c_o_shift.shift()) / 2)
    )

    # 12. 三只乌鸦
    patterns['three_black_crows'] = (
        _is_bearish(o, c) &
        _is_bearish(c_o_shift, c_c_shift) &
        _is_bearish(c_o_shift.shift(), c_c_shift.shift()) &
        (c < c_c_shift) &
        (c_c_shift < c_c_shift.shift()) &
        (o < c_o_shift) &
        (c_o_shift < c_o_shift.shift())
    )

    # 13. 红三兵
    patterns['three_white_soldiers'] = (
        _is_bullish(o, c) &
        _is_bullish(c_o_shift, c_c_shift) &
        _is_bullish(c_o_shift.shift(), c_c_shift.shift()) &
        (c > c_c_shift) &
        (c_c_shift > c_c_shift.shift()) &
        (o > c_o_shift) &
        (c_o_shift > c_o_shift.shift())
    )

    # 14. 看涨分离线
    patterns['bullish_separating'] = (
        _is_bearish(c_o_shift, c_c_shift) &
        _is_bullish(o, c) &
        (abs(o - c_c_shift) <= avg_body * 0.1)
    )

    # 15. 看跌分离线
    patterns['bearish_separating'] = (
        _is_bullish(c_o_shift, c_c_shift) &
        _is_bearish(o, c) &
        (abs(o - c_c_shift) <= avg_body * 0.1)
    )

    return patterns


def get_latest_patterns(df: pd.DataFrame) -> list:
    """获取最近5根K线的形态"""
    patterns_df = detect_all(df)
    if len(patterns_df) < 5:
        return []

    result = []
    pattern_names = {
        'hammer': '锤子线', 'hanging_man': '上吊线', 'doji': '十字星',
        'long_body': '长实体', 'spinning_top': '纺锤线',
        'bullish_engulfing': '看涨吞没', 'bearish_engulfing': '看跌吞没',
        'piercing': '看涨刺透', 'dark_cloud': '乌云盖顶',
        'morning_star': '启明星', 'evening_star': '黄昏星',
        'three_black_crows': '三只乌鸦', 'three_white_soldiers': '红三兵',
        'bullish_separating': '看涨分离', 'bearish_separating': '看跌分离',
    }

    for i in range(-5, 0):
        row = patterns_df.iloc[i]
        day = df.iloc[i]['day'] if 'day' in df.columns else str(i)
        active = [(pattern_names[k], k.startswith('bull') or k in ('hammer','piercing','morning_star','three_white_soldiers'))
                  for k in pattern_names if row.get(k, False)]
        if active:
            result.append({'day': day, 'patterns': active})

    return result
