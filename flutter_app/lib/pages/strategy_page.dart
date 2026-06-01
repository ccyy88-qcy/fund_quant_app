import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class StrategyPage extends StatefulWidget {
  const StrategyPage({super.key});

  @override
  State<StrategyPage> createState() => _StrategyPageState();
}

class _StrategyPageState extends State<StrategyPage> {
  final _api = ApiService();
  final _codeController = TextEditingController(text: '000001');
  final _paramsController = TextEditingController(text: '{}');

  String _selectedStrategy = 'ma_cross';
  bool _loadingBacktest = false;
  Map<String, dynamic>? _backtestResult;

  final List<Map<String, String>> _strategies = [
    {'value': 'ma_cross', 'label': '均线交叉', 'desc': '短期均线上穿/下穿长期均线'},
    {'value': 'bollinger', 'label': '布林带', 'desc': '价格突破布林带上下轨'},
    {'value': 'rsi', 'label': 'RSI超买超卖', 'desc': 'RSI进入超买(<30)/超卖(>70)区域'},
    {'value': 'macd', 'label': 'MACD金叉死叉', 'desc': 'MACD快慢线金叉/死叉信号'},
    {'value': 'momentum', 'label': '动量策略', 'desc': 'N日收益率动量排序轮动'},
  ];

  @override
  void dispose() {
    _codeController.dispose();
    _paramsController.dispose();
    super.dispose();
  }

  Future<void> _runBacktest() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      _showError('请输入基金代码');
      return;
    }

    Map<String, dynamic> params;
    try {
      params = Map<String, dynamic>.from(
          const JsonDecoder().convert(_paramsController.text.trim()));
    } catch (_) {
      _showError('参数格式错误，请使用JSON格式');
      return;
    }

    setState(() {
      _loadingBacktest = true;
      _backtestResult = null;
    });

    try {
      final result =
          await _api.customBacktest(code, _selectedStrategy, params);
      if (!mounted) return;
      setState(() {
        _backtestResult = result;
        _loadingBacktest = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingBacktest = false);
      _showError('$e');
    }
  }

  void _showError(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: AppTheme.red,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Map<String, dynamic> _defaultParams() {
    switch (_selectedStrategy) {
      case 'ma_cross':
        return {'short_period': 5, 'long_period': 20};
      case 'bollinger':
        return {'period': 20, 'std_dev': 2};
      case 'rsi':
        return {'period': 14, 'oversold': 30, 'overbought': 70};
      case 'macd':
        return {'fast_period': 12, 'slow_period': 26, 'signal_period': 9};
      case 'momentum':
        return {'lookback': 20};
      default:
        return {};
    }
  }

  void _applyDefaultParams() {
    _paramsController.text = const JsonEncoder.withIndent('  ')
        .convert(_defaultParams());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('策略回测')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 参数配置
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
                  const Text('回测参数',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _codeController,
                    decoration: const InputDecoration(
                      labelText: '基金代码',
                      prefixIcon:
                          Icon(Icons.code, color: AppTheme.accent),
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _selectedStrategy,
                    decoration: const InputDecoration(
                      labelText: '策略类型',
                      prefixIcon:
                          Icon(Icons.psychology, color: AppTheme.accent),
                    ),
                    items: _strategies
                        .map((s) => DropdownMenuItem(
                              value: s['value'],
                              child: Column(
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
                                children: [
                                  Text(s['label']!,
                                      style: const TextStyle(
                                          color: AppTheme.textPrimary)),
                                  Text(s['desc']!,
                                      style: const TextStyle(
                                          color: AppTheme.textSecondary,
                                          fontSize: 11)),
                                ],
                              ),
                            ))
                        .toList(),
                    onChanged: (v) {
                      if (v != null) {
                        setState(() => _selectedStrategy = v);
                        _applyDefaultParams();
                      }
                    },
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _paramsController,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: '策略参数 (JSON)',
                      prefixIcon: Icon(Icons.tune, color: AppTheme.accent),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: _applyDefaultParams,
                      icon: const Icon(Icons.restore, size: 16),
                      label: const Text('恢复默认参数'),
                      style: TextButton.styleFrom(
                          foregroundColor: AppTheme.accent),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _runBacktest,
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
            // 结果
            _buildResult(),
          ],
        ),
      ),
    );
  }

  Widget _buildResult() {
    if (_loadingBacktest) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: CircularProgressIndicator(color: AppTheme.primary),
        ),
      );
    }
    if (_backtestResult == null) {
      return const SizedBox.shrink();
    }

    final bt = _backtestResult!;
    if (bt.containsKey('error')) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.red.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border:
              Border.all(color: AppTheme.red.withOpacity(0.3), width: 0.5),
        ),
        child: Row(
          children: [
            const Icon(Icons.error, color: AppTheme.red),
            const SizedBox(width: 8),
            Expanded(
                child: Text('${bt['error']}',
                    style:
                        const TextStyle(color: AppTheme.textSecondary))),
          ],
        ),
      );
    }

    final metrics = bt['metrics'] as Map<String, dynamic>? ?? {};
    final trades = bt['trades'] as List<dynamic>? ?? [];

    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0x1A8B5CF6), Color(0x0D00D4FF)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: AppTheme.primary.withOpacity(0.3), width: 0.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.history, color: AppTheme.accent, size: 20),
                  SizedBox(width: 8),
                  Text('策略回测结果',
                      style: TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600)),
                ],
              ),
              const SizedBox(height: 16),
              if (metrics.isEmpty)
                const Text('回测无结果',
                    style: TextStyle(color: AppTheme.textSecondary))
              else
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
                                  fontWeight: FontWeight.w600)),
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
                            child: Text(
                              '${t['entry_date'] ?? '-'} → ${t['exit_date'] ?? '-'}',
                              style: const TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 12),
                            ),
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
