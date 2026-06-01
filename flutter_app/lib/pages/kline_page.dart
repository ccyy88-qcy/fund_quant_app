import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class KlinePage extends StatefulWidget {
  final String? initialCode;
  const KlinePage({super.key, this.initialCode});

  @override
  State<KlinePage> createState() => _KlinePageState();
}

class _KlinePageState extends State<KlinePage> {
  final _api = ApiService();
  final _codeController = TextEditingController();
  List<dynamic> _kline = [];
  Map<String, dynamic>? _indicators;
  bool _loading = false;
  String _period = '1月';
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.initialCode != null && widget.initialCode!.isNotEmpty) {
      _codeController.text = widget.initialCode!;
      _loadKline(widget.initialCode!);
    }
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadKline(String code) async {
    if (code.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _api.getIndicators(code);
      if (!mounted) return;
      setState(() {
        _kline = result['kline'] ?? [];
        _indicators = result['indicators'];
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '数据获取失败: ${e.toString().substring(0, 60)}';
      });
    }
  }

  List<dynamic> _getVisibleKline() {
    if (_kline.isEmpty) return [];
    int days;
    switch (_period) {
      case '1月': days = 22; break;
      case '3月': days = 66; break;
      case '6月': days = 132; break;
      case '1年': days = 250; break;
      default: days = 66;
    }
    return _kline.sublist(_kline.length - days < 0 ? 0 : _kline.length - days);
  }

  List<double>? _getIndicator(String name) {
    if (_indicators == null || !_indicators!.containsKey(name)) return null;
    final vals = _indicators![name] as List;
    final visible = _getVisibleKline().length;
    final start = vals.length - visible;
    if (start < 0) return null;
    return vals.sublist(start).map((v) => v is double ? v : double.nan).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('K线分析')),
      body: Column(
        children: [
          // 输入栏
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _codeController,
                    decoration: const InputDecoration(
                      hintText: '输入基金代码 (如 510300)',
                      prefixIcon: Icon(Icons.code, color: AppTheme.accent),
                    ),
                    textInputAction: TextInputAction.go,
                    onSubmitted: _loadKline,
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  decoration: BoxDecoration(
                    gradient: AppTheme.neonGradient,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.travel_explore, color: Colors.white),
                    onPressed: () => _loadKline(_codeController.text),
                  ),
                ),
              ],
            ),
          ),

          // 周期选择
          if (_kline.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: ['1月', '3月', '6月', '1年'].map((p) {
                  final active = _period == p;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(p),
                      selected: active,
                      selectedColor: AppTheme.primary,
                      backgroundColor: AppTheme.bgCard,
                      labelStyle: TextStyle(
                        color: active ? Colors.white : AppTheme.textSecondary,
                        fontSize: 12,
                      ),
                      onSelected: (_) => setState(() => _period = p),
                    ),
                  );
                }).toList(),
              ),
            ),

          // 图表区域
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
                : _error != null
                    ? Center(child: Text(_error!, style: const TextStyle(color: AppTheme.textSecondary)))
                    : _kline.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.show_chart, size: 64, color: AppTheme.textSecondary.withOpacity(0.3)),
                                const SizedBox(height: 16),
                                const Text('输入基金代码查看K线图和指标', style: TextStyle(color: AppTheme.textSecondary)),
                              ],
                            ),
                          )
                        : SingleChildScrollView(
                            child: Column(
                              children: [
                                _buildCandlestickChart(),
                                const SizedBox(height: 16),
                                _buildIndicatorCards(),
                                const SizedBox(height: 16),
                                _buildKlinePatterns(),
                                const SizedBox(height: 32),
                              ],
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildCandlestickChart() {
    final kline = _getVisibleKline();
    if (kline.isEmpty) return const SizedBox();

    final closes = kline.map((k) => (k['close'] as num).toDouble()).toList();
    final minPrice = closes.reduce((a, b) => a < b ? a : b) * 0.995;
    final maxPrice = closes.reduce((a, b) => a > b ? a : b) * 1.005;

    final ma10 = _getIndicator('ma10');
    final ma60 = _getIndicator('ma60');

    return Container(
      height: 340,
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.fromLTRB(8, 20, 16, 20),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SizedBox(width: 8),
              _buildLegend('K线', AppTheme.textPrimary),
              if (ma10 != null) ...[const SizedBox(width: 12), _buildLegend('MA10', AppTheme.accent)],
              if (ma60 != null) ...[const SizedBox(width: 12), _buildLegend('MA60', AppTheme.yellow)],
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: (maxPrice - minPrice) / 4,
                  getDrawingHorizontalLine: (v) => FlLine(
                    color: Colors.white.withOpacity(0.05),
                    strokeWidth: 0.5,
                  ),
                ),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 56,
                      getTitlesWidget: (v, _) => Text(
                        v.toStringAsFixed(2),
                        style: const TextStyle(color: AppTheme.textSecondary, fontSize: 9),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 28,
                      interval: (kline.length / 5).ceilToDouble(),
                      getTitlesWidget: (v, _) {
                        final idx = v.toInt();
                        if (idx < 0 || idx >= kline.length) return const SizedBox();
                        final day = kline[idx]['day'] ?? '';
                        return Text(
                          day.toString().substring(5),
                          style: const TextStyle(color: AppTheme.textSecondary, fontSize: 9),
                        );
                      },
                    ),
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                minY: minPrice,
                maxY: maxPrice,
                lineBarsData: [
                  if (ma10 != null)
                    _buildLine(ma10, AppTheme.accent),
                  if (ma60 != null)
                    _buildLine(ma60, AppTheme.yellow),
                ],
                lineTouchData: const LineTouchData(enabled: false),
              ),
              duration: const Duration(milliseconds: 300),
            ),
          ),
        ],
      ),
    );
  }

  LineChartBarData _buildLine(List<double> data, Color color) {
    return LineChartBarData(
      spots: List.generate(data.length, (i) => FlSpot(i.toDouble(), data[i])),
      isCurved: false,
      color: color,
      barWidth: 1.2,
      dotData: const FlDotData(show: false),
      preventCurveOverShooting: true,
    );
  }

  Widget _buildLegend(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 10, height: 2, color: color),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
      ],
    );
  }

  Widget _buildIndicatorCards() {
    if (_indicators == null) return const SizedBox();
    final rsi = _getIndicator('rsi14');
    final cci = _getIndicator('cci');

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(child: _buildIndicatorCard('RSI(14)', rsi?.last?.toStringAsFixed(1) ?? '-', _rsiColor(rsi?.last))),
          const SizedBox(width: 12),
          Expanded(child: _buildIndicatorCard('CCI(20)', cci?.last?.toStringAsFixed(0) ?? '-', _cciColor(cci?.last))),
          const SizedBox(width: 12),
          Expanded(child: _buildIndicatorCard('信号', _getLatestSignal(), _getSignalColor())),
        ],
      ),
    );
  }

  Widget _buildIndicatorCard(String title, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3), width: 0.5),
      ),
      child: Column(
        children: [
          Text(title, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
          const SizedBox(height: 6),
          Text(value, style: TextStyle(color: color, fontSize: 18, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Color _rsiColor(double? v) {
    if (v == null || v.isNaN) return AppTheme.textSecondary;
    if (v > 70) return AppTheme.red;
    if (v < 30) return AppTheme.green;
    return AppTheme.yellow;
  }

  Color _cciColor(double? v) {
    if (v == null || v.isNaN) return AppTheme.textSecondary;
    if (v > 100) return AppTheme.red;
    if (v < -100) return AppTheme.green;
    return AppTheme.yellow;
  }

  String _getLatestSignal() {
    final rsi = _getIndicator('rsi14')?.last;
    final cci = _getIndicator('cci')?.last;
    if (rsi == null || rsi.isNaN || cci == null || cci.isNaN) return '-';
    if (rsi > 70 && cci > 100) return '超买';
    if (rsi < 30 && cci < -100) return '超卖';
    return '中性';
  }

  Color _getSignalColor() {
    final s = _getLatestSignal();
    if (s == '超买') return AppTheme.red;
    if (s == '超卖') return AppTheme.green;
    return AppTheme.yellow;
  }

  Widget _buildKlinePatterns() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.bgCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.auto_awesome, color: AppTheme.accent, size: 18),
                SizedBox(width: 8),
                Text('K线形态识别', style: TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 8),
            const Text('(数据在服务端计算, App端展示)', style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
