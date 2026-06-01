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
  List<dynamic> _indices = [];
  List<dynamic> _watchlistData = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final api = ApiService();
      final indices = await api.getIndex();
      List<dynamic> wlData = [];
      try {
        wlData = await api.getWatchlistRealtime();
      } catch (_) {}

      if (!mounted) return;
      setState(() {
        _indices = indices;
        _watchlistData = wlData;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '连接服务器失败\n${e.toString().substring(0, 80)}';
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
            Icon(Icons.auto_graph, color: AppTheme.accent, size: 24),
            SizedBox(width: 8),
            Text('基金量化工具'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: AppTheme.accent),
            onPressed: _loadData,
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppTheme.accent,
        onRefresh: _loadData,
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
            : _error != null
                ? Center(
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
                            onPressed: _loadData,
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
                  )
                : SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // 指数行情
                        _buildSectionTitle('📊 大盘指数'),
                        const SizedBox(height: 12),
                        _buildIndexCards(),
                        const SizedBox(height: 24),

                        // 自选基金实时估值
                        _buildSectionTitle('💰 自选基金实时估值'),
                        const SizedBox(height: 12),
                        _watchlistData.isEmpty
                            ? _buildEmptyWatchlist()
                            : _buildWatchlistCards(),

                        // 市场雷达
                        const SizedBox(height: 24),
                        _buildMarketRadar(),
                      ],
                    ),
                  ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(title, style: const TextStyle(
      color: AppTheme.textPrimary,
      fontSize: 18,
      fontWeight: FontWeight.w600,
    ));
  }

  Widget _buildIndexCards() {
    if (_indices.isEmpty) {
      return const Center(child: Text('暂无指数数据', style: TextStyle(color: AppTheme.textSecondary)));
    }
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _indices.length,
        separatorBuilder: (_, __) => const SizedBox(width: 12),
        itemBuilder: (_, i) {
          final idx = _indices[i];
          final change = (idx['change'] as num?)?.toDouble() ?? 0;
          final color = AppTheme.changeColor(change);
          return Container(
            width: 150,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.bgCard,
                  AppTheme.bgCardAlt,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
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
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${change >= 0 ? '+' : ''}${change.toStringAsFixed(2)}%',
                    style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptyWatchlist() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
      ),
      child: Column(
        children: [
          Icon(Icons.star_outline, size: 48, color: AppTheme.textSecondary.withOpacity(0.5)),
          const SizedBox(height: 12),
          const Text('还没有添加自选基金', style: TextStyle(color: AppTheme.textSecondary)),
          const SizedBox(height: 8),
          const Text('在「量化回测」中搜索并添加到自选', style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildWatchlistCards() {
    return Column(
      children: _watchlistData.map((f) {
        final change = (f['est_change'] as num?)?.toDouble();
        final nav = (f['est_nav'] as num?)?.toDouble() ?? (f['nav'] as num?)?.toDouble();
        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppTheme.bgCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(f['name'] ?? '', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text('${f['code']}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  ],
                ),
              ),
              if (nav != null)
                Text(nav.toStringAsFixed(4), style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w500)),
              const SizedBox(width: 16),
              if (change != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.changeColor(change).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${change >= 0 ? '+' : ''}${change.toStringAsFixed(2)}%',
                    style: TextStyle(
                      color: AppTheme.changeColor(change),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                )
              else
                const Text('--', style: TextStyle(color: AppTheme.textSecondary)),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildMarketRadar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: AppTheme.neonGradient.withOpacity(0.08) as Gradient? ?? LinearGradient(
          colors: [AppTheme.primary.withOpacity(0.08), AppTheme.accent.withOpacity(0.08)],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.radar, color: AppTheme.accent, size: 20),
              const SizedBox(width: 8),
              const Text('市场雷达', style: TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
              const Spacer(),
              Text(
                '${DateTime.now().toString().substring(0, 10)}',
                style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildRadarItem(Icons.trending_up, '板块轮动', '申万行业排行', 'quant'),
          const SizedBox(height: 8),
          _buildRadarItem(Icons.monitor_heart, '量化信号', 'MA10+MA60规则回测', 'backtest'),
        ],
      ),
    );
  }

  Widget _buildRadarItem(IconData icon, String title, String subtitle, String route) {
    return InkWell(
      onTap: () {},
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Icon(icon, color: AppTheme.accent, size: 18),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14)),
                Text(subtitle, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
              ],
            ),
            const Spacer(),
            const Icon(Icons.chevron_right, color: AppTheme.textSecondary, size: 18),
          ],
        ),
      ),
    );
  }
}
