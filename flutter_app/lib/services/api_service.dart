import 'package:dio/dio.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  // 默认地址，用户可在设置中修改
  String baseUrl = 'http://192.168.1.100:8000';
  late Dio _dio;

  void init() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));
  }

  void updateBaseUrl(String url) {
    baseUrl = url;
    _dio.options.baseUrl = url;
  }

  // ─── 基金搜索 ───
  Future<List<dynamic>> searchFunds(String keyword, {int limit = 20}) async {
    final res = await _dio.get('/api/funds/search',
        queryParameters: {'keyword': keyword, 'limit': limit});
    return res.data['data'] ?? [];
  }

  // ─── 基金信息 ───
  Future<Map<String, dynamic>> getFundInfo(String code) async {
    final res = await _dio.get('/api/funds/$code/info');
    return res.data['data'] ?? {};
  }

  // ─── K线数据 ───
  Future<List<dynamic>> getKline(String code, {int days = 500}) async {
    final res = await _dio.get('/api/funds/$code/kline',
        queryParameters: {'days': days});
    return res.data['data'] ?? [];
  }

  // ─── 技术指标 ───
  Future<Map<String, dynamic>> getIndicators(String code, {int days = 500}) async {
    final res = await _dio.get('/api/funds/$code/indicators',
        queryParameters: {'days': days});
    return res.data['data'] ?? {};
  }

  // ─── 信号判定 ───
  Future<Map<String, dynamic>> getSignal(String code,
      {double? pePct, double? pbPct}) async {
    final params = <String, dynamic>{};
    if (pePct != null) params['pe_pct'] = pePct;
    if (pbPct != null) params['pb_pct'] = pbPct;
    final res = await _dio.get('/api/funds/$code/signal',
        queryParameters: params);
    return res.data['data'] ?? {};
  }

  // ─── 回测 ───
  Future<Map<String, dynamic>> getBacktest(String code) async {
    final res = await _dio.get('/api/funds/$code/backtest');
    return res.data['data'] ?? {};
  }

  // ─── 市场概览 ───
  Future<Map<String, dynamic>> getMarketOverview() async {
    final res = await _dio.get('/api/market/overview');
    return res.data['data'] ?? {};
  }

  // ─── 指数行情 ───
  Future<List<dynamic>> getIndex() async {
    final res = await _dio.get('/api/market/index');
    return res.data['data'] ?? [];
  }

  // ─── 行业涨跌 ───
  Future<List<dynamic>> getSectors() async {
    final res = await _dio.get('/api/market/sectors');
    return res.data['data'] ?? [];
  }

  // ─── 自选列表 ───
  Future<List<dynamic>> getWatchlist() async {
    final res = await _dio.get('/api/funds/watchlist');
    return res.data['data'] ?? [];
  }

  Future<void> setWatchlist(List<String> codes) async {
    await _dio.post('/api/funds/watchlist', data: codes);
  }

  Future<List<dynamic>> getWatchlistRealtime() async {
    final res = await _dio.get('/api/funds/watchlist/realtime');
    return res.data['data'] ?? [];
  }

  // ═══════════════════════════════════════
  // 多因子选股
  // ═══════════════════════════════════════

  /// 因子分析
  Future<Map<String, dynamic>> getFactorAnalysis() async {
    final res = await _dio.get('/api/factors/analysis');
    return res.data['data'] ?? {};
  }

  /// IC历史序列
  Future<Map<String, dynamic>> getIcHistory() async {
    final res = await _dio.get('/api/factors/ic-history');
    return res.data['data'] ?? {};
  }

  /// 分层回测
  Future<Map<String, dynamic>> getLayerBacktest(
      String factorName, int layers) async {
    final res = await _dio.get('/api/factors/layer-backtest',
        queryParameters: {'factor_name': factorName, 'layers': layers});
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // 行业轮动
  // ═══════════════════════════════════════

  /// 宏观周期
  Future<Map<String, dynamic>> getMacroCycle() async {
    final res = await _dio.get('/api/rotation/macro-cycle');
    return res.data['data'] ?? {};
  }

  /// 行业评分
  Future<List<dynamic>> getSectorScores() async {
    final res = await _dio.get('/api/rotation/sector-scores');
    return res.data['data'] ?? [];
  }

  /// 轮动信号
  Future<List<dynamic>> getRotationSignals({int topN = 10}) async {
    final res = await _dio.get('/api/rotation/rotation-signals',
        queryParameters: {'top_n': topN});
    return res.data['data'] ?? [];
  }

  /// 轮动回测
  Future<Map<String, dynamic>> getRotationBacktest() async {
    final res = await _dio.get('/api/rotation/rotation-backtest');
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // 资产配置
  // ═══════════════════════════════════════

  /// 有效前沿
  Future<Map<String, dynamic>> getEfficientFrontier({int nAssets = 5}) async {
    final res = await _dio.get('/api/portfolio/efficient-frontier',
        queryParameters: {'n_assets': nAssets});
    return res.data['data'] ?? {};
  }

  /// 优化组合
  Future<Map<String, dynamic>> optimizePortfolio(
      {String objective = 'sharpe', int nAssets = 5}) async {
    final res = await _dio.get('/api/portfolio/optimize', queryParameters: {
      'objective': objective,
      'n_assets': nAssets,
    });
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // 策略回测
  // ═══════════════════════════════════════

  /// 自定义策略回测
  Future<Map<String, dynamic>> customBacktest(
      String code, String strategy, Map<String, dynamic> params) async {
    final res = await _dio.get('/api/strategy/backtest', queryParameters: {
      'code': code,
      'strategy': strategy,
      'params': params.toString(),
    });
    return res.data['data'] ?? {};
  }

  /// 策略参数优化
  Future<Map<String, dynamic>> optimizeStrategy(
      String code, String strategy, String objective) async {
    final res = await _dio.get('/api/strategy/optimize', queryParameters: {
      'code': code,
      'strategy': strategy,
      'objective': objective,
    });
    return res.data['data'] ?? {};
  }

  /// 策略对比
  Future<Map<String, dynamic>> strategyComparison(String code) async {
    final res = await _dio.get('/api/strategy/comparison',
        queryParameters: {'code': code});
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // 风险分析
  // ═══════════════════════════════════════

  /// 风险分析总览
  Future<Map<String, dynamic>> getRiskAnalysis(String code) async {
    final res = await _dio.get('/api/risk/analysis',
        queryParameters: {'code': code});
    return res.data['data'] ?? {};
  }

  /// VaR分析
  Future<Map<String, dynamic>> getVarAnalysis(
      String code, double confidence) async {
    final res = await _dio.get('/api/risk/var', queryParameters: {
      'code': code,
      'confidence': confidence,
    });
    return res.data['data'] ?? {};
  }

  /// 压力测试
  Future<Map<String, dynamic>> getStressTest(String code) async {
    final res = await _dio.get('/api/risk/stress-test',
        queryParameters: {'code': code});
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // AI智能分析
  // ═══════════════════════════════════════

  /// 一键分析报告
  Future<Map<String, dynamic>> getAnalysisReport(String code,
      {double? pePct, double? pbPct}) async {
    final params = <String, dynamic>{'code': code};
    if (pePct != null) params['pe_pct'] = pePct;
    if (pbPct != null) params['pb_pct'] = pbPct;
    final res = await _dio.get('/api/analysis/report',
        queryParameters: params);
    return res.data['data'] ?? {};
  }

  /// 投资建议
  Future<Map<String, dynamic>> getInvestmentAdvice(String code,
      {double? pePct, double? pbPct}) async {
    final params = <String, dynamic>{'code': code};
    if (pePct != null) params['pe_pct'] = pePct;
    if (pbPct != null) params['pb_pct'] = pbPct;
    final res = await _dio.get('/api/analysis/advice',
        queryParameters: params);
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // 智能定投
  // ═══════════════════════════════════════

  /// 定投回测
  Future<Map<String, dynamic>> dcaBacktest(
      String code, String strategy, double amount, int frequency,
      {int years = 3}) async {
    final res = await _dio.get('/api/dca/backtest', queryParameters: {
      'code': code,
      'strategy': strategy,
      'amount': amount,
      'frequency': frequency,
      'years': years,
    });
    return res.data['data'] ?? {};
  }

  /// 定投策略对比
  Future<Map<String, dynamic>> compareDcaStrategies(
      String code, double amount, int frequency,
      {int years = 3}) async {
    final res = await _dio.get('/api/dca/compare', queryParameters: {
      'code': code,
      'amount': amount,
      'frequency': frequency,
      'years': years,
    });
    return res.data['data'] ?? {};
  }

  // ═══════════════════════════════════════
  // 市场情绪 & 建仓提醒
  // ═══════════════════════════════════════

  /// 市场情绪
  Future<Map<String, dynamic>> getMarketSentiment() async {
    final res = await _dio.get('/api/sentiment/');
    return res.data['data'] ?? {};
  }

  /// 建仓信号
  Future<Map<String, dynamic>> getBuildSignal(String code,
      {double? pePct, double? pbPct}) async {
    final params = <String, dynamic>{'code': code};
    if (pePct != null) params['pe_pct'] = pePct;
    if (pbPct != null) params['pb_pct'] = pbPct;
    final res = await _dio.get('/api/sentiment/build-signal',
        queryParameters: params);
    return res.data['data'] ?? {};
  }

  /// 基金排名
  Future<List<dynamic>> getFundRanks() async {
    final res = await _dio.get('/api/sentiment/fund-ranks');
    return res.data['data'] ?? [];
  }

  // ═══════════════════════════════════════
  // 系统管理
  // ═══════════════════════════════════════

  /// 系统状态
  Future<Map<String, dynamic>> getSystemStatus() async {
    final res = await _dio.get('/api/system/status');
    return res.data['data'] ?? {};
  }

  /// 重启后端
  Future<Map<String, dynamic>> restartBackend() async {
    final res = await _dio.post('/api/system/restart');
    return res.data['data'] ?? {};
  }
}
