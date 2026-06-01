"""量化引擎 — 所有模块导出"""
from .indicators import (
    calc_ma, calc_ema, calc_rsi, calc_macd,
    calc_bollinger, calc_cci, calc_adx, calc_obv,
    calc_all_indicators, get_latest_kline_patterns,
)
from .risk_metrics import (
    annual_return, max_drawdown, current_drawdown,
    annual_volatility, sharpe_ratio, win_rate,
    profit_loss_ratio, calc_risk_metrics,
)
from .signals import calc_signal_v4, run_backtest
from .candlestick_patterns import detect_all, get_latest_patterns
from .data_fetcher import (
    search_funds, get_fund_info, get_kline,
    get_realtime_estimation, get_market_index, get_sector_performance,
)
from .sector_rotation import (
    macro_cycle_position, sector_score, rotation_signal,
    rotation_backtest, capital_flow_analysis,
)
from .factor_model import (
    calc_factor_returns, factor_ic_analysis,
    factor_layer_backtest, factor_correlation_matrix,
    composite_factor, batch_layer_backtest, full_factor_analysis,
)
from .volatility_strategy import (
    calc_hv, calc_hv_percentile, calc_vol_mean_reversion_signal,
    calc_volatility_cone, backtest_vol_signal,
)
from .portfolio_optimizer import (
    efficient_frontier, min_variance_portfolio,
    max_sharpe_portfolio, risk_parity_portfolio,
    portfolio_stats,
)
from .custom_backtest import (
    run_custom_strategy, optimize_params,
    describe_strategy, brinson_attribution, multi_asset_backtest,
)
