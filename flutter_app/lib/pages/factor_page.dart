import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class FactorPage extends StatefulWidget {
  const FactorPage({super.key});

  @override
  State<FactorPage> createState() => _FactorPageState();
}

class _FactorPageState extends State<FactorPage>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  late TabController _tabController;

  bool _loadingAnalysis = false;
  bool _loadingIc = false;
  bool _loadingLayer = false;
  Map<String, dynamic>? _analysis;
  Map<String, dynamic>? _icHistory;
  Map<String, dynamic>? _layerBacktest;

  String _selectedFactor = 'pe_ratio';
  final int _layers = 5;

  final List<String> _factorOptions = [
    'pe_ratio',
    'pb_ratio',
    'roe',
    'profit_growth',
    'revenue_growth',
    'debt_ratio',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    await Future.wait([_loadAnalysis(), _loadIcHistory()]);
  }

  Future<void> _loadAnalysis() async {
    setState(() => _loadingAnalysis = true);
    try {
      final data = await _api.getFactorAnalysis();
      if (!mounted) return;
      setState(() {
        _analysis = data;
        _loadingAnalysis = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingAnalysis = false);
    }
  }

  Future<void> _loadIcHistory() async {
    setState(() => _loadingIc = true);
    try {
      final data = await _api.getIcHistory();
      if (!mounted) return;
      setState(() {
        _icHistory = data;
        _loadingIc = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingIc = false);
    }
  }

  Future<void> _loadLayerBacktest() async {
    setState(() => _loadingLayer = true);
    try {
      final data =
          await _api.getLayerBacktest(_selectedFactor, _layers);
      if (!mounted) return;
      setState(() {
        _layerBacktest = data;
        _loadingLayer = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingLayer = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('多因子选股'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: '因子IC'),
            Tab(text: '合成因子'),
            Tab(text: '分层回测'),
            Tab(text: '相关性'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildIcTab(),
          _buildCompositeTab(),
          _buildLayerTab(),
          _buildCorrelationTab(),
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

  Widget _buildError(dynamic e) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline,
                size: 48, color: AppTheme.red),
            const SizedBox(height: 12),
            Text('$e',
                style: const TextStyle(color: AppTheme.textSecondary)),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadData,
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('重试'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
      );

  // ─── 因子IC Tab ───
  Widget _buildIcTab() {
    if (_loadingIc) return _buildLoading();
    if (_icHistory == null) return _buildEmpty('暂无因子IC数据');

    final icData = _icHistory!;
    final factors = (icData['factors'] as List<dynamic>?) ?? [];
    final icValues = (icData['ic_values'] as Map<String, dynamic>?) ?? {};

    return RefreshIndicator(
      onRefresh: _loadIcHistory,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
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
                    Icon(Icons.trending_up, color: AppTheme.accent, size: 20),
                    SizedBox(width: 8),
                    Text('因子IC分析',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                if (icValues.isEmpty)
                  const Text('暂无IC数据',
                      style: TextStyle(color: AppTheme.textSecondary))
                else
                  ...icValues.entries.map((e) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          children: [
                            SizedBox(
                                width: 100,
                                child: Text(e.key,
                                    style: const TextStyle(
                                        color: AppTheme.textSecondary))),
                            Expanded(
                              child: Text(
                                (e.value is num) ? e.value.toStringAsFixed(4) : '${e.value}',
                                style: const TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontWeight: FontWeight.w500),
                              ),
                            ),
                          ],
                        ),
                      )),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (factors.isNotEmpty)
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
                  const Text('因子列表',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  ...factors.map((f) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Text('${f}',
                            style: const TextStyle(
                                color: AppTheme.textSecondary)),
                      )),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // ─── 合成因子 Tab ───
  Widget _buildCompositeTab() {
    if (_loadingAnalysis) return _buildLoading();
    if (_analysis == null) return _buildEmpty('暂无因子数据');

    final composite = _analysis!['composite'] as Map<String, dynamic>? ?? {};
    final factorScores =
        _analysis!['factor_scores'] as List<dynamic>? ?? [];

    return RefreshIndicator(
      onRefresh: _loadAnalysis,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
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
              children: [
                const Text('合成因子得分',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w500)),
                const SizedBox(height: 8),
                Text(
                  '${(composite['score'] as num?)?.toStringAsFixed(2) ?? '-'}',
                  style: const TextStyle(
                      color: AppTheme.accent,
                      fontSize: 36,
                      fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text('排名: ${composite['rank'] ?? '-'}',
                    style: const TextStyle(
                        color: AppTheme.textSecondary, fontSize: 13)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          if (factorScores.isNotEmpty)
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
                  const Text('各因子评分',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  ...factorScores.map((f) {
                    final name = f['factor'] ?? f['name'] ?? '-';
                    final score = f['score'] ?? 0;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          SizedBox(
                              width: 100,
                              child: Text('$name',
                                  style: const TextStyle(
                                      color: AppTheme.textSecondary))),
                          Expanded(
                            child: LinearProgressIndicator(
                              value: (score is num) ? score.toDouble().abs().clamp(0, 1) : 0,
                              backgroundColor: AppTheme.bgCardAlt,
                              color: AppTheme.accent,
                              minHeight: 6,
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text((score is num) ? score.toStringAsFixed(2) : '$score',
                              style: const TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontWeight: FontWeight.w500)),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // ─── 分层回测 Tab ───
  Widget _buildLayerTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 参数选择
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('分层回测参数',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: _selectedFactor,
                  decoration: const InputDecoration(labelText: '因子'),
                  items: _factorOptions.map((f) => DropdownMenuItem(
                        value: f,
                        child: Text(f, style: const TextStyle(color: AppTheme.textPrimary)),
                      )).toList(),
                  onChanged: (v) {
                    if (v != null) setState(() => _selectedFactor = v);
                  },
                ),
                const SizedBox(height: 12),
                Text('分层数: $_layers',
                    style: const TextStyle(color: AppTheme.textSecondary)),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _loadLayerBacktest,
                    icon: const Icon(Icons.play_arrow, size: 18),
                    label: const Text('运行回测'),
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
          Expanded(child: _buildLayerResult()),
        ],
      ),
    );
  }

  Widget _buildLayerResult() {
    if (_loadingLayer) return _buildLoading();
    if (_layerBacktest == null) return _buildEmpty('点击"运行回测"查看结果');

    final layers = _layerBacktest!['layers'] as List<dynamic>? ?? [];
    final metrics = _layerBacktest!['metrics'] as Map<String, dynamic>? ?? {};

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
                const Text('回测指标',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
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
        if (layers.isNotEmpty) ...[
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
                const Text('分层收益',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...layers.asMap().entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Text('第${e.key + 1}层',
                              style: const TextStyle(
                                  color: AppTheme.textSecondary)),
                          const Spacer(),
                          Text(
                            (e.value is num) ? '${e.value.toStringAsFixed(2)}%' : '${e.value}',
                            style: TextStyle(
                              color: (e.value is num && e.value > 0)
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

  // ─── 相关性 Tab ───
  Widget _buildCorrelationTab() {
    if (_loadingAnalysis) return _buildLoading();
    if (_analysis == null) return _buildEmpty('暂无相关性数据');

    final corrMatrix =
        _analysis!['correlation'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: _loadAnalysis,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
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
                    Icon(Icons.grid_on, color: AppTheme.accent, size: 20),
                    SizedBox(width: 8),
                    Text('因子相关性矩阵',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                if (corrMatrix.isEmpty)
                  const Text('暂无数据',
                      style: TextStyle(color: AppTheme.textSecondary))
                else
                  ...corrMatrix.entries.map((e) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          children: [
                            SizedBox(
                                width: 100,
                                child: Text(e.key,
                                    style: const TextStyle(
                                        color: AppTheme.textSecondary))),
                            Expanded(
                              child: Text(
                                (e.value is num) ? e.value.toStringAsFixed(3) : '${e.value}',
                                style: TextStyle(
                                  color: (e.value is num)
                                      ? (e.value.abs() > 0.7
                                          ? AppTheme.yellow
                                          : AppTheme.textPrimary)
                                      : AppTheme.textPrimary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
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
}
