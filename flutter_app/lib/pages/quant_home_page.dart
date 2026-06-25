import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'quant_page.dart';
import 'factor_page.dart';
import 'rotation_page.dart';
import 'sector_month_page.dart';
import 'volatility_page.dart';
import 'risk_analysis_page.dart';
import 'build_signal_page.dart';
import 'analysis_report_page.dart';
import 'holding_analysis_page.dart';
import 'fund_detail_page.dart';

class QuantHomePage extends StatefulWidget {
  const QuantHomePage({super.key});

  @override
  State<QuantHomePage> createState() => _QuantHomePageState();
}

class _QuantHomePageState extends State<QuantHomePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // 基金详情页导航
  void _navigateToFundDetail(String code, String name) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => FundDetailPage(code: code, name: name),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 10, vsync: this);
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
            Tab(text: '🔥建仓提醒'),
            Tab(text: '🤖智能分析'),
            Tab(text: '⏱持有期'),
            Tab(text: '回测信号'),
            Tab(text: '多因子'),
            Tab(text: '行业轮动'),
            Tab(text: '📊行业涨跌'),
            Tab(text: '波动率'),
            Tab(text: '风险分析'),
            Tab(text: '基金详情'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          BuildSignalPage(),
          AnalysisReportPage(),
          HoldingAnalysisPage(),
          QuantPage(),
          FactorPage(),
          RotationPage(),
          SectorMonthPage(),
          VolatilityPage(),
          RiskAnalysisPage(),
          _FundDetailPlaceholder(),
        ],
      ),
    );
  }
}

/// 基金详情占位页 - 实际通过导航进入
class _FundDetailPlaceholder extends StatelessWidget {
  const _FundDetailPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.search, size: 48, color: AppTheme.textSecondary.withOpacity(0.4)),
          const SizedBox(height: 12),
          Text('搜索基金查看详情', style: TextStyle(color: AppTheme.textSecondary)),
          const SizedBox(height: 8),
          Text('在搜索页输入基金代码', style: TextStyle(color: AppTheme.textSecondary.withOpacity(0.6), fontSize: 12)),
        ],
      ),
    );
  }
}
