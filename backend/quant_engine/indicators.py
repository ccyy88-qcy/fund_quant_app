"""技术指标计算模块 — 纯pandas向量化实现"""
import numpy as np
import pandas as pd

def calc_ma(series: pd.Series, period: int) -> pd.Series:
    """移动平均线"""
    return series.rolling(window=period).mean()

def calc_ema(series: pd.Series, period: int) -> pd.Series:
    """指数移动平均"""
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI相对强弱指标"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_macd(series: pd.Series) -> tuple:
    """MACD指标"""
    ema12 = calc_ema(series, 12)
    ema26 = calc_ema(series, 26)
    dif = ema12 - ema26
    dea = calc_ema(dif, 9)
    macd = 2 * (dif - dea)
    return dif, dea, macd

def calc_bollinger(series: pd.Series, period: int = 20, std: int = 2) -> tuple:
    """布林带"""
    ma = calc_ma(series, period)
    sd = series.rolling(window=period).std()
    upper = ma + std * sd
    lower = ma - std * sd
    return upper, ma, lower

def calc_cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """CCI商品通道指标"""
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
    cci = (tp - sma) / (0.015 * mad.replace(0, np.nan))
    return cci

def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX平均趋向指数"""
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=df.index)

    plus_di = 100 * plus_dm.rolling(window=period).mean() / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(window=period).mean() / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(window=period).mean()
    return adx

def calc_obv(df: pd.DataFrame) -> pd.Series:
    """OBV能量潮"""
    obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    return obv

def calc_all_indicators(df: pd.DataFrame) -> dict:
    """计算全部技术指标，返回dict"""
    close = df['close']
    return {
        'ma5': calc_ma(close, 5).tolist(),
        'ma10': calc_ma(close, 10).tolist(),
        'ma20': calc_ma(close, 20).tolist(),
        'ma60': calc_ma(close, 60).tolist(),
        'rsi14': calc_rsi(close, 14).tolist(),
        'macd_dif': calc_macd(close)[0].tolist(),
        'macd_dea': calc_macd(close)[1].tolist(),
        'macd_bar': calc_macd(close)[2].tolist(),
        'boll_upper': calc_bollinger(close)[0].tolist(),
        'boll_mid': calc_bollinger(close)[1].tolist(),
        'boll_lower': calc_bollinger(close)[2].tolist(),
        'cci': calc_cci(df, 20).tolist(),
        'adx': calc_adx(df, 14).tolist(),
        'obv': calc_obv(df).tolist(),
    }

def get_latest_kline_patterns(kline_data: list) -> list:
    """获取最近K线形态"""
    if not kline_data or len(kline_data) < 10:
        return []
    from . import candlestick_patterns as cp
    df = pd.DataFrame(kline_data)
    return cp.get_latest_patterns(df)
