import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class RotationPage extends StatefulWidget {
  const RotationPage({super.key});

  @override
  State<RotationPage> createState() => _RotationPageState();
}

class _RotationPageState extends State<RotationPage>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  late TabController _tabController;

  bool _loadingCycle = false;
  bool _loadingScores = false;
  bool _loadingSignals = false;
  bool _loadingBacktest = false;

  Map<String, dynamic>? _macroCycle;
  List<dynamic>? _sectorScores;
  List<dynamic>? _rotationSignals;
  Map<String, dynamic>? _rotationBacktest;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadAll();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    await Future.wait([
      _loadCycle(),
      _loadScores(),
      _loadSignals(),
    ]);
  }

  Future<void> _loadCycle() async {
    setState(() => _loadingCycle = true);
    try {
      final data = await _api.getMacroCycle();
      if (!mounted) return;
      setState(() {
        _macroCycle = data;
        _loadingCycle = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingCycle = false);
    }
  }

  Future<void> _loadScores() async {
    setState(() => _loadingScores = true);
    try {
      final data = await _api.getSectorScores();
      if (!mounted) return;
      setState(() {
        _sectorScores = data;
        _loadingScores = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingScores = false);
    }
  }

  Future<void> _loadSignals() async {
    setState(() => _loadingSignals = true);
    try {
      final data = await _api.getRotationSignals();
      if (!mounted) return;
      setState(() {
        _rotationSignals = data;
        _loadingSignals = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingSignals = false);
    }
  }

  Future<void> _loadBacktest() async {
    setState(() => _loadingBacktest = true);
    try {
      final data = await _api.getRotationBacktest();
      if (!mounted) return;
      setState(() {
        _rotationBacktest = data;
        _loadingBacktest = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingBacktest = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('行业轮动'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: '宏观周期'),
            Tab(text: '行业评分'),
            Tab(text: '轮动信号'),
            Tab(text: '回测'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildCycleTab(),
          _buildScoresTab(),
          _buildSignalsTab(),
          _buildBacktestTab(),
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

  // ─── 宏观周期 ───
  Widget _buildCycleTab() {
    if (_loadingCycle) return _buildLoading();
    if (_macroCycle == null) return _buildEmpty('暂无宏观周期数据');

    final cycle = _macroCycle!;
    final current = cycle['current_phase'] as String? ?? '未知';
    final indicators =
        cycle['indicators'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: _loadCycle,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.primary.withOpacity(0.15),
                  AppTheme.accent.withOpacity(0.08),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: AppTheme.primary.withOpacity(0.3), width: 0.5),
            ),
            child: Column(
              children: [
                const Text('当前宏观周期',
                    style: TextStyle(
                        color: AppTheme.textSecondary, fontSize: 13)),
                const SizedBox(height: 8),
                Text(current,
                    style: const TextStyle(
                        color: AppTheme.accent,
                        fontSize: 28,
                        fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (indicators.isNotEmpty)
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
                  const Text('宏观指标',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  ...indicators.entries.map((e) => Padding(
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
        ],
      ),
    );
  }

  // ─── 行业评分 ───
  Widget _buildScoresTab() {
    if (_loadingScores) return _buildLoading();
    if (_sectorScores == null || _sectorScores!.isEmpty) {
      return _buildEmpty('暂无行业评分数据');
    }

    return RefreshIndicator(
      onRefresh: _loadScores,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _sectorScores!.length,
        itemBuilder: (_, i) {
          final s = _sectorScores![i];
          final score = (s['score'] as num?) ?? 0;
          final change = (s['change'] as num?) ?? 0;
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${s['name'] ?? s['sector'] ?? '-'}',
                          style: const TextStyle(
                              color: AppTheme.textPrimary,
                              fontWeight: FontWeight.w500)),
                      const SizedBox(height: 4),
                      Text('得分: ${score.toStringAsFixed(1)}',
                          style: const TextStyle(
                              color: AppTheme.textSecondary,
                              fontSize: 12)),
                    ],
                  ),
                ),
                Text(
                  change >= 0
                      ? '+${change.toStringAsFixed(1)}%'
                      : '${change.toStringAsFixed(1)}%',
                  style: TextStyle(
                    color: change >= 0 ? AppTheme.green : AppTheme.red,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ─── 轮动信号 ───
  Widget _buildSignalsTab() {
    if (_loadingSignals) return _buildLoading();
    if (_rotationSignals == null || _rotationSignals!.isEmpty) {
      return _buildEmpty('暂无轮动信号');
    }

    return RefreshIndicator(
      onRefresh: _loadSignals,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _rotationSignals!.length,
        itemBuilder: (_, i) {
          final s = _rotationSignals![i];
          final direction = '${s['direction'] ?? s['signal'] ?? 'hold'}';
          final isBuy = direction.contains('buy') || direction.contains('买入');
          final isSell =
              direction.contains('sell') || direction.contains('卖出');
          final sigColor = isBuy
              ? AppTheme.green
              : (isSell ? AppTheme.red : AppTheme.yellow);
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: sigColor.withOpacity(0.3), width: 0.5),
            ),
            child: Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: sigColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(direction,
                      style: TextStyle(
                          color: sigColor,
                          fontSize: 12,
                          fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text('${s['name'] ?? s['sector'] ?? '-'}',
                      style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontWeight: FontWeight.w500)),
                ),
                Text(
                  '${(s['confidence'] as num?)?.toStringAsFixed(1) ?? '-'}%',
                  style: const TextStyle(
                      color: AppTheme.textSecondary, fontSize: 13),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ─── 回测 ───
  Widget _buildBacktestTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _loadBacktest,
              icon: const Icon(Icons.play_arrow, size: 18),
              label: const Text('运行轮动回测'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(child: _buildBacktestResult()),
        ],
      ),
    );
  }

  Widget _buildBacktestResult() {
    if (_loadingBacktest) return _buildLoading();
    if (_rotationBacktest == null) return _buildEmpty('点击按钮运行回测');

    final bt = _rotationBacktest!;
    final metrics = bt['metrics'] as Map<String, dynamic>? ?? {};
    final trades = bt['trades'] as List<dynamic>? ?? [];

    return ListView(
      children: [
        if (metrics.isNotEmpty)
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
                const Row(
                  children: [
                    Icon(Icons.history, color: AppTheme.accent, size: 20),
                    SizedBox(width: 8),
                    Text('轮动回测结果',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                ...metrics.entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Row(
                        children: [
                          Text(e.key,
                              style: const TextStyle(
                                  color: AppTheme.textSecondary)),
                          const Spacer(),
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
        if (trades.isNotEmpty) ...[
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
                const Text('交易记录',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...trades.take(10).map((t) => Container(
                      margin: const EdgeInsets.only(bottom: 4),
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppTheme.bgCardAlt,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text('${t['sector'] ?? t['name'] ?? '-'}',
                                style: const TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontSize: 13)),
                          ),
                          Text(
                            '${(t['return'] as num?)?.toStringAsFixed(2) ?? '-'}%',
                            style: TextStyle(
                              color: (t['return'] as num? ?? 0) >= 0
                                  ? AppTheme.green
                                  : AppTheme.red,
                              fontWeight: FontWeight.w600,
                            ),
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
