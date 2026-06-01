import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'quant_page.dart';
import 'factor_page.dart';
import 'rotation_page.dart';
import 'volatility_page.dart';
import 'risk_analysis_page.dart';

class QuantHomePage extends StatefulWidget {
  const QuantHomePage({super.key});

  @override
  State<QuantHomePage> createState() => _QuantHomePageState();
}

class _QuantHomePageState extends State<QuantHomePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
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
        title: const Text('量化分析'),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          indicatorColor: AppTheme.accent,
          labelColor: AppTheme.accent,
          unselectedLabelColor: AppTheme.textSecondary,
          tabs: const [
            Tab(text: '回测信号'),
            Tab(text: '多因子'),
            Tab(text: '行业轮动'),
            Tab(text: '波动率'),
            Tab(text: '风险分析'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          QuantPage(),
          FactorPage(),
          RotationPage(),
          VolatilityPage(),
          RiskAnalysisPage(),
        ],
      ),
    );
  }
}
