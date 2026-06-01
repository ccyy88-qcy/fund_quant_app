import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../main.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final _api = ApiService();
  List<dynamic> _indices = [];
  List<dynamic> _watchlistData = [];
  List<dynamic> _fundRanks = [];
  Map<String, dynamic>? _sentiment;
  Map<String, dynamic>? _buildSignal;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadAllData();
  }

  Future<void> _loadAllData() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        _api.getIndex().catchError((_) => <dynamic>[]),
        _api.getWatchlistRealtime().catchError((_) => <dynamic>[]),
        _api.getBuildCandidates(topN: 10).catchError((_) => <dynamic>[]),
        _api.getMarketSentiment().catchError((_) => <Map<String, dynamic>>{}),
        _api.getBuildSignal('562360').catchError((_) => <String, dynamic>{}),
      ]);
      if (!mounted) return;
      setState(() {
        _indices = results[0] as List<dynamic>;
        _watchlistData = results[1] as List<dynamic>;
        _fundRanks = results[2] as List<dynamic>;
        _sentiment = results[3] as Map<String, dynamic>?;
        _buildSignal = results[4] as Map<String, dynamic>?;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '数据加载失败';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.auto_graph, color: AppTheme.accent, size: 22),
            SizedBox(width: 8),
            Text('基金量化'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: AppTheme.accent),
            onPressed: _loadAllData,
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppTheme.accent,
        onRefresh: _loadAllData,
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
            : _error != null
                ? _buildErrorView()
                : SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildBuildSignalBanner(),
                        const SizedBox(height: 12),
                        _buildSectionTitle('📊 大盘指数'),
                        const SizedBox(height: 8),
                        _buildIndexCards(),
                        const SizedBox(height: 16),
                        _buildSectionTitle('📈 市场情绪'),
                        const SizedBox(height: 8),
                        _buildSentimentBar(),
                        const SizedBox(height: 16),
                        _buildSectionTitle('🔥 实时建仓推荐（真实市场数据）'),
                        const SizedBox(height: 8),
                        _buildFundRankList(),
                        const SizedBox(height: 16),
                        _buildSectionTitle('💰 自选基金估值'),
                        const SizedBox(height: 8),
                        _watchlistData.isEmpty
                            ? _buildEmptyWidget('暂无自选基金', '在量化→回测信号中搜索添加')
                            : _buildWatchlistCards(),
                        const SizedBox(height: 16),
                        _buildRadarSection(),
                        const SizedBox(height: 24),
                      ],
                    ),
                  ),
      ),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 64, color: AppTheme.textSecondary),
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: AppTheme.textSecondary), textAlign: TextAlign.center),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _loadAllData,
              icon: const Icon(Icons.refresh),
              label: const Text('重试'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBuildSignalBanner() {
    if (_buildSignal == null || _buildSignal!.isEmpty) return const SizedBox.shrink();
    final signal = _buildSignal!['build_signal'] ?? '';
    final score = (_buildSignal!['total_score'] as num?)?.toDouble() ?? 0;
    final position = _buildSignal!['suggested_position'] ?? '';
    final detail = _buildSignal!['action_detail'] ?? '';
    final color = score >= 80 ? AppTheme.green : (score >= 65 ? const Color(0xFF66BB6A) : (score >= 45 ? AppTheme.yellow : (score >= 30 ? AppTheme.red : const Color(0xFFB71C1C))));

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [color.withOpacity(0.12), color.withOpacity(0.04)], begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
            child: Icon(score >= 65 ? Icons.trending_up : Icons.trending_flat, color: color, size: 28),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(signal, style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text('评分: ${score.toStringAsFixed(0)} | 建议仓位: $position', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                const SizedBox(height: 2),
                Text(detail, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
              ],
            ),
          ),
          SizedBox(
            width: 40, height: 40,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(value: score / 100, strokeWidth: 4, backgroundColor: color.withOpacity(0.15), valueColor: AlwaysStoppedAnimation<Color>(color)),
                Text('${score.toStringAsFixed(0)}', style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Row(
      children: [
        Text(title, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
        const Spacer(),
        TextButton(onPressed: _loadAllData, child: const Text('刷新', style: TextStyle(color: AppTheme.accent, fontSize: 12))),
      ],
    );
  }

  Widget _buildIndexCards() {
    if (_indices.isEmpty) return _buildEmptyWidget('暂无数据', '');
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _indices.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final idx = _indices[i];
          final change = (idx['change'] as num?)?.toDouble() ?? 0;
          final color = AppTheme.changeColor(change);
          return Container(
            width: 150, padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [AppTheme.bgCard, AppTheme.bgCardAlt], begin: Alignment.topLeft, end: Alignment.bottomRight),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: color.withOpacity(0.3), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(idx['name'] ?? '', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                const Spacer(),
                Text('${idx['price']}', style: const TextStyle(color: AppTheme.textPrimary, fontSize: 20, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                  child: Text('${change >= 0 ? '+' : ''}${change.toStringAsFixed(2)}%', style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w600)),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSentimentBar() {
    if (_sentiment == null || _sentiment!.isEmpty) return _buildEmptyWidget('加载中...', '');
    final index = (_sentiment!['sentiment_index'] as num?)?.toDouble() ?? 50;
    final interp = _sentiment!['interpretation'] ?? '';
    final action = _sentiment!['suggested_action'] ?? '';
    final barColor = index >= 65 ? AppTheme.red : (index >= 45 ? AppTheme.yellow : AppTheme.green);
    final scores = _sentiment!['scores'] as Map<String, dynamic>? ?? {};

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: AppTheme.bgCard, borderRadius: BorderRadius.circular(16), border: Border.all(color: barColor.withOpacity(0.2))),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(interp, style: TextStyle(color: barColor, fontSize: 16, fontWeight: FontWeight.bold)),
                    Text('建议: $action', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ),
              SizedBox(
                width: 56, height: 56,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    CircularProgressIndicator(value: index / 100, strokeWidth: 5, backgroundColor: barColor.withOpacity(0.15), valueColor: AlwaysStoppedAnimation<Color>(barColor)),
                    Text('${index.toStringAsFixed(0)}', style: TextStyle(color: barColor, fontSize: 16, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: scores.entries.take(4).map((e) {
              final v = (e.value as num?)?.toDouble() ?? 0;
              return Expanded(
                child: Column(
                  children: [
                    Text('${v.toStringAsFixed(0)}', style: TextStyle(color: v >= 60 ? AppTheme.red : (v >= 40 ? AppTheme.yellow : AppTheme.green), fontSize: 14, fontWeight: FontWeight.bold)),
                    Text(_shortLabel(e.key), style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  String _shortLabel(String key) {
    switch (key) {
      case 'advance_decline': return '涨跌';
      case 'volume': return '量能';
      case 'north_flow': return '北向';
      case 'limit_up_down': return '涨停';
      case 'macro': return '宏观';
      default: return key;
    }
  }

  Widget _buildFundRankList() {
    if (_fundRanks.isEmpty) return _buildEmptyWidget('扫描中...', '正在分析全市场ETF');
    return Column(
      children: _fundRanks.take(5).map((f) {
        final score = (f['total_score'] as num?)?.toDouble() ?? 0;
        final signal = f['build_signal'] ?? '';
        final change = (f['change_pct'] as num?)?.toDouble() ?? 0;
        final flow = (f['capital_flow_pct'] as num?)?.toDouble();
        final advice = f['short_term_advice'] ?? '';

        Color sc;
        if (signal.contains('强烈建仓')) sc = AppTheme.green;
        else if (signal.contains('建议建仓')) sc = const Color(0xFF66BB6A);
        else if (signal.contains('观察')) sc = AppTheme.yellow;
        else sc = AppTheme.grey;

        return Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: AppTheme.bgCard, borderRadius: BorderRadius.circular(12), border: Border.all(color: sc.withOpacity(0.15))),
          child: Row(
            children: [
              Container(width: 6, height: 40, decoration: BoxDecoration(color: sc, borderRadius: BorderRadius.circular(3))),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(f['name'] ?? '', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600, fontSize: 13)),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                          decoration: BoxDecoration(color: AppTheme.changeColor(change).withOpacity(0.15), borderRadius: BorderRadius.circular(4)),
                          child: Text('${change >= 0 ? '+' : ''}${change.toStringAsFixed(2)}%', style: TextStyle(color: AppTheme.changeColor(change), fontSize: 11, fontWeight: FontWeight.w600)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Text('${f['code'] ?? ''}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 10)),
                        if (flow != null) ...[const SizedBox(width: 8), Text('主力${flow >= 0 ? '+' : ''}${flow.toStringAsFixed(1)}%', style: TextStyle(color: flow >= 0 ? AppTheme.green : AppTheme.red, fontSize: 10))],
                      ],
                    ),
                    if (advice.isNotEmpty) Text(advice, style: const TextStyle(color: sc, fontSize: 10)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                decoration: BoxDecoration(color: sc.withOpacity(0.12), borderRadius: BorderRadius.circular(6)),
                child: Text('${score.toStringAsFixed(0)}分', style: TextStyle(color: sc, fontSize: 12, fontWeight: FontWeight.w600)),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildWatchlistCards() {
    return Column(
      children: _watchlistData.map((f) {
        final change = (f['est_change'] as num?)?.toDouble();
        final nav = (f['est_nav'] as num?)?.toDouble() ?? (f['nav'] as num?)?.toDouble();
        return Container(
          margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppTheme.bgCard, borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x338B5CF6), width: 0.5)),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(f['name'] ?? '', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 2),
                    Text('${f['code']}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ),
              if (nav != null) Text(nav.toStringAsFixed(4), style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w500)),
              const SizedBox(width: 12),
              if (change != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: AppTheme.changeColor(change).withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                  child: Text('${change >= 0 ? '+' : ''}${change.toStringAsFixed(2)}%', style: TextStyle(color: AppTheme.changeColor(change), fontWeight: FontWeight.w600)),
                )
              else
                const Text('--', style: TextStyle(color: AppTheme.textSecondary)),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildRadarSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [AppTheme.primary.withOpacity(0.08), AppTheme.accent.withOpacity(0.08)]),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.radar, color: AppTheme.accent, size: 18),
              const SizedBox(width: 8),
              const Text('市场雷达', style: TextStyle(color: AppTheme.textPrimary, fontSize: 15, fontWeight: FontWeight.w600)),
              const Spacer(),
              Text(DateTime.now().toString().substring(0, 10), style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 12),
          _radarItem(Icons.analytics, '量化信号', 'MA10+MA60回测 + 多因子 + 行业轮动'),
          const SizedBox(height: 6),
          _radarItem(Icons.auto_graph, '策略回测', '自定义策略 + 参数优化 + 多策略对比'),
          const SizedBox(height: 6),
          _radarItem(Icons.assessment, '风险分析', 'VaR + 回撤分析 + 压力测试 + 尾部风险'),
        ],
      ),
    );
  }

  Widget _radarItem(IconData icon, String title, String subtitle) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.accent, size: 16),
            const SizedBox(width: 10),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13)),
              Text(subtitle, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 11)),
            ]),
            const Spacer(),
            const Icon(Icons.chevron_right, color: AppTheme.textSecondary, size: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyWidget(String text, String sub) {
    return Container(
      width: double.infinity, padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: AppTheme.bgCard, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0x338B5CF6), width: 0.5)),
      child: Column(
        children: [
          Icon(Icons.inbox, size: 36, color: AppTheme.textSecondary.withOpacity(0.4)),
          const SizedBox(height: 8),
          Text(text, style: const TextStyle(color: AppTheme.textSecondary)),
          if (sub.isNotEmpty) ...[const SizedBox(height: 4), Text(sub, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12))],
        ],
      ),
    );
  }
}
