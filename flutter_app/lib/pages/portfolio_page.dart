import 'dart:convert';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class PortfolioPage extends StatefulWidget {
  const PortfolioPage({super.key});

  @override
  State<PortfolioPage> createState() => _PortfolioPageState();
}

class _PortfolioPageState extends State<PortfolioPage>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  late TabController _tabController;

  bool _loadingFrontier = false;
  bool _loadingOptimize = false;
  Map<String, dynamic>? _frontier;
  Map<String, dynamic>? _optimized;

  String _objective = 'sharpe';
  int _nAssets = 5;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadFrontier() async {
    setState(() => _loadingFrontier = true);
    try {
      final data = await _api.getEfficientFrontier(nAssets: _nAssets);
      if (!mounted) return;
      setState(() {
        _frontier = data;
        _loadingFrontier = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingFrontier = false);
    }
  }

  Future<void> _loadOptimize() async {
    setState(() => _loadingOptimize = true);
    try {
      final data =
          await _api.optimizePortfolio(objective: _objective, nAssets: _nAssets);
      if (!mounted) return;
      setState(() {
        _optimized = data;
        _loadingOptimize = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingOptimize = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('资产配置'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: '有效前沿'),
            Tab(text: '风险平价'),
            Tab(text: '最大夏普'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildFrontierTab(),
          _buildRiskParityTab(),
          _buildMaxSharpeTab(),
        ],
      ),
    );
  }

  Widget _buildLoading() => const Center(
        child: CircularProgressIndicator(color: AppTheme.primary),
      );

  Widget _buildEmpty(String msg) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox_outlined,
                size: 56, color: AppTheme.textSecondary.withOpacity(0.4)),
            const SizedBox(height: 12),
            Text(msg,
                style: const TextStyle(color: AppTheme.textSecondary)),
          ],
        ),
      );

  // ─── 有效前沿 ───
  Widget _buildFrontierTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    const Text('资产数量:',
                        style: TextStyle(color: AppTheme.textSecondary)),
                    const Spacer(),
                    SegmentedButton<int>(
                      segments: const [
                        ButtonSegment(value: 3, label: Text('3')),
                        ButtonSegment(value: 5, label: Text('5')),
                        ButtonSegment(value: 10, label: Text('10')),
                      ],
                      selected: {_nAssets},
                      onSelectionChanged: (v) {
                        setState(() => _nAssets = v.first);
                      },
                      style: ButtonStyle(
                        backgroundColor: WidgetStateProperty.resolveWith(
                            (states) => states.contains(WidgetState.selected)
                                ? AppTheme.primary
                                : AppTheme.bgCardAlt),
                        foregroundColor: WidgetStateProperty.resolveWith(
                            (states) => states.contains(WidgetState.selected)
                                ? Colors.white
                                : AppTheme.textSecondary),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _loadFrontier,
                    icon: const Icon(Icons.trending_up, size: 18),
                    label: const Text('计算有效前沿'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Expanded(child: _buildFrontierResult()),
        ],
      ),
    );
  }

  Widget _buildFrontierResult() {
    if (_loadingFrontier) return _buildLoading();
    if (_frontier == null) return _buildEmpty('点击按钮计算有效前沿');

    final points = _frontier!['points'] as List<dynamic>? ?? [];
    final optimal = _frontier!['optimal'] as Map<String, dynamic>? ?? {};

    return ListView(
      children: [
        if (optimal.isNotEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0x1A8B5CF6), Color(0x0D00D4FF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: AppTheme.primary.withOpacity(0.3), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('最优组合',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...optimal.entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(e.key,
                                style: const TextStyle(
                                    color: AppTheme.textSecondary)),
                          ),
                          Text('${e.value}',
                              style: const TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontWeight: FontWeight.w500)),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        if (points.isNotEmpty) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('前沿点',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...points.take(20).map((p) {
                  final ret = (p['return'] as num?) ?? 0;
                  final risk = (p['risk'] as num?) ?? 0;
                  final sr = (p['sharpe'] as num?) ?? 0;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 4),
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.bgCardAlt,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Text('收益: ${ret.toStringAsFixed(2)}%',
                            style: const TextStyle(
                                color: AppTheme.green, fontSize: 12)),
                        const SizedBox(width: 12),
                        Text('风险: ${risk.toStringAsFixed(2)}%',
                            style: const TextStyle(
                                color: AppTheme.red, fontSize: 12)),
                        const Spacer(),
                        Text('夏普: ${sr.toStringAsFixed(2)}',
                            style: const TextStyle(
                                color: AppTheme.accent,
                                fontSize: 12,
                                fontWeight: FontWeight.w600)),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ],
      ],
    );
  }

  // ─── 风险平价 ───
  Widget _buildRiskParityTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                setState(() => _objective = 'risk_parity');
                _loadOptimize();
              },
              icon: const Icon(Icons.balance, size: 18),
              label: const Text('计算风险平价组合'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(child: _buildOptimizeResult('risk_parity')),
        ],
      ),
    );
  }

  // ─── 最大夏普 ───
  Widget _buildMaxSharpeTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                setState(() => _objective = 'sharpe');
                _loadOptimize();
              },
              icon: const Icon(Icons.star, size: 18),
              label: const Text('计算最大夏普组合'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(child: _buildOptimizeResult('sharpe')),
        ],
      ),
    );
  }

  Widget _buildOptimizeResult(String expectedObjective) {
    if (_loadingOptimize) return _buildLoading();
    if (_optimized == null || _objective != expectedObjective) {
      return _buildEmpty('点击上方按钮计算');
    }

    final weights = _optimized!['weights'] as List<dynamic>? ?? [];
    final metrics = _optimized!['metrics'] as Map<String, dynamic>? ?? {};
    final allocation =
        _optimized!['allocation'] as Map<String, dynamic>? ?? {};

    return ListView(
      children: [
        if (metrics.isNotEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0x1A8B5CF6), Color(0x0D00D4FF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: AppTheme.primary.withOpacity(0.3), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _objective == 'sharpe' ? '最大夏普组合' : '风险平价组合',
                  style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 12),
                ...metrics.entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(e.key,
                                style: const TextStyle(
                                    color: AppTheme.textSecondary)),
                          ),
                          Text('${e.value}',
                              style: const TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontWeight: FontWeight.w500)),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        if (allocation.isNotEmpty) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('资产配置权重',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...allocation.entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 80,
                            child: Text(e.key,
                                style: const TextStyle(
                                    color: AppTheme.textSecondary)),
                          ),
                          Expanded(
                            child: LinearProgressIndicator(
                              value: (e.value is num)
                                  ? (e.value as num).toDouble().clamp(0, 1)
                                  : 0,
                              backgroundColor: AppTheme.bgCardAlt,
                              color: AppTheme.accent,
                              minHeight: 8,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            (e.value is num)
                                ? '${((e.value as num) * 100).toStringAsFixed(1)}%'
                                : '${e.value}',
                            style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        ],
        if (weights.isNotEmpty) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('权重明细',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...weights.asMap().entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Text('资产 ${e.key + 1}',
                              style: const TextStyle(
                                  color: AppTheme.textSecondary)),
                          const Spacer(),
                          Text(
                            (e.value is num)
                                ? '${((e.value as num) * 100).toStringAsFixed(1)}%'
                                : '${e.value}',
                            style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
