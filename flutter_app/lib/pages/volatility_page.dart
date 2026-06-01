import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class VolatilityPage extends StatefulWidget {
  const VolatilityPage({super.key});

  @override
  State<VolatilityPage> createState() => _VolatilityPageState();
}

class _VolatilityPageState extends State<VolatilityPage>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  late TabController _tabController;
  final _codeController = TextEditingController(text: '000001');

  bool _loadingHV = false;
  bool _loadingSignal = false;
  Map<String, dynamic>? _hvData;
  Map<String, dynamic>? _volSignal;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    await _loadHV();
  }

  Future<void> _loadHV() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) return;
    setState(() => _loadingHV = true);
    try {
      final data = await _api.getRiskAnalysis(code);
      if (!mounted) return;
      setState(() {
        _hvData = data;
        _loadingHV = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingHV = false);
    }
  }

  Future<void> _loadSignal() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) return;
    setState(() => _loadingSignal = true);
    try {
      final signal = await _api.getSignal(code);
      if (!mounted) return;
      setState(() {
        _volSignal = signal;
        _loadingSignal = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingSignal = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('波动率策略'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: 'HV曲线'),
            Tab(text: '分位数'),
            Tab(text: '信号'),
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
                _buildHVTab(),
                _buildQuantileTab(),
                _buildSignalTab(),
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

  // ─── HV曲线 ───
  Widget _buildHVTab() {
    if (_loadingHV) return _buildLoading();
    if (_hvData == null) return _buildEmpty('输入基金代码并搜索');

    final hv = _hvData!['historical_volatility'] as Map<String, dynamic>? ??
        _hvData!['volatility'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: _loadHV,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.show_chart,
                        color: AppTheme.accent, size: 20),
                    SizedBox(width: 8),
                    Text('历史波动率(HV)',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                if (hv.isEmpty)
                  const Text('暂无HV数据',
                      style: TextStyle(color: AppTheme.textSecondary))
                else
                  ...hv.entries.map((e) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          children: [
                            Text(
                              '${e.key}'.replaceAll('_', ' ').toUpperCase(),
                              style: const TextStyle(
                                  color: AppTheme.textSecondary),
                            ),
                            const Spacer(),
                            Text(
                              (e.value is num)
                                  ? '${(e.value as num).toStringAsFixed(2)}%'
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
      ),
    );
  }

  // ─── 分位数 Tab ───
  Widget _buildQuantileTab() {
    if (_loadingHV) return _buildLoading();
    if (_hvData == null) return _buildEmpty('暂无分位数数据');

    final quantiles = _hvData!['quantiles'] as Map<String, dynamic>? ??
        _hvData!['percentiles'] as Map<String, dynamic>? ?? {};

    return RefreshIndicator(
      onRefresh: _loadHV,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.percent, color: AppTheme.accent, size: 20),
                    SizedBox(width: 8),
                    Text('波动率分位数',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 16),
                if (quantiles.isEmpty)
                  const Text('暂无数据',
                      style: TextStyle(color: AppTheme.textSecondary))
                else
                  ...quantiles.entries.map((e) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          children: [
                            Text(e.key,
                                style: const TextStyle(
                                    color: AppTheme.textSecondary)),
                            const Spacer(),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: (e.value is num &&
                                        e.value > 0.8)
                                    ? AppTheme.red.withOpacity(0.15)
                                    : (e.value is num && e.value < 0.2)
                                        ? AppTheme.green.withOpacity(0.15)
                                        : AppTheme.bgCardAlt,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                (e.value is num)
                                    ? '${((e.value as num) * 100).toStringAsFixed(0)}%'
                                    : '${e.value}',
                                style: TextStyle(
                                  color: (e.value is num && e.value > 0.8)
                                      ? AppTheme.red
                                      : (e.value is num && e.value < 0.2)
                                          ? AppTheme.green
                                          : AppTheme.textPrimary,
                                  fontWeight: FontWeight.w600,
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

  // ─── 信号 Tab ───
  Widget _buildSignalTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _loadSignal,
              icon: const Icon(Icons.analytics, size: 18),
              label: const Text('获取波动率信号'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(child: _buildSignalResult()),
        ],
      ),
    );
  }

  Widget _buildSignalResult() {
    if (_loadingSignal) return _buildLoading();
    if (_volSignal == null) return _buildEmpty('点击按钮获取信号');

    final s = _volSignal!;
    final signalType = '${s['type'] ?? 'wait'}';
    final sigColor = AppTheme.signalColor(signalType);

    return ListView(
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                sigColor.withOpacity(0.1),
                sigColor.withOpacity(0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: sigColor.withOpacity(0.3), width: 0.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: sigColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${s['signal'] ?? s['type'] ?? '-'}',
                  style: TextStyle(
                    color: sigColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              ...s.entries
                  .where((e) =>
                      e.key != 'signal' && e.key != 'type')
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
}
