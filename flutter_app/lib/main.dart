import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'pages/dashboard_page.dart';
import 'pages/quant_page.dart';
import 'pages/kline_page.dart';
import 'pages/settings_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  ApiService().init();
  runApp(const FundQuantApp());
}

class FundQuantApp extends StatelessWidget {
  const FundQuantApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppState()),
      ],
      child: MaterialApp(
        title: '基金量化工具',
        theme: AppTheme.darkTheme,
        debugShowCheckedModeBanner: false,
        home: const MainShell(),
      ),
    );
  }
}

class AppState extends ChangeNotifier {
  List<String> _watchlist = [];
  List<String> get watchlist => _watchlist;

  void setWatchlist(List<String> codes) {
    _watchlist = codes;
    notifyListeners();
  }

  void addWatchlist(String code) {
    if (!_watchlist.contains(code)) {
      _watchlist.add(code);
      notifyListeners();
      ApiService().setWatchlist(_watchlist);
    }
  }

  void removeWatchlist(String code) {
    _watchlist.remove(code);
    notifyListeners();
    ApiService().setWatchlist(_watchlist);
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  final _pages = const [
    DashboardPage(),
    QuantPage(),
    KlinePage(),
    SettingsPage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_currentIndex],
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (i) => setState(() => _currentIndex = i),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_outlined),
              activeIcon: Icon(Icons.dashboard),
              label: '仪表盘',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.analytics_outlined),
              activeIcon: Icon(Icons.analytics),
              label: '量化回测',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.show_chart_outlined),
              activeIcon: Icon(Icons.show_chart),
              label: 'K线分析',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings_outlined),
              activeIcon: Icon(Icons.settings),
              label: '设置',
            ),
          ],
        ),
      ),
    );
  }
}
