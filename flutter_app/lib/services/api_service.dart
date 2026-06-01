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
}
