import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class QuantPage extends StatefulWidget {
  const QuantPage({super.key});

  @override
  State<QuantPage> createState() => _QuantPageState();
}

class _QuantPageState extends State<QuantPage> {
  final _searchController = TextEditingController();
  final _api = ApiService();
  List<dynamic> _searchResults = [];
  bool _searching = false;
  String? _selectedCode;
  Map<String, dynamic>? _signal;
  Map<String, dynamic>? _backtest;
  bool _loadingSignal = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search(String keyword) async {
    if (keyword.isEmpty) return;
    setState(() => _searching = true);
    try {
      final results = await _api.searchFunds(keyword);
      if (!mounted) return;
      setState(() {
        _searchResults = results;
        _searching = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _searching = false);
    }
  }

  Future<void> _analyze(String code) async {
    setState(() {
      _selectedCode = code;
      _loadingSignal = true;
      _signal = null;
      _backtest = null;
    });
    try {
      final signal = await _api.getSignal(code, pePct: 40, pbPct: 35);
      Map<String, dynamic>? backtest;
      try {
        backtest = await _api.getBacktest(code);
      } catch (_) {}

      if (!mounted) return;
      setState(() {
        _signal = signal;
        _backtest = backtest;
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
      appBar: AppBar(title: const Text('量化回测')),
      body: Column(
        children: [
          // 搜索栏
          Container(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索基金代码或名称...',
                prefixIcon: const Icon(Icons.search, color: AppTheme.accent),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, color: AppTheme.textSecondary),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchResults = []);
                        },
                      )
                    : null,
              ),
              onChanged: (v) {
                if (v.length >= 2) _search(v);
              },
              textInputAction: TextInputAction.search,
              onSubmitted: _search,
            ),
          ),

          // 搜索结果或分析面板
          Expanded(
            child: _selectedCode == null ? _buildSearchResults() : _buildAnalysisPanel(),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchResults() {
    if (_searching) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }
    if (_searchResults.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off, size: 64, color: AppTheme.textSecondary.withOpacity(0.5)),
            const SizedBox(height: 16),
            const Text('输入基金代码或名称开始搜索', style: TextStyle(color: AppTheme.textSecondary)),
          ],
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: _searchResults.length,
      itemBuilder: (_, i) {
        final f = _searchResults[i];
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          decoration: BoxDecoration(
            color: AppTheme.bgCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
          ),
          child: ListTile(
            title: Text(f['name'] ?? '', style: const TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w500)),
            subtitle: Text('${f['code']}  ${f['type'] ?? ''}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
            trailing: const Icon(Icons.analytics, color: AppTheme.accent),
            onTap: () => _analyze(f['code']),
          ),
        );
      },
    );
  }

  Widget _buildAnalysisPanel() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 返回按钮
          TextButton.icon(
            onPressed: () => setState(() {
              _selectedCode = null;
              _signal = null;
              _backtest = null;
            }),
            icon: const Icon(Icons.arrow_back, color: AppTheme.accent),
            label: const Text('返回搜索', style: TextStyle(color: AppTheme.accent)),
          ),

          const SizedBox(height: 8),

          if (_loadingSignal)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(40),
                child: CircularProgressIndicator(color: AppTheme.primary),
              ),
            )
          else ...[
            // 信号卡片
            if (_signal != null) _buildSignalCard(),
            const SizedBox(height: 16),

            // 回测结果
            if (_backtest != null) _buildBacktestCard(),
          ],
        ],
      ),
    );
  }

  Widget _buildSignalCard() {
    final s = _signal!;
    final signalColor = AppTheme.signalColor(s['type'] ?? 'wait');
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            signalColor.withOpacity(0.1),
            signalColor.withOpacity(0.05),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: signalColor.withOpacity(0.3), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: signalColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${s['signal'] ?? ''}',
                  style: TextStyle(
                    color: signalColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildInfoRow('最新价', '${s['price'] ?? ''}'),
          _buildInfoRow('MA10', '${s['ma10'] ?? ''}'),
          _buildInfoRow('MA60', '${s['ma60'] ?? ''}'),
          _buildInfoRow('量比', '${s['vol_ratio'] ?? ''}'),
          _buildInfoRow('PE评级', '${s['pe_rating'] ?? 'N/A'}', valueColor: _ratingColor(s['pe_rating'])),
          _buildInfoRow('PB评级', '${s['pb_rating'] ?? 'N/A'}', valueColor: _ratingColor(s['pb_rating'])),
          const SizedBox(height: 8),
          Text('${s['detail'] ?? ''}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14)),
          const Spacer(),
          Text(value, style: TextStyle(color: valueColor ?? AppTheme.textPrimary, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Color? _ratingColor(String? rating) {
    if (rating == null) return null;
    if (rating.contains('低估')) return AppTheme.green;
    if (rating.contains('高估')) return AppTheme.red;
    if (rating.contains('中性')) return AppTheme.yellow;
    return null;
  }

  Widget _buildBacktestCard() {
    final bt = _backtest!;
    if (bt.containsKey('error')) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.bgCard,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text('${bt['error']}', style: const TextStyle(color: AppTheme.textSecondary)),
      );
    }

    final metrics = bt['metrics'] as Map<String, dynamic>? ?? {};
    final trades = bt['trades'] as List<dynamic>? ?? [];

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.history, color: AppTheme.accent, size: 20),
              const SizedBox(width: 8),
              const Text('历史回测', style: TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 16),
          if (metrics['total_trades'] == 0)
            const Text('回测期间无完整交易信号', style: TextStyle(color: AppTheme.textSecondary))
          else ...[
            _buildMetricRow('总交易次数', '${metrics['total_trades']}'),
            _buildMetricRow('胜率', '${metrics['win_rate'] ?? '-'}%'),
            _buildMetricRow('平均盈利', '${metrics['avg_win'] ?? '-'}%', valueColor: AppTheme.green),
            _buildMetricRow('平均亏损', '${metrics['avg_loss'] ?? '-'}%', valueColor: AppTheme.red),
            _buildMetricRow('盈亏比', '${metrics['profit_loss_ratio'] ?? '-'}'),
            _buildMetricRow('总收益', '${metrics['total_return'] ?? '-'}%',
                valueColor: (metrics['total_return'] as num? ?? 0) >= 0 ? AppTheme.green : AppTheme.red),
            _buildMetricRow('最大回撤', '${metrics['max_drawdown'] ?? '-'}%', valueColor: AppTheme.red),
          ],
          if (trades.isNotEmpty) ...[
            const SizedBox(height: 16),
            const Text('最近交易', style: TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            ...trades.reversed.take(5).map((t) => Container(
              margin: const EdgeInsets.only(bottom: 4),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.bgCardAlt,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Text('${t['entry_date']} → ${t['exit_date']}', style: const TextStyle(color: AppTheme.textSecondary, fontSize: 12)),
                  const Spacer(),
                  Text(
                    '${(t['return'] as num?)?.toStringAsFixed(2) ?? '-'}%',
                    style: TextStyle(
                      color: (t['return'] as num? ?? 0) >= 0 ? AppTheme.green : AppTheme.red,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            )),
          ],
        ],
      ),
    );
  }

  Widget _buildMetricRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
          const Spacer(),
          Text(value, style: TextStyle(
            color: valueColor ?? AppTheme.textPrimary,
            fontWeight: FontWeight.w600,
            fontSize: 14,
          )),
        ],
      ),
    );
  }
}
