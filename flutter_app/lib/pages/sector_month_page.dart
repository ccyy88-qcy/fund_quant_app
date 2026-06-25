import 'package:flutter/material.dart';
import '../services/sector_data_service.dart';
import '../theme/app_theme.dart';

class SectorMonthPage extends StatefulWidget {
  const SectorMonthPage({super.key});

  @override
  State<SectorMonthPage> createState() => _SectorMonthPageState();
}

class _SectorMonthPageState extends State<SectorMonthPage> {
  final _service = SectorDataService();
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _results = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await _service.fetchAllSectorsMonthly();
      if (!mounted) return;
      setState(() {
        _results = results;
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('行业月度涨跌幅'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primary),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: AppTheme.red),
            const SizedBox(height: 12),
            Text('加载失败', style: TextStyle(color: AppTheme.textSecondary)),
            const SizedBox(height: 8),
            Text(_error!, style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadData,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (_results.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.inbox_outlined, size: 48, color: AppTheme.textSecondary.withOpacity(0.4)),
            const SizedBox(height: 12),
            Text('暂无数据', style: TextStyle(color: AppTheme.textSecondary)),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          // 概览卡片
          _buildSummaryCard(),
          const SizedBox(height: 12),
          // 涨幅 TOP10
          _buildSectionTitle('📈 月度涨幅 TOP10'),
          ..._results.take(10).map((s) => _buildSectorCard(s, isGainer: true)),
          const SizedBox(height: 16),
          // 跌幅 TOP5
          _buildSectionTitle('📉 月度跌幅 TOP5'),
          ..._results.reversed.take(5).map((s) => _buildSectorCard(s, isGainer: false)),
          const SizedBox(height: 16),
          // 完整列表
          _sectionTitle('📋 全部行业 (${_results.length})'),
          ..._results.map((s) => _buildSectorCard(s, isGainer: s['month_chg_pct'] >= 0)),
        ],
      ),
    );
  }

  Widget _buildSummaryCard() {
    final upCount = _results.where((s) => s['month_chg_pct'] >= 0).length;
    final downCount = _results.length - upCount;
    final avgChg = _results.isNotEmpty
        ? _results.fold<double>(0, (sum, s) => sum + (s['month_chg_pct'] as double)) / _results.length
        : 0;

    return Container(
      padding: const EdgeInsets.all(16),
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
        border: Border.all(color: AppTheme.primary.withOpacity(0.3), width: 0.5),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildStatItem('上涨', '$upCount', AppTheme.green),
          ),
          Expanded(
            child: _buildStatItem('下跌', '$downCount', AppTheme.red),
          ),
          Expanded(
            child: _buildStatItem('平均', '${avgChg.toStringAsFixed(2)}%', avgChg >= 0 ? AppTheme.green : AppTheme.red),
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          color: AppTheme.textPrimary,
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildSectorCard(Map<String, dynamic> s, {required bool isGainer}) {
    final chg = s['month_chg_pct'] as double;
    final dd60 = s['max_drawdown_60d'] as double;
    final upDays = s['up_days'] as int;
    final downDays = s['down_days'] as int;
    final avgDaily = s['avg_daily_chg'] as double;
    final maxDaily = s['max_daily_chg'] as double;
    final minDaily = s['min_daily_chg'] as int;

    final color = chg >= 0 ? AppTheme.green : AppTheme.red;

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.2), width: 0.5),
      ),
      child: Column(
        children: [
          Row(
            children: [
              // 涨跌幅
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${chg >= 0 ? '+' : ''}${chg.toStringAsFixed(2)}%',
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              // 名称和上级行业
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      s['name'] ?? '-',
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontWeight: FontWeight.w500,
                        fontSize: 14,
                      ),
                    ),
                    Text(
                      '${s['parent'] ?? ''} · ${s['code']}',
                      style: TextStyle(
                        color: AppTheme.textSecondary.withOpacity(0.7),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              // 60日回撤
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '60日回撤',
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 10),
                  ),
                  Text(
                    '${dd60.toStringAsFixed(1)}%',
                    style: TextStyle(
                      color: dd60 < -15 ? AppTheme.red : AppTheme.textSecondary,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          // 详细信息行
          Row(
            children: [
              _buildMiniStat('↑$upDays↓$downDays', '涨跌天数'),
              const SizedBox(width: 16),
              _buildMiniStat('日均${avgDaily >= 0 ? '+' : ''}${avgDaily.toStringAsFixed(2)}%', '日均'),
              const SizedBox(width: 16),
              _buildMiniStat('最高${maxDaily >= 0 ? '+' : ''}${maxDaily.toStringAsFixed(1)}%', '单日'),
              const SizedBox(width: 16),
              _buildMiniStat('最低${minDaily >= 0 ? '+' : ''}${minDaily.toStringAsFixed(1)}%', '单日'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMiniStat(String value, String label) {
    return Column(
      children: [
        Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 11, fontWeight: FontWeight.w500)),
        Text(label, style: TextStyle(color: AppTheme.textSecondary.withOpacity(0.6), fontSize: 9)),
      ],
    );
  }
}
