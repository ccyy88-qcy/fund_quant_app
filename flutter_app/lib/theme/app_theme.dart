import 'package:flutter/material.dart';

class AppTheme {
  // 霓虹紫蓝配色
  static const Color primary = Color(0xFF8B5CF6);      // 霓虹紫
  static const Color accent = Color(0xFF00D4FF);        // 霓虹蓝
  static const Color bgDark = Color(0xFF0A0A1A);        // 深黑背景
  static const Color bgCard = Color(0xFF12122A);        // 卡片背景
  static const Color bgCardAlt = Color(0xFF1A1A3E);     // 备用卡片
  static const Color textPrimary = Color(0xFFE8E8F0);   // 主文字
  static const Color textSecondary = Color(0xFF9898B0); // 次文字
  static const Color green = Color(0xFF4CAF50);         // 涨
  static const Color red = Color(0xFFF44336);           // 跌
  static const Color yellow = Color(0xFFFF9800);        // 持有
  static const Color grey = Color(0xFF9E9E9E);          // 观望

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgDark,
      primaryColor: primary,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: accent,
        surface: bgCard,
        onPrimary: Colors.white,
        onSecondary: Colors.black,
        onSurface: textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: bgDark,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
        iconTheme: IconThemeData(color: accent),
      ),
      cardTheme: CardTheme(
        color: AppTheme.bgCard,
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0x338B5CF6), width: 0.5),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Color(0xFF0D0D20),
        selectedItemColor: accent,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(color: textPrimary, fontSize: 28, fontWeight: FontWeight.bold),
        headlineMedium: TextStyle(color: textPrimary, fontSize: 22, fontWeight: FontWeight.w600),
        titleLarge: TextStyle(color: textPrimary, fontSize: 18, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: textPrimary, fontSize: 16, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(color: textPrimary, fontSize: 16),
        bodyMedium: TextStyle(color: textSecondary, fontSize: 14),
        labelLarge: TextStyle(color: accent, fontSize: 14, fontWeight: FontWeight.w600),
      ),
      dividerTheme: const DividerThemeData(
        color: Color(0x1A9898B0),
        thickness: 0.5,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: bgCard,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x338B5CF6)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0x338B5CF6)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: accent, width: 1.5),
        ),
        hintStyle: const TextStyle(color: textSecondary),
      ),
    );
  }

  // 涨跌颜色
  static Color changeColor(double change) {
    if (change > 0) return green;
    if (change < 0) return red;
    return textSecondary;
  }

  // 信号类型颜色
  static Color signalColor(String type) {
    switch (type) {
      case 'buy':
        return green;
      case 'sell':
        return red;
      case 'hold':
        return yellow;
      case 'wait':
      default:
        return grey;
    }
  }

  // 霓虹渐变
  static const LinearGradient neonGradient = LinearGradient(
    colors: [primary, accent],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // 玻璃态效果
  static BoxDecoration glassDecoration({
    double opacity = 0.15,
    double blur = 20,
  }) {
    return BoxDecoration(
      gradient: LinearGradient(
        colors: [
          Colors.white.withOpacity(opacity),
          Colors.white.withOpacity(opacity * 0.3),
        ],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      borderRadius: BorderRadius.circular(16),
    );
  }
}
