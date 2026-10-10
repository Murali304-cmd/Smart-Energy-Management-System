import 'package:flutter/material.dart';
import 'localization.dart';

class AppColors {
  static const Color primary = Color(0xFF0284C7);
  static const Color solar = Color(0xFFF59E0B);
  static const Color battery = Color(0xFF10B981);
  static const Color grid = Color(0xFF8B5CF6);
  static const Color danger = Color(0xFFEF4444);
}

class AppTheme {
  // Brand Colors
  static const Color primaryBlue = Color(0xFF0284C7);
  static const Color solarAmber = Color(0xFFF59E0B);
  static const Color batteryGreen = Color(0xFF10B981);
  static const Color gridViolet = Color(0xFF8B5CF6);
  static const Color dangerRed = Color(0xFFEF4444);
  static const Color bgDark = Color(0xFF0F172A);
  static const Color cardDark = Color(0xFF1E293B);

  // Elder High-Contrast Colors
  static const Color elderBg = Color(0xFFFFFFFF);
  static const Color elderCard = Color(0xFFF1F5F9);
  static const Color elderText = Color(0xFF000000);
  static const Color elderBorder = Color(0xFF334155);

  static ThemeData getTheme({
    required bool isDark,
    required UserAgeMode ageMode,
  }) {
    if (ageMode == UserAgeMode.elder) {
      // High-accessibility Elder Mode (Large text, high contrast, clean buttons)
      return ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        colorScheme: const ColorScheme.light(
          primary: Color(0xFF0369A1),
          secondary: Color(0xFFD97706),
          surface: Colors.white,
          error: dangerRed,
        ),
        cardTheme: CardThemeData(
          color: Colors.white,
          elevation: 3,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: Color(0xFF94A3B8), width: 1.5),
          ),
          margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        ),
        textTheme: const TextTheme(
          headlineLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: Colors.black, height: 1.2),
          headlineMedium: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: Colors.black, height: 1.2),
          titleLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colors.black),
          titleMedium: TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
          bodyLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.black),
          bodyMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w500, color: Color(0xFF1E293B)),
          labelLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Colors.white),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF0284C7),
            foregroundColor: Colors.white,
            minimumSize: const Size(double.infinity, 60),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
        ),
      );
    }

    // Modern / Youth Mode (Sleek dark or light with modern styling)
    if (isDark) {
      return ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: bgDark,
        colorScheme: const ColorScheme.dark(
          primary: primaryBlue,
          secondary: solarAmber,
          surface: cardDark,
          error: dangerRed,
        ),
        cardTheme: CardThemeData(
          color: cardDark,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: const BorderSide(color: Color(0xFF334155), width: 1),
          ),
          margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        ),
        textTheme: const TextTheme(
          headlineLarge: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, color: Colors.white),
          headlineMedium: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Colors.white),
          titleLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Colors.white),
          titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE2E8F0)),
          bodyLarge: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: Color(0xFFCBD5E1)),
          bodyMedium: TextStyle(fontSize: 13, fontWeight: FontWeight.w400, color: Color(0xFF94A3B8)),
        ),
      );
    } else {
      return ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        colorScheme: const ColorScheme.light(
          primary: primaryBlue,
          secondary: solarAmber,
          surface: Colors.white,
          error: dangerRed,
        ),
        cardTheme: CardThemeData(
          color: Colors.white,
          elevation: 1,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: const BorderSide(color: Color(0xFFE2E8F0), width: 1),
          ),
          margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        ),
      );
    }
  }
}
