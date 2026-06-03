import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class StockMonitorPage extends StatefulWidget {
  const StockMonitorPage({super.key});

  @override
  State<StockMonitorPage> createState() => _StockMonitorPageState();
}

class _StockMonitorPageState extends State<StockMonitorPage> {
  final _api = ApiService();
  List<dynamic> _stocks = [];
  bool _loading = true;
  String _error = '';
  int _counter = 0;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    setState(() => _loading = true);
    try {
      final data = await _api.getMonitorStocks();
      if (data.containsKey('stocks')) {
        setState(() {
          _stocks = data['stocks'] as List<dynamic>;
          _loading = false;
          _error = '';
          _counter++;
        });
      } else {
        setState(() {
          _loading = false;
          _error = '无数据返回';
        });
      }
    } catch (e) {
      setState(() {
        _loading = false;
        _error = '请求失败: $e';
      });
    }
  }

  String _fmt(dynamic v, {int dec = 2}) {
    if (v == null) return '-';
    return v.toStringAsFixed(dec);
  }

  Color _color(double v) => v >= 0 ? const Color(0xFFF44336) : const Color(0xFF4CAF50);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0D14),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1723),
        title: const Text('股票实时监控',
            style: TextStyle(color: Color(0xFF7B6FE0), fontWeight: FontWeight.w600)),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF7B6FE0)),
            onPressed: _fetchData,
          ),
          Text(' ${_counter > 0 ? "$_counter" : ""}',
              style: const TextStyle(color: Color(0xFF5BB5D8), fontSize: 12)),
          const SizedBox(width: 8),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF7B6FE0)))
          : _error.isNotEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.cloud_off, color: Color(0xFF5BB5D8), size: 48),
                      const SizedBox(height: 12),
                      Text(_error, style: const TextStyle(color: Color(0xFF888888))),
                      const SizedBox(height: 16),
                      ElevatedButton(onPressed: _fetchData, child: const Text('重试')),
                    ],
                  ),
                )
              : RefreshIndicator(
                  color: const Color(0xFF7B6FE0),
                  onRefresh: _fetchData,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: _stocks.length,
                    itemBuilder: (ctx, i) => _StockCard(
                      stock: _stocks[i],
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => _StockDetailPage(stock: _stocks[i]),
                        ),
                      ),
                    ),
                  ),
                ),
    );
  }
}

class _StockCard extends StatelessWidget {
  final dynamic stock;
  final VoidCallback onTap;

  const _StockCard({required this.stock, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final q = stock['quote'] as Map<String, dynamic>? ?? {};
    final t = stock['technical'] as Map<String, dynamic>?;
    final f = stock['flow'] as Map<String, dynamic>?;
    final name = stock['name'] ?? '';
    final price = (q['price'] as num?)?.toDouble() ?? 0;
    final chgPct = (q['change_pct'] as num?)?.toDouble() ?? 0;
    final chgAmt = (q['change_amt'] as num?)?.toDouble() ?? 0;
    final vol = (q['volume'] as num?)?.toDouble() ?? 0;
    final amt = (q['amount'] as num?)?.toDouble() ?? 0;
    final time = q['time']?.toString() ?? '';
    final c = chgPct >= 0 ? const Color(0xFFF44336) : const Color(0xFF4CAF50);

    return Card(
      color: const Color(0xFF1A1723),
      margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(name,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
                  ),
                  Text('$price',
                      style: TextStyle(
                          color: c, fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: c.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text('${chgPct >= 0 ? "+" : ""}${chgPct.toStringAsFixed(2)}%',
                        style: TextStyle(color: c, fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  _InfoChip('涨跌', '${chgAmt >= 0 ? "+" : ""}${chgAmt.toStringAsFixed(2)}', c),
                  _InfoChip('量', _fmt(vol / 10000, dec: 0) + '万', const Color(0xFF5BB5D8)),
                  _InfoChip('额', _fmt(amt / 100000000, dec: 1) + '亿', const Color(0xFF5BB5D8)),
                  if (t != null) ...[
                    _InfoChip('MACD', t['macd']['trend'] ?? '-', const Color(0xFF7B6FE0)),
                    _InfoChip('RSI', _fmt(t['rsi'], dec: 1), const Color(0xFF5BB5D8)),
                  ],
                ],
              ),
              if (f != null) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    _FlowChip('主力', _fmt(f['main_force']! / 10000, dec: 0) + '万',
                        (f['main_force'] as num).toDouble()),
                    _FlowChip('特大单', _fmt(f['super_large']! / 10000, dec: 0) + '万',
                        (f['super_large'] as num).toDouble()),
                    _FlowChip('增仓', _fmt(f['main_ratio'], dec: 1) + '%',
                        (f['main_ratio'] as num).toDouble()),
                  ],
                ),
              ],
              if (time.isNotEmpty)
                Align(
                  alignment: Alignment.centerRight,
                  child: Text(time, style: const TextStyle(color: Color(0xFF555555), fontSize: 11)),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final String label, value;
  final Color color;
  const _InfoChip(this.label, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$label ',
              style: const TextStyle(color: Color(0xFF777777), fontSize: 11)),
          Text(value,
              style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _FlowChip extends StatelessWidget {
  final String label, value;
  final double numVal;
  const _FlowChip(this.label, this.value, this.numVal);

  @override
  Widget build(BuildContext context) {
    final c = numVal >= 0 ? const Color(0xFFF44336) : const Color(0xFF4CAF50);
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: c.withOpacity(0.1),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('$label ',
                style: const TextStyle(color: Color(0xFF888888), fontSize: 10)),
            Text(value,
                style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

// ─── 个股详情页 ───
class _StockDetailPage extends StatelessWidget {
  final dynamic stock;
  const _StockDetailPage({required this.stock});

  @override
  Widget build(BuildContext context) {
    final q = stock['quote'] as Map<String, dynamic>? ?? {};
    final t = stock['technical'] as Map<String, dynamic>?;
    final f = stock['flow'] as Map<String, dynamic>?;
    final name = stock['name'] ?? '';
    final code = stock['code'] ?? '';
    final price = (q['price'] as num?)?.toDouble() ?? 0;
    final chgPct = (q['change_pct'] as num?)?.toDouble() ?? 0;
    final chgAmt = (q['change_amt'] as num?)?.toDouble() ?? 0;
    final open = (q['open'] as num?)?.toDouble() ?? 0;
    final high = (q['high'] as num?)?.toDouble() ?? 0;
    final low = (q['low'] as num?)?.toDouble() ?? 0;
    final yclose = (q['yclose'] as num?)?.toDouble() ?? 0;
    final vol = (q['volume'] as num?)?.toDouble() ?? 0;
    final amt = (q['amount'] as num?)?.toDouble() ?? 0;
    final turnRate = (q['turnover_rate'] as num?)?.toDouble() ?? 0;
    final pe = (q['pe'] as num?)?.toDouble() ?? 0;
    final c = chgPct >= 0 ? const Color(0xFFF44336) : const Color(0xFF4CAF50);

    return Scaffold(
      backgroundColor: const Color(0xFF0F0D14),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1723),
        title: Text('$name  $code',
            style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          // 价格大卡片
          Card(
            color: const Color(0xFF1A1723),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Text('$price',
                      style: TextStyle(color: c, fontSize: 40, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('${chgAmt >= 0 ? "+" : ""}${chgAmt.toStringAsFixed(2)}',
                          style: TextStyle(color: c, fontSize: 18)),
                      const SizedBox(width: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: c.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text('${chgPct >= 0 ? "+" : ""}${chgPct.toStringAsFixed(2)}%',
                            style: TextStyle(color: c, fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _infoRow('今开', open.toStringAsFixed(2), '昨收', yclose.toStringAsFixed(2)),
                  const SizedBox(height: 6),
                  _infoRow('最高', high.toStringAsFixed(2), '最低', low.toStringAsFixed(2)),
                  const SizedBox(height: 6),
                  _infoRow('成交量', '${(vol / 10000).toStringAsFixed(0)}万手',
                      '成交额', '${(amt / 100000000).toStringAsFixed(2)}亿'),
                  const SizedBox(height: 6),
                  _infoRow('换手率', '${turnRate.toStringAsFixed(2)}%',
                      '市盈率', '${pe.toStringAsFixed(1)}倍'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),

          // 技术指标
          if (t != null) ...[
            _sectionTitle('技术指标'),
            Card(
              color: const Color(0xFF1A1723),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  children: [
                    _techRow('MA排列', t['ma_trend'] ?? '-', const Color(0xFF5BB5D8)),
                    const Divider(color: Color(0xFF333333), height: 12),
                    _techRow('MACD', t['macd']['trend'] ?? '-',
                        const Color(0xFF7B6FE0)),
                    _techRow('  DIF', (t['macd']['dif'] as num?)?.toStringAsFixed(4) ?? '-',
                        const Color(0xFF7B6FE0)),
                    _techRow('  DEA', (t['macd']['dea'] as num?)?.toStringAsFixed(4) ?? '-',
                        const Color(0xFF7B6FE0)),
                    _techRow('  柱', (t['macd']['macd'] as num?)?.toStringAsFixed(4) ?? '-',
                        const Color(0xFF7B6FE0)),
                    const Divider(color: Color(0xFF333333), height: 12),
                    _techRow('RSI(14)', (t['rsi'] as num?)?.toStringAsFixed(1) ?? '-',
                        const Color(0xFF5BB5D8)),
                    _techRow('KDJ', 'K:${t['kdj']['k']}  D:${t['kdj']['d']}  J:${t['kdj']['j']}',
                        const Color(0xFF5BB5D8)),
                    const Divider(color: Color(0xFF333333), height: 12),
                    _techRow('布林上轨', (t['boll']['upper'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                    _techRow('布林中轨', (t['boll']['mid'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                    _techRow('布林下轨', (t['boll']['lower'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                    const Divider(color: Color(0xFF333333), height: 12),
                    _techRow('MA5', (t['ma5'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                    _techRow('MA10', (t['ma10'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                    _techRow('MA20', (t['ma20'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                    _techRow('MA60', (t['ma60'] as num?)?.toStringAsFixed(2) ?? '-',
                        const Color(0xFF5BB5D8)),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 8),

          // 资金流向
          if (f != null) ...[
            _sectionTitle('资金流向'),
            Card(
              color: const Color(0xFF1A1723),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  children: [
                    _flowRow('主力净流入', f['main_force']),
                    _flowRow('特大单', f['super_large']),
                    _flowRow('大单', f['large']),
                    _flowRow('中单', f['medium']),
                    _flowRow('小单', f['small']),
                    const Divider(color: Color(0xFF333333), height: 12),
                    _techRow('主力增仓占比', '${(f['main_ratio'] as num?)?.toStringAsFixed(2) ?? "-"}%',
                        const Color(0xFF7B6FE0)),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _sectionTitle(String t) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 6, top: 4),
      child: Text(t,
          style: const TextStyle(
              color: Color(0xFF7B6FE0), fontSize: 14, fontWeight: FontWeight.w600)),
    );
  }

  Widget _infoRow(String l1, String v1, String l2, String v2) {
    return Row(
      children: [
        Expanded(
            child: Row(children: [
          Text('$l1 ', style: const TextStyle(color: Color(0xFF777777), fontSize: 13)),
          Text(v1, style: const TextStyle(color: Colors.white70, fontSize: 13)),
        ])),
        Expanded(
            child: Row(children: [
          Text('$l2 ', style: const TextStyle(color: Color(0xFF777777), fontSize: 13)),
          Text(v2, style: const TextStyle(color: Colors.white70, fontSize: 13)),
        ])),
      ],
    );
  }

  Widget _techRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 90,
            child: Text(label,
                style: const TextStyle(color: Color(0xFF777777), fontSize: 12)),
          ),
          Expanded(
            child: Text(value,
                style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }

  Widget _flowRow(String label, dynamic val) {
    final v = (val as num?)?.toDouble() ?? 0;
    final c = v >= 0 ? const Color(0xFFF44336) : const Color(0xFF4CAF50);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
            width: 90,
            child: Text(label,
                style: const TextStyle(color: Color(0xFF777777), fontSize: 12)),
          ),
          Text(
            '${v >= 0 ? "+" : ""}${(v / 10000).toStringAsFixed(0)}万',
            style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
