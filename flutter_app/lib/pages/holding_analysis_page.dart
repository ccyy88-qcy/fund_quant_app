import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class HoldingAnalysisPage extends StatefulWidget {
  const HoldingAnalysisPage({super.key});

  @override
  State<HoldingAnalysisPage> createState() => _HoldingAnalysisPageState();
}

class _HoldingAnalysisPageState extends State<HoldingAnalysisPage> {
  final _api = ApiService();
  final _codeController = TextEditingController(text: '562360');
  Map<String, dynamic>? _data;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _data = null;
    });
    try {
      final result = await _api.getHoldingAnalysis(_codeController.text.trim());
      if (!mounted) return;
      setState(() {
        _data = result;
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

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 搜索
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
                  onSubmitted: (_) => _load(),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                decoration: BoxDecoration(
                  gradient: AppTheme.neonGradient,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: IconButton(
                  onPressed: _load,
                  icon: const Icon(Icons.timeline, color: Colors.white),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

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
              ),
              child: Text('$_error',
                  style: const TextStyle(color: AppTheme.red)),
            )
          else if (_data != null) ...[
            _buildRecommendationBanner(),
            const SizedBox(height: 16),
            _buildSummaryCard(),
            const SizedBox(height: 16),
            _buildPeriodTable(),
            if (_data!['recommendation'] != null) ...[
              const SizedBox(height: 16),
              _buildStrategyCompareCard(),
            ],
          ] else
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.timeline, size: 64,
                      color: AppTheme.accent.withOpacity(0.4)),
                  const SizedBox(height: 16),
                  const Text('输入基金代码查看持有期收益分析',
                      style: TextStyle(color: AppTheme.textSecondary)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildRecommendationBanner() {
    final rec = _data!['recommendation'] as Map<String, dynamic>? ?? {};
    final adv = rec['advice'] ?? '';
    final period = rec['optimal_holding'] ?? '';
    final wr = rec['optimal_win_rate'] ?? 0;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.accent.withOpacity(0.12),
            AppTheme.primary.withOpacity(0.08),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.accent.withOpacity(0.25)),
      ),
      child: Column(
        children: [
          const Icon(Icons.emoji_events, color: AppTheme.accent, size: 32),
          const SizedBox(height: 8),
          Text('建议持有 $period',
              style: const TextStyle(
                  color: AppTheme.accent,
                  fontSize: 22,
                  fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            decoration: BoxDecoration(
              color: (wr >= 65 ? AppTheme.green : AppTheme.yellow)
                  .withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '历史胜率 ${(wr as num).toStringAsFixed(0)}%',
              style: TextStyle(
                color: wr >= 65 ? AppTheme.green : AppTheme.yellow,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text('$adv',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildSummaryCard() {
    final sum = _data!['summary'] as Map<String, dynamic>? ?? {};
    final price = sum['current_price'] ?? '';
    final days = sum['total_history_days'] ?? '';
    final bh = _data!['buy_hold_return'];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          _summaryItem('最新价', price.toString(), AppTheme.accent),
          Container(
              width: 1,
              height: 40,
              color: AppTheme.textSecondary.withOpacity(0.2)),
          _summaryItem('历史天数', '$days', AppTheme.textPrimary),
          Container(
              width: 1,
              height: 40,
              color: AppTheme.textSecondary.withOpacity(0.2)),
          _summaryItem(
            '买入持有',
            '${bh ?? 0}%',
            (bh as num?)?.toDouble() >= 0 ? AppTheme.green : AppTheme.red,
          ),
        ],
      ),
    );
  }

  Widget _summaryItem(String label, String value, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(value,
              style: TextStyle(
                  color: color,
                  fontSize: 18,
                  fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(label,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildPeriodTable() {
    final periods =
        _data!['periods_analysis'] as List<dynamic>? ?? [];
    if (periods.isEmpty) return const SizedBox();

    final bestPeriod = _data!['best_period'];
    final bestName = bestPeriod != null
        ? (bestPeriod as Map<String, dynamic>)['period']
        : '';

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            child: const Text('各持有期收益统计',
                style: TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600)),
          ),
          const Divider(height: 1, color: Color(0x1A9898B0)),
          ...periods.map((p) {
            final pm = p as Map<String, dynamic>;
            final isBest = pm['period'] == bestName;
            final wr = (pm['win_rate'] as num?)?.toDouble() ?? 0;
            final ar = (pm['avg_return'] as num?)?.toDouble() ?? 0;

            return Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isBest
                    ? AppTheme.accent.withOpacity(0.06)
                    : Colors.transparent,
                border: isBest
                    ? Border.all(
                        color: AppTheme.accent.withOpacity(0.2))
                    : null,
              ),
              child: Row(
                children: [
                  Container(
                    width: 50,
                    padding:
                        const EdgeInsets.symmetric(vertical: 4),
                    decoration: BoxDecoration(
                      color: isBest
                          ? AppTheme.accent.withOpacity(0.12)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      pm['period'] ?? '',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: isBest
                            ? AppTheme.accent
                            : AppTheme.textPrimary,
                        fontWeight: isBest
                            ? FontWeight.bold
                            : FontWeight.normal,
                        fontSize: 13,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(2),
                          child: LinearProgressIndicator(
                            value: wr / 100,
                            backgroundColor:
                                AppTheme.bgCardAlt,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(
                              wr >= 65
                                  ? AppTheme.green
                                  : (wr >= 50
                                      ? AppTheme.yellow
                                      : AppTheme.red),
                            ),
                            minHeight: 4,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text('胜率${wr.toStringAsFixed(0)}%',
                            style: const TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 11)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    '${ar >= 0 ? '+' : ''}${ar.toStringAsFixed(1)}%',
                    style: TextStyle(
                      color: ar >= 0 ? AppTheme.green : AppTheme.red,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
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

  Widget _buildStrategyCompareCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('策略对比',
              style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          _buildStrategyRow('买入持有', '${_data!['buy_hold_return'] ?? 0}%',
              (_data!['buy_hold_return'] as num?)?.toDouble() ?? 0),
          const Divider(height: 16, color: Color(0x1A9898B0)),
          _buildStrategyRow(
            '最优持有期操作',
            '${(_data!['recommendation'] as Map)?['optimal_avg_return'] ?? 0}%',
            ((_data!['recommendation'] as Map)?['optimal_avg_return'] as num?)?.toDouble() ?? 0,
          ),
          const SizedBox(height: 8),
          Text(
            '${(_data!['recommendation'] as Map)?['advice'] ?? ''}',
            style: const TextStyle(
                color: AppTheme.textSecondary, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildStrategyRow(String label, String value, double ret) {
    return Row(
      children: [
        Text(label,
            style: const TextStyle(
                color: AppTheme.textSecondary, fontSize: 13)),
        const Spacer(),
        Text(value,
            style: TextStyle(
              color: ret >= 0 ? AppTheme.green : AppTheme.red,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            )),
      ],
    );
  }
}
