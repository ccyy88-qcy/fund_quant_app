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
    final ma5 = _getIndicator('ma5');
    final ma10 = _getIndicator('ma10');
    final ma20 = _getIndicator('ma20');

    // 价格范围
    double minP = double.infinity, maxP = double.negativeInfinity;
    for (final k in kline) {
      final h = (k['high'] as num).toDouble();
      final l = (k['low'] as num).toDouble();
      if (h > maxP) maxP = h;
      if (l < minP) minP = l;
    }
    for (final list in [ma5, ma10, ma20]) {
      if (list == null) continue;
      for (final v in list) {
        if (v > maxP) maxP = v;
        if (v < minP) minP = v;
      }
    }
    final pad = (maxP - minP) * 0.08;
    minP -= pad;
    maxP += pad;
    if (minP >= maxP) { minP = minP * 0.95; maxP = maxP * 1.05; }

    return Container(
      height: 360,
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.fromLTRB(8, 20, 16, 20),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
      ),
      child: Column(
        children: [
          Row(
            children: [
              const SizedBox(width: 8),
              _buildLegend('K线', AppTheme.textPrimary),
              if (ma5 != null) ...[const SizedBox(width: 12), _buildLegend('MA5', const Color(0xFFFFD740))],
              if (ma10 != null) ...[const SizedBox(width: 12), _buildLegend('MA10', AppTheme.accent)],
              if (ma20 != null) ...[const SizedBox(width: 12), _buildLegend('MA20', const Color(0xFFFF7043))],
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: LayoutBuilder(
              builder: (_, constraints) => CustomPaint(
                size: Size(constraints.maxWidth, constraints.maxHeight),
                painter: _CandlestickPainter(
                  kline: kline,
                  ma5: ma5,
                  ma10: ma10,
                  ma20: ma20,
                  minPrice: minP,
                  maxPrice: maxP,
                ),
              ),
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

/// 蜡烛图绘制器
class _CandlestickPainter extends CustomPainter {
  final List<dynamic> kline;
  final List<double>? ma5;
  final List<double>? ma10;
  final List<double>? ma20;
  final double minPrice;
  final double maxPrice;

  _CandlestickPainter({
    required this.kline,
    this.ma5,
    this.ma10,
    this.ma20,
    required this.minPrice,
    required this.maxPrice,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final chartW = size.width - 50;
    final chartH = size.height - 30;
    final n = kline.length;
    if (n == 0) return;
    final candleW = chartW / n;

    // 检测是否为NAV数据（OHLC全相同）
    bool isNav = false;
    if (n > 2) {
      int sameCount = 0;
      for (int i = 0; i < n && i < 10; i++) {
        final k = kline[i];
        if ((k['open'] as num) == (k['close'] as num) &&
            (k['high'] as num) == (k['low'] as num)) {
          sameCount++;
        }
      }
      isNav = sameCount == (n < 10 ? n : 10);
    }

    final gap = candleW * 0.25;
    final bodyW = candleW - gap * 2;
    final minBodyW = 1.0;
    final drawBodyW = bodyW < minBodyW ? minBodyW : bodyW;
    final drawGap = (candleW - drawBodyW) / 2;

    final range = maxPrice - minPrice;

    double yPos(double v) => chartH - (v - minPrice) / range * chartH;

    // ── 网格线 ──
    final gridPaint = Paint()
      ..color = Colors.white.withOpacity(0.05)
      ..strokeWidth = 0.5;
    for (int i = 0; i <= 4; i++) {
      final y = chartH / 4 * i;
      canvas.drawLine(Offset(50, y), Offset(size.width, y), gridPaint);
    }

    // ── Y轴价格 ──
    final labelStyle = TextStyle(color: const Color(0xFF9898B0), fontSize: 9);
    for (int i = 0; i <= 4; i++) {
      final price = minPrice + range * (1 - i / 4);
      final tp = TextPainter(
        text: TextSpan(text: price.toStringAsFixed(2), style: labelStyle),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(50 - tp.width - 4, chartH / 4 * i - tp.height / 2));
    }

    // ── X轴日期 ──
    final dateInterval = (n / 5).ceil();
    final dateStyle = TextStyle(color: const Color(0xFF9898B0), fontSize: 8);
    for (int i = 0; i < n; i += dateInterval) {
      final day = kline[i]['day']?.toString() ?? '';
      if (day.length >= 10) {
        final tp = TextPainter(
          text: TextSpan(text: day.substring(5), style: dateStyle),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas, Offset(50 + i * candleW + (candleW - tp.width) / 2, chartH + 8));
      }
    }

    // ── NAV模式：折线图（无OHLC的基金净值）──
    if (isNav) {
      final linePaint = Paint()
        ..color = const Color(0xFF00D4FF)
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke;
      final linePath = Path();
      bool started = false;
      for (int i = 0; i < n; i++) {
        final close = (kline[i]['close'] as num).toDouble();
        final x = 50 + i * candleW + candleW / 2;
        final y = chartH - (close - minPrice) / range * chartH;
        if (!started) {
          linePath.moveTo(x, y);
          started = true;
        } else {
          linePath.lineTo(x, y);
        }
      }
      if (started) canvas.drawPath(linePath, linePaint);

      // 标注"净值"标签
      final navTp = TextPainter(
        text: TextSpan(text: '净值', style: TextStyle(color: const Color(0xFF00D4FF), fontSize: 9)),
        textDirection: TextDirection.ltr,
      )..layout();
      navTp.paint(canvas, Offset(54, 4));
    }

    // ── 蜡烛线 ──
    if (!isNav) {
    for (int i = 0; i < n; i++) {
      final k = kline[i];
      final open = (k['open'] as num).toDouble();
      final close = (k['close'] as num).toDouble();
      final high = (k['high'] as num).toDouble();
      final low = (k['low'] as num).toDouble();
      final x = 50 + i * candleW + drawGap;
      final isUp = close >= open;

      final bodyColor = isUp ? const Color(0xFFF44336) : const Color(0xFF4CAF50);
      final bodyTop = yPos(isUp ? close : open);
      final bodyBottom = yPos(isUp ? open : close);
      final bodyH = bodyBottom - bodyTop;

      // 影线
      final wickPaint = Paint()
        ..color = bodyColor
        ..strokeWidth = 1;
      canvas.drawLine(Offset(x + drawBodyW / 2, yPos(high)), Offset(x + drawBodyW / 2, yPos(low)), wickPaint);

      // 实体
      if (bodyH < 1) {
        canvas.drawLine(Offset(x, bodyTop), Offset(x + drawBodyW, bodyTop), wickPaint);
      } else {
        canvas.drawRect(
          Rect.fromLTRB(x, bodyTop, x + drawBodyW, bodyBottom),
          Paint()..color = bodyColor,
        );
      }
    }
    }

    // ── MA线 ──
    _drawMALine(canvas, chartW, chartH, candleW, ma5, const Color(0xFFFFD740));
    _drawMALine(canvas, chartW, chartH, candleW, ma10, const Color(0xFF00D4FF));
    _drawMALine(canvas, chartW, chartH, candleW, ma20, const Color(0xFFFF7043));
  }

  void _drawMALine(Canvas canvas, double chartW, double chartH, double candleW,
                   List<double>? data, Color color) {
    if (data == null || data.length < 2) return;
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;
    final offset = kline.length - data.length;
    final path = Path();
    bool started = false;
    for (int i = 0; i < data.length; i++) {
      final v = data[i];
      if (v.isNaN || v.isInfinite) continue;
      final x = 50 + (offset + i) * candleW + candleW / 2;
      final y = chartH - (v - minPrice) / (maxPrice - minPrice) * chartH;
      if (!started) {
        path.moveTo(x, y);
        started = true;
      } else {
        path.lineTo(x, y);
      }
    }
    if (started) canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _CandlestickPainter old) =>
      kline != old.kline || minPrice != old.minPrice || maxPrice != old.maxPrice;
}
