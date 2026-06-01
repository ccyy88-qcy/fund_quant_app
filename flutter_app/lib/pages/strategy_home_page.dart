import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'strategy_page.dart';
import 'portfolio_page.dart';

class StrategyHomePage extends StatefulWidget {
  const StrategyHomePage({super.key});

  @override
  State<StrategyHomePage> createState() => _StrategyHomePageState();
}

class _StrategyHomePageState extends State<StrategyHomePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('策略中心'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: '策略回测'),
            Tab(text: '资产配置'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          StrategyPage(),
          PortfolioPage(),
        ],
      ),
    );
  }
}
