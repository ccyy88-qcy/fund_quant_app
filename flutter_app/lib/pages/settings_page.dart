import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _hostController = TextEditingController();
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _hostController.text = ApiService().baseUrl;
  }

  @override
  void dispose() {
    _hostController.dispose();
    super.dispose();
  }

  Future<void> _saveHost() async {
    final url = _hostController.text.trim();
    if (url.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_host', url);
    ApiService().updateBaseUrl(url);
    setState(() => _saved = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _saved = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 服务器配置
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.dns, color: AppTheme.accent),
                    SizedBox(width: 8),
                    Text('服务器配置', style: TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 8),
                const Text('输入Termux后端的IP地址', style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                const SizedBox(height: 12),
                TextField(
                  controller: _hostController,
                  decoration: InputDecoration(
                    hintText: 'http://192.168.1.100:8000',
                    prefixIcon: const Icon(Icons.link, color: AppTheme.accent, size: 20),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _saveHost,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: Text(
                      _saved ? '✅ 已保存' : '保存',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // 关于
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info_outline, color: AppTheme.accent),
                    SizedBox(width: 8),
                    Text('关于', style: TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
                  ],
                ),
                SizedBox(height: 12),
                Text('基金全量化工具 v1.0.0', style: TextStyle(color: AppTheme.textPrimary)),
                SizedBox(height: 4),
                Text('后端: Python FastAPI + akshare + pandas', style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                SizedBox(height: 4),
                Text('前端: Flutter + fl_chart', style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                SizedBox(height: 4),
                Text('功能: 量化回测 / MA10+MA60信号 / K线技术指标 / 行业轮动', style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // 快速启动指南
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [AppTheme.primary.withOpacity(0.08), AppTheme.accent.withOpacity(0.08)],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.primary.withOpacity(0.2), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.terminal, color: AppTheme.accent),
                    SizedBox(width: 8),
                    Text('Termux后端启动', style: TextStyle(color: AppTheme.textPrimary, fontSize: 16, fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 12),
                _buildCodeBlock('cd ~/fund_quant_app/backend && python3 main.py'),
                const SizedBox(height: 12),
                const Text('后端启动后，在本页设置中输入Termux的IP地址', style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCodeBlock(String code) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black87,
        borderRadius: BorderRadius.circular(8),
      ),
      child: SelectableText(
        code,
        style: const TextStyle(
          color: Color(0xFF00FF88),
          fontFamily: 'monospace',
          fontSize: 13,
        ),
      ),
    );
  }
}
