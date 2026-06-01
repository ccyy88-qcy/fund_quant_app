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
  final _api = ApiService();
  bool _saved = false;
  Map<String, dynamic>? _sysStatus;
  bool _checking = false;
  bool _restarting = false;
  String? _statusError;

  @override
  void initState() {
    super.initState();
    _hostController.text = _api.baseUrl;
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
    _api.updateBaseUrl(url);
    setState(() => _saved = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _saved = false);
    });
  }

  Future<void> _checkStatus() async {
    setState(() {
      _checking = true;
      _statusError = null;
    });
    try {
      final status = await _api.getSystemStatus();
      if (!mounted) return;
      setState(() {
        _sysStatus = status;
        _checking = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusError = '连接失败:\n${e.toString()}';
        _sysStatus = null;
        _checking = false;
      });
    }
  }

  Future<void> _restartBackend() async {
    setState(() => _restarting = true);
    try {
      final result = await _api.restartBackend();
      if (!mounted) return;
      setState(() => _restarting = false);
      // 等待几秒再检查状态
      await Future.delayed(const Duration(seconds: 3));
      if (mounted) _checkStatus();
    } catch (e) {
      if (!mounted) return;
      setState(() => _restarting = false);
      // 重启后服务短暂不可用是正常的
      await Future.delayed(const Duration(seconds: 5));
      if (mounted) _checkStatus();
    }
  }

  String _formatUptime(int? seconds) {
    if (seconds == null) return '-';
    final h = seconds ~/ 3600;
    final m = (seconds % 3600) ~/ 60;
    final s = seconds % 60;
    if (h > 0) return '${h}时${m}分';
    if (m > 0) return '${m}分${s}秒';
    return '${s}秒';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── 后端管理面板 ──
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  (_sysStatus != null ? AppTheme.green : AppTheme.red)
                      .withOpacity(0.08),
                  AppTheme.bgCard,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: (_sysStatus != null ? AppTheme.green : AppTheme.red)
                    .withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _sysStatus != null
                            ? AppTheme.green
                            : AppTheme.red,
                        boxShadow: [
                          BoxShadow(
                            color: (_sysStatus != null
                                    ? AppTheme.green
                                    : AppTheme.red)
                                .withOpacity(0.5),
                            blurRadius: 8,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text('后端服务',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                    const Spacer(),
                    if (_checking)
                      const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: AppTheme.accent),
                      )
                    else
                      TextButton.icon(
                        onPressed: _checkStatus,
                        icon: const Icon(Icons.refresh, size: 16),
                        label: const Text('检测'),
                      ),
                  ],
                ),
                const SizedBox(height: 12),

                // 状态信息
                if (_statusError != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.red.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline,
                            color: AppTheme.red, size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(_statusError!,
                              style: const TextStyle(
                                  color: AppTheme.red, fontSize: 12)),
                        ),
                      ],
                    ),
                  ),
                ] else if (_sysStatus != null) ...[
                  _statusRow('运行状态', '🟢 正常运行中'),
                  _statusRow('进程PID', '${_sysStatus!['pid'] ?? '-'}'),
                  _statusRow(
                      '运行时长', _formatUptime(_sysStatus!['uptime_seconds'] as int?)),
                  _statusRow('Python版本', '${_sysStatus!['python_version'] ?? '-'}'),
                ] else ...[
                  const Text('未检测后端状态',
                      style: TextStyle(color: AppTheme.textSecondary)),
                ],

                const SizedBox(height: 12),

                // 操作按钮
                Row(
                  children: [
                    if (_sysStatus != null) ...[
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _restarting ? null : _restartBackend,
                          icon: _restarting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.refresh, size: 18),
                          label: Text(_restarting ? '重启中...' : '重启后端'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.accent.withOpacity(0.8),
                            foregroundColor: Colors.black,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                    ] else ...[
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _checking ? null : _checkStatus,
                          icon: const Icon(Icons.wifi_find, size: 18),
                          label: const Text('检测连接'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // ── 服务器配置 ──
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(16),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.dns, color: AppTheme.accent),
                    SizedBox(width: 8),
                    Text('服务器地址',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 8),
                const Text('输入Termux后端的IP地址（含http://和端口）',
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                const SizedBox(height: 12),
                TextField(
                  controller: _hostController,
                  decoration: const InputDecoration(
                    hintText: 'http://127.0.0.1:8000',
                    prefixIcon:
                        Icon(Icons.link, color: AppTheme.accent, size: 20),
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
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                    child: Text(
                      _saved ? '✅ 已保存' : '保存',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── 启动指引 ──
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.primary.withOpacity(0.08),
                  AppTheme.accent.withOpacity(0.08)
                ],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: AppTheme.primary.withOpacity(0.2), width: 0.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.terminal, color: AppTheme.accent),
                    SizedBox(width: 8),
                    Text('Termux手动启动',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                const SizedBox(height: 12),
                _buildCodeBlock('# 一键启动'),
                _buildCodeBlock('cd ~/fund_quant_app && bash start_backend.sh'),
                const SizedBox(height: 8),
                _buildCodeBlock('# 或直接运行'),
                _buildCodeBlock('cd ~/fund_quant_app/backend && python3 main.py'),
                const SizedBox(height: 12),
                const Text('保存服务器地址后点击"检测连接"，绿色圆点表示后端正常运行',
                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── 关于 ──
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppTheme.bgCard,
              borderRadius: BorderRadius.circular(16),
              border:
                  Border.all(color: const Color(0x338B5CF6), width: 0.5),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info_outline, color: AppTheme.accent),
                    SizedBox(width: 8),
                    Text('关于',
                        style: TextStyle(
                            color: AppTheme.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600)),
                  ],
                ),
                SizedBox(height: 12),
                Text('基金全量化工具 v3.0',
                    style: TextStyle(color: AppTheme.textPrimary)),
                SizedBox(height: 4),
                Text('后端: Python FastAPI + akshare + pandas + scipy',
                    style:
                        TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                SizedBox(height: 4),
                Text('前端: Flutter + fl_chart',
                    style:
                        TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
                SizedBox(height: 4),
                Text('功能: 建仓提醒/智能分析/多因子/行业轮动/波动率策略/资产配置/定投/风险分析',
                    style:
                        TextStyle(color: AppTheme.textSecondary, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label,
              style: const TextStyle(
                  color: AppTheme.textSecondary, fontSize: 13)),
          const Spacer(),
          Text(value,
              style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontWeight: FontWeight.w500,
                  fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildCodeBlock(String code) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.black87,
        borderRadius: BorderRadius.circular(6),
      ),
      child: SelectableText(
        code,
        style: const TextStyle(
          color: Color(0xFF00FF88),
          fontFamily: 'monospace',
          fontSize: 12,
        ),
      ),
    );
  }
}
