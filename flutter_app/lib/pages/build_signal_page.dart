import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class BuildSignalPage extends StatefulWidget {
  const BuildSignalPage({super.key});

  @override
  State<BuildSignalPage> createState() => _BuildSignalPageState();
}

class _BuildSignalPageState extends State<BuildSignalPage> {
  final _api = ApiService();
  final _codeController = TextEditingController(text: '562360');
  Map<String, dynamic>? _signal;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSignal();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadSignal() async {
    setState(() {
      _loading = true;
      _error = null;
      _signal = null;
    });
    try {
      final result = await _api.getBuildSignal(_codeController.text.trim());
      if (!mounted) return;
      setState(() {
        _signal = result;
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

  Color _signalColor(String signal) {
    if (signal.contains('强烈建仓')) return AppTheme.green;
    if (signal.contains('建议建仓')) return const Color(0xFF66BB6A);
    if (signal.contains('观望')) return AppTheme.yellow;
    if (signal.contains('注意风险')) return AppTheme.red;
    if (signal.contains('回避')) return const Color(0xFFB71C1C);
    return AppTheme.grey;
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 代码输入
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _codeController,
                  decoration: const InputDecoration(
                    labelText: '基金/ETF代码',
                    prefixIcon: Icon(Icons.search, color: AppTheme.accent),
                  ),
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _loadSignal(),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                decoration: BoxDecoration(
                  gradient: AppTheme.neonGradient,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: IconButton(
                  onPressed: _loadSignal,
                  icon: const Icon(Icons.refresh, color: Colors.white),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(color: AppTheme.primary),
              ),
            )
          else if (_error != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.red.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.red.withOpacity(0.2)),
              ),
              child: Text('加载失败: $_error',
                  style: const TextStyle(color: AppTheme.red)),
            )
          else if (_signal != null) ...[
            // 建仓信号大卡片
            _buildSignalCard(),
            const SizedBox(height: 16),
            // 各维度分数
            _buildScoreCards(),
            const SizedBox(height: 16),
            // 市场情绪详情
            if (_signal!['scores'] != null) _buildDetailSection(),
          ] else
            const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.trending_up, size: 64,
                      color: AppTheme.textSecondary),
                  SizedBox(height: 16),
                  Text('输入基金代码查看建仓信号',
                      style: TextStyle(color: AppTheme.textSecondary)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSignalCard() {
    final s = _signal!;
    final signal = s['build_signal'] ?? '';
    final color = _signalColor(signal);
    final position = s['suggested_position'] ?? '';
    final detail = s['action_detail'] ?? '';
    final score = (s['total_score'] as num?)?.toDouble() ?? 0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.15), color.withOpacity(0.05)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(signal,
              style: TextStyle(
                color: color,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              )),
          const SizedBox(height: 20),
          // 综合评分环形指示
          SizedBox(
            width: 100,
            height: 100,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 100,
                  height: 100,
                  child: CircularProgressIndicator(
                    value: score / 100,
                    strokeWidth: 8,
                    backgroundColor: color.withOpacity(0.2),
                    valueColor: AlwaysStoppedAnimation<Color>(color),
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('${score.toStringAsFixed(0)}',
                        style: TextStyle(
                          color: color,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        )),
                    const Text('分', style: TextStyle(
                        color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text('建议仓位: $position',
                style: TextStyle(
                    color: color,
                    fontSize: 16,
                    fontWeight: FontWeight.w600)),
          ),
          const SizedBox(height: 12),
          Text(detail,
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 14)),
          const SizedBox(height: 8),
          Text(s['timestamp'] ?? '',
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildScoreCards() {
    final scores = _signal!['scores'] as Map<String, dynamic>? ?? {};
    final weights = _signal!['weights'] as Map<String, dynamic>? ?? {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('各维度评分',
            style: TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 12),
        ...scores.entries.map((e) {
          final v = (e.value as num?)?.toDouble() ?? 0;
          final w = weights[e.key] != null
              ? ((weights[e.key] as num) * 100).toStringAsFixed(0)
              : '';
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.bgCard,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(_labelFor(e.key),
                          style: const TextStyle(
                              color: AppTheme.textSecondary, fontSize: 13)),
                      if (w.isNotEmpty)
                        Text(' ($w%)',
                            style: const TextStyle(
                                color: AppTheme.textSecondary, fontSize: 11)),
                      const Spacer(),
                      Text('${v.toStringAsFixed(0)}分',
                          style: TextStyle(
                            color: v >= 70
                                ? AppTheme.green
                                : (v >= 45 ? AppTheme.yellow : AppTheme.red),
                            fontWeight: FontWeight.w600,
                          )),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: v / 100,
                      backgroundColor: AppTheme.bgCardAlt,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        v >= 70
                            ? AppTheme.green
                            : (v >= 45 ? AppTheme.yellow : AppTheme.red),
                      ),
                      minHeight: 4,
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
      ],
    );
  }

  String _labelFor(String key) {
    switch (key) {
      case 'valuation_score': return '估值吸引力';
      case 'technical_score': return '技术面趋势';
      case 'sentiment_score': return '市场情绪';
      default: return key;
    }
  }

  Widget _buildDetailSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('评分权重配置',
              style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ...(_signal!['weights'] as Map<String, dynamic>? ?? {}).entries
              .map((e) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      children: [
                        Text(_labelFor(e.key),
                            style: const TextStyle(
                                color: AppTheme.textSecondary, fontSize: 12)),
                        const Spacer(),
                        Text(
                            '${((e.value as num) * 100).toStringAsFixed(0)}%',
                            style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontWeight: FontWeight.w500)),
                      ],
                    ),
                  )),
        ],
      ),
    );
  }
}
