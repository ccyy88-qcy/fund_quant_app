import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class RiskAnalysisPage extends StatefulWidget {
  const RiskAnalysisPage({super.key});

  @override
  State<RiskAnalysisPage> createState() => _RiskAnalysisPageState();
}

class _RiskAnalysisPageState extends State<RiskAnalysisPage>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  late TabController _tabController;
  final _codeController = TextEditingController(text: '000001');

  bool _loadingAnalysis = false;
  bool _loadingVar = false;
  bool _loadingStress = false;

  Map<String, dynamic>? _analysis;
  Map<String, dynamic>? _varData;
  Map<String, dynamic>? _stressData;

  double _varConfidence = 0.95;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) return;
    await Future.wait([
      _loadAnalysis(code),
      _loadVar(code),
      _loadStress(code),
    ]);
  }

  Future<void> _loadAnalysis(String code) async {
    setState(() => _loadingAnalysis = true);
    try {
      final data = await _api.getRiskAnalysis(code);
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

  Future<void> _loadVar(String code) async {
    setState(() => _loadingVar = true);
    try {
      final data = await _api.getVarAnalysis(code, _varConfidence);
      if (!mounted) return;
      setState(() {
        _varData = data;
        _loadingVar = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingVar = false);
    }
  }

  Future<void> _loadStress(String code) async {
    setState(() => _loadingStress = true);
    try {
      final data = await _api.getStressTest(code);
      if (!mounted) return;
      setState(() {
        _stressData = data;
        _loadingStress = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingStress = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('风险分析'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: 'VaR'),
            Tab(text: '回撤分析'),
            Tab(text: '压力测试'),
            Tab(text: '尾部风险'),
          ],
        ),
      ),
      body: Column(
        children: [
          // 搜索栏
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _codeController,
                    decoration: const InputDecoration(
                      hintText: '输入基金代码',
                      prefixIcon:
                          Icon(Icons.search, color: AppTheme.accent),
                    ),
                    textInputAction: TextInputAction.go,
                    onSubmitted: (_) => _loadAll(),
                  ),
                ),
                const SizedBox(width: 12),
                IconButton(
                  onPressed: _loadAll,
                  icon: const Icon(Icons.refresh, color: AppTheme.accent),
                ),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildVarTab(),
                _buildDrawdownTab(),
                _buildStressTab(),
                _buildTailRiskTab(),
              ],
            ),
          ),
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

  // ─── VaR Tab ───
  Widget _buildVarTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // 置信度选择
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
                const Text('VaR参数',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Text('置信度:',
                        style: TextStyle(color: AppTheme.textSecondary)),
                    const SizedBox(width: 12),
                    SegmentedButton<double>(
                      segments: const [
                        ButtonSegment(value: 0.90, label: Text('90%')),
                        ButtonSegment(value: 0.95, label: Text('95%')),
                        ButtonSegment(value: 0.99, label: Text('99%')),
                      ],
                      selected: {_varConfidence},
                      onSelectionChanged: (v) {
                        setState(() => _varConfidence = v.first);
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
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      final code = _codeController.text.trim();
                      if (code.isNotEmpty) _loadVar(code);
                    },
                    icon: const Icon(Icons.calculate, size: 18),
                    label: const Text('计算VaR'),
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
          Expanded(child: _buildVarResult()),
        ],
      ),
    );
  }

  Widget _buildVarResult() {
    if (_loadingVar) return _buildLoading();
    if (_varData == null) return _buildEmpty('设置参数后点击计算');

    return ListView(
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppTheme.red.withOpacity(0.1),
                AppTheme.red.withOpacity(0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: AppTheme.red.withOpacity(0.3), width: 0.5),
          ),
          child: Column(
            children: [
              const Text('在险价值 (VaR)',
                  style: TextStyle(
                      color: AppTheme.textSecondary, fontSize: 13)),
              const SizedBox(height: 8),
              Text(
                '${(_varData!['var'] as num?)?.toStringAsFixed(2) ?? '-'}%',
                style: const TextStyle(
                    color: AppTheme.red,
                    fontSize: 36,
                    fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              ..._varData!.entries
                  .where((e) => e.key != 'var')
                  .map((e) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
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
      ],
    );
  }

  // ─── 回撤分析 Tab ───
  Widget _buildDrawdownTab() {
    if (_loadingAnalysis) return _buildLoading();
    if (_analysis == null) return _buildEmpty('搜索基金代码查看回撤分析');

    final dd = _analysis!['drawdown'] as Map<String, dynamic>? ??
        _analysis!['max_drawdown'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: () => _loadAnalysis(_codeController.text.trim()),
      child: ListView(
        padding: const EdgeInsets.all(16),
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
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.trending_down,
                        color: AppTheme.red, size: 20),
                    SizedBox(width: 8),
                    Text('最大回撤分析',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                if (dd.containsKey('max_drawdown'))
                  Center(
                    child: Text(
                      '${(dd['max_drawdown'] as num?)?.toStringAsFixed(2) ?? '-'}%',
                      style: const TextStyle(
                          color: AppTheme.red,
                          fontSize: 32,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                const SizedBox(height: 16),
                ...dd.entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
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
        ],
      ),
    );
  }

  // ─── 压力测试 Tab ───
  Widget _buildStressTab() {
    if (_loadingStress) return _buildLoading();
    if (_stressData == null) return _buildEmpty('搜索基金代码查看压力测试');

    final scenarios = _stressData!['scenarios'] as List<dynamic>? ?? [];
    final result = _stressData!['result'] as Map<String, dynamic>? ?? {};

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (result.isNotEmpty)
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
                    Icon(Icons.warning_amber,
                        color: AppTheme.yellow, size: 20),
                    SizedBox(width: 8),
                    Text('压力测试结果',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                ...result.entries.map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
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
        if (scenarios.isNotEmpty) ...[
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
                const Text('压力情景',
                    style: TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 12),
                ...scenarios.map((s) => Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.bgCardAlt,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${s['name'] ?? s['scenario'] ?? '-'}',
                              style: const TextStyle(
                                  color: AppTheme.textPrimary,
                                  fontWeight: FontWeight.w500)),
                          if (s['impact'] != null)
                            Text(
                              '影响: ${s['impact']}',
                              style: TextStyle(
                                color: (s['impact'] is num &&
                                        s['impact'] < 0)
                                    ? AppTheme.red
                                    : AppTheme.green,
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

  // ─── 尾部风险 Tab ───
  Widget _buildTailRiskTab() {
    if (_loadingAnalysis) return _buildLoading();
    if (_analysis == null) return _buildEmpty('搜索基金代码查看尾部风险');

    final tail = _analysis!['tail_risk'] as Map<String, dynamic>? ??
        _analysis!['tail'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: () => _loadAnalysis(_codeController.text.trim()),
      child: ListView(
        padding: const EdgeInsets.all(16),
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
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.bolt, color: AppTheme.yellow, size: 20),
                    SizedBox(width: 8),
                    Text('尾部风险指标',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                if (tail.isEmpty)
                  const Text('暂无尾部风险数据',
                      style: TextStyle(color: AppTheme.textSecondary))
                else
                  ...tail.entries.map((e) => Padding(
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
}
