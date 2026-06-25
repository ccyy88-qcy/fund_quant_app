import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:dio/dio.dart';
import '../theme/app_theme.dart';

class FundDetailPage extends StatefulWidget {
  final String code;
  final String name;

  const FundDetailPage({super.key, required this.code, required this.name});

  @override
  State<FundDetailPage> createState() => _FundDetailPageState();
}

class _FundDetailPageState extends State<FundDetailPage> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _fundInfo;
  List<Map<String, dynamic>> _navHistory = [];

  final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    headers: {
      'User-Agent': 'Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36',
      'Referer': 'https://quote.eastmoney.com/',
    },
  ));

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // 并行拉取基金信息和净值
      final results = await Future.wait([
        _fetchFundInfo(),
        _fetchNavHistory(),
      ]);
      if (!mounted) return;
      setState(() {
        _fundInfo = results[0] as Map<String, dynamic>?;
        _navHistory = results[1] as List<Map<String, dynamic>>;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<Map<String, dynamic>?> _fetchFundInfo() async {
    try {
      // 东方财富基金基本信息
      final url = 'https://fund.eastmoney.com/pingzhongdata/${widget.code}.js';
      final resp = await _dio.get(url);
      // 返回的是 JS 变量，需要解析
      final text = resp.data as String;
      
      // 提取关键信息
      final info = <String, dynamic>{'code': widget.code, 'name': widget.name};
      
      // 提取基金名称
      final nameMatch = RegExp(r'var fS_name = "(.+?)"').firstMatch(text);
      if (nameMatch != null) {
        info['full_name'] = nameMatch.group(1);
      }
      
      // 提取基金代码
      final codeMatch = RegExp(r'var fS_code = "(.+?)"').firstMatch(text);
      if (codeMatch != null) {
        info['fund_code'] = codeMatch.group(1);
      }

      return info;
    } catch (_) {
      return {'code': widget.code, 'name': widget.name};
    }
  }

  Future<List<Map<String, dynamic>>> _fetchNavHistory() async {
    try {
      // 东方财富基金净值历史
      final now = DateTime.now();
      final endDate = '${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}';
      final startDate = '${now.year - 1}0101';

      final url = 'https://api.fund.eastmoney.com/f10/lsjz';
      final params = {
        'fundCode': widget.code,
        'pageIndex': '1',
        'pageSize': '120',
        'startDate': startDate,
        'endDate': endDate,
      };
      final headers = {
        'Referer': 'https://fundf10.eastmoney.com/',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36',
      };

      final resp = await _dio.get(url, queryParameters: params, options: Options(headers: headers));
      final data = resp.data;

      if (data == null || data['Data'] == null || data['Data']['LSJZList'] == null) {
        return [];
      }

      final list = data['Data']['LSJZList'] as List;
      List<Map<String, dynamic>> result = [];
      for (var item in list) {
        result.add({
          'date': item['FSRQ'] ?? '',
          'nav': double.tryParse(item['DWJZ']?.toString() ?? '0') ?? 0,
          'nav_acc': double.tryParse(item['LJJZ']?.toString() ?? '0') ?? 0,
          'daily_chg': double.tryParse(item['JZZZL']?.toString() ?? '0') ?? 0,
        });
      }
      return result.reversed.toList();
    } catch (_) {
      return [];
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.name),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primary),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: AppTheme.red),
            const SizedBox(height: 12),
            Text('加载失败', style: TextStyle(color: AppTheme.textSecondary)),
            const SizedBox(height: 8),
            Text(_error!, style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadData, child: const Text('重试')),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 基金基本信息
          _buildInfoCard(),
          const SizedBox(height: 16),
          // 净值走势图
          _buildNavChart(),
          const SizedBox(height: 16),
          // 近期净值列表
          _buildNavList(),
        ],
      ),
    );
  }

  Widget _buildInfoCard() {
    final info = _fundInfo ?? {};
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            info['full_name'] ?? widget.name,
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text(
                '代码: ${info['fund_code'] ?? widget.code}',
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
              ),
              const Spacer(),
              if (_navHistory.isNotEmpty)
                Text(
                  '最新净值: ${_navHistory.last['nav']}',
                  style: TextStyle(
                    color: AppTheme.accent,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
            ],
          ),
          if (_navHistory.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Text(
                  '日涨跌: ${(_navHistory.last['daily_chg'] as double) >= 0 ? '+' : ''}${_navHistory.last['daily_chg']}%',
                  style: TextStyle(
                    color: (_navHistory.last['daily_chg'] as double) >= 0 ? AppTheme.green : AppTheme.red,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const Spacer(),
                Text(
                  '近一年涨跌: ${_calcYearChg()}%',
                  style: TextStyle(
                    color: _calcYearChg() >= 0 ? AppTheme.green : AppTheme.red,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  double _calcYearChg() {
    if (_navHistory.length < 2) return 0;
    final first = _navHistory.first['nav'] as double;
    final last = _navHistory.last['nav'] as double;
    if (first <= 0) return 0;
    return double.parse(((last / first) - 1) * 100).toStringAsFixed(2));
  }

  Widget _buildNavChart() {
    if (_navHistory.isEmpty) {
      return Container(
        height: 200,
        decoration: BoxDecoration(
          color: AppTheme.bgCard,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Center(
          child: Text('暂无净值数据', style: TextStyle(color: AppTheme.textSecondary)),
        ),
      );
    }

    return Container(
      height: 220,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('近一年净值走势', style: TextStyle(color: AppTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          Expanded(
            child: LineChart(
              LineChartData(
                gridData: FlGridData(show: false),
                titlesData: FlTitlesData(show: false),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: _navHistory.asMap().entries.map((e) {
                      return FlSpot(e.key.toDouble(), e.value['nav'] as double);
                    }).toList(),
                    isCurved: true,
                    color: AppTheme.accent,
                    barWidth: 2,
                    dotData: FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      color: AppTheme.accent.withOpacity(0.1),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNavList() {
    if (_navHistory.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('近期净值', style: TextStyle(color: AppTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          ..._navHistory.reversed.take(10).map((item) {
            final chg = item['daily_chg'] as double;
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  Text(
                    item['date'],
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                  ),
                  const SizedBox(width: 16),
                  Text(
                    item['nav'].toString(),
                    style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
                  ),
                  const Spacer(),
                  Text(
                    '${chg >= 0 ? '+' : ''}${chg.toStringAsFixed(2)}%',
                    style: TextStyle(
                      color: chg >= 0 ? AppTheme.green : AppTheme.red,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
