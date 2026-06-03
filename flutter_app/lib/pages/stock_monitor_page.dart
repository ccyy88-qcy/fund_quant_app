import 'package:flutter/material.dart';
import '../services/api_service.dart';

class StockMonitorPage extends StatefulWidget {
  const StockMonitorPage({super.key});
  @override
  State<StockMonitorPage> createState() => _StockMonitorPageState();
}

class _StockMonitorPageState extends State<StockMonitorPage> {
  final _api = ApiService();
  List<dynamic> _stocks = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    try {
      final data = await _api.getMonitorStocks();
      setState(() {
        _stocks = data['stocks'] as List<dynamic>? ?? [];
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('股票监控')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _stocks.length,
              itemBuilder: (_, i) {
                final s = _stocks[i];
                final q = s['quote'] as Map<String, dynamic>? ?? {};
                return ListTile(
                  title: Text('${s['name'] ?? ""}'),
                  subtitle: Text('${q['price'] ?? "-"}'),
                );
              },
            ),
    );
  }
}
