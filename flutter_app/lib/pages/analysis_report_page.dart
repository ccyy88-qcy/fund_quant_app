import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class AnalysisReportPage extends StatefulWidget {
  const AnalysisReportPage({super.key});

  @override
  State<AnalysisReportPage> createState() => _AnalysisReportPageState();
}

class _AnalysisReportPageState extends State<AnalysisReportPage> {
  final _api = ApiService();
  final _codeController = TextEditingController(text: '562360');
  Map<String, dynamic>? _report;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadReport() async {
    setState(() {
      _loading = true;
      _error = null;
      _report = null;
    });
    try {
      final result = await _api.getAnalysisReport(_codeController.text.trim());
      if (!mounted) return;
      setState(() {
        _report = result;
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

  Color _ratingColor(String? rating) {
    if (rating == null) return AppTheme.grey;
    if (rating == 'S') return const Color(0xFFFFD700);
    if (rating == 'A') return AppTheme.green;
    if (rating == 'B') return AppTheme.yellow;
    if (rating == 'C') return AppTheme.red;
    if (rating == 'D') return const Color(0xFFB71C1C);
    return AppTheme.grey;
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
                  onSubmitted: (_) => _loadReport(),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                decoration: BoxDecoration(
                  gradient: AppTheme.neonGradient,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: IconButton(
                  onPressed: _loadReport,
                  icon: const Icon(Icons.auto_awesome, color: Colors.white),
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
              ),
              child: Text('$_error',
                  style: const TextStyle(color: AppTheme.red)),
            )
          else if (_report != null) ...[
            _buildHeader(),
            const SizedBox(height: 16),
            _buildSection('技术面', _report!['technical_score']),
            _buildSection('估值面', _report!['valuation_score']),
            _buildSection('动量面', _report!['momentum_score']),
            _buildSection('风险面', _report!['risk_score']),
            if (_report!['comprehensive_rating'] != null) ...[
              const SizedBox(height: 16),
              _buildRatingSection(),
            ],
            if (_report!['investment_advice'] != null) ...[
              const SizedBox(height: 16),
              _buildAdviceSection(),
            ],
          ] else
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.auto_awesome, size: 64,
                      color: AppTheme.accent.withOpacity(0.5)),
                  const SizedBox(height: 16),
                  const Text('输入基金代码一键AI分析',
                      style: TextStyle(color: AppTheme.textSecondary)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    final name = _report!['name'] ?? '';
    final code = _report!['code'] ?? '';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.primary.withOpacity(0.15), AppTheme.accent.withOpacity(0.1)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.primary.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.auto_awesome, color: AppTheme.accent, size: 28),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$name', style: const TextStyle(
                  color: AppTheme.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
              Text(code, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSection(String title, dynamic data) {
    if (data == null) return const SizedBox();
    final score = (data is Map) ? (data['score'] ?? 0) : data;
    final detail = (data is Map) ? (data['detail'] ?? '') : '';
    final s = (score is num) ? score.toDouble() : 0.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(title, style: const TextStyle(
                  color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
              const Spacer(),
              Text('${s.toStringAsFixed(0)}分', style: TextStyle(
                  color: s >= 70 ? AppTheme.green : (s >= 45 ? AppTheme.yellow : AppTheme.red),
                  fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: s / 100,
              backgroundColor: AppTheme.bgCardAlt,
              valueColor: AlwaysStoppedAnimation<Color>(
                s >= 70 ? AppTheme.green : (s >= 45 ? AppTheme.yellow : AppTheme.red),
              ),
              minHeight: 4,
            ),
          ),
          if (detail.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(detail, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
          ],
        ],
      ),
    );
  }

  Widget _buildRatingSection() {
    final r = _report!['comprehensive_rating'] as Map<String, dynamic>? ?? {};
    final rating = r['rating'] ?? '';
    final color = _ratingColor(rating);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.1), color.withOpacity(0.05)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            width: 50, height: 50,
            decoration: BoxDecoration(
              color: color.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text('$rating', style: TextStyle(
                  color: color, fontSize: 24, fontWeight: FontWeight.bold)),
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('综合评级: $rating', style: TextStyle(
                  color: color, fontWeight: FontWeight.bold, fontSize: 16)),
              Text(r['description'] ?? '', style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 12)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAdviceSection() {
    final a = _report!['investment_advice'] as Map<String, dynamic>? ?? {};
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.accent.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.lightbulb_outline, color: AppTheme.accent, size: 20),
              const SizedBox(width: 8),
              const Text('投资建议',
                  style: TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 12),
          if (a['direction'] != null)
            _infoRow('方向', a['direction']),
          if (a['position'] != null)
            _infoRow('仓位', a['position']),
          if (a['logic'] != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('${a['logic']}',
                  style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
            ),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Text('$label: ',
              style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
          Text(value,
              style: const TextStyle(
                  color: AppTheme.textPrimary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
