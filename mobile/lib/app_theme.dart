import 'package:flutter/material.dart';

class MediFuelColors {
  static const navy = Color(0xFF102F60);
  static const navyDeep = Color(0xFF0B2348);
  static const orange = Color(0xFFCD4A12);
  static const blue = Color(0xFF2D68B2);
  static const canvas = Color(0xFFF4F6FA);
  static const ink = Color(0xFF17263D);
  static const muted = Color(0xFF68768A);
  static const line = Color(0xFFE1E6ED);
  static const green = Color(0xFF267451);
  static const red = Color(0xFFB43C35);
  static const amber = Color(0xFFFFF0D2);
}

ThemeData buildMediFuelTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: MediFuelColors.navy,
    primary: MediFuelColors.navy,
    secondary: MediFuelColors.orange,
    surface: Colors.white,
    error: MediFuelColors.red,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: MediFuelColors.canvas,
    appBarTheme: const AppBarTheme(
      backgroundColor: MediFuelColors.navy,
      foregroundColor: Colors.white,
      centerTitle: false,
      elevation: 0,
    ),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(fontSize: 29, height: 1.12, fontWeight: FontWeight.w800, color: MediFuelColors.ink),
      headlineMedium: TextStyle(fontSize: 23, height: 1.2, fontWeight: FontWeight.w700, color: MediFuelColors.ink),
      titleLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: MediFuelColors.ink),
      titleMedium: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: MediFuelColors.ink),
      bodyLarge: TextStyle(fontSize: 15, height: 1.45, color: MediFuelColors.ink),
      bodyMedium: TextStyle(fontSize: 13, height: 1.4, color: MediFuelColors.muted),
      labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      hintStyle: const TextStyle(color: MediFuelColors.muted),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: MediFuelColors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: MediFuelColors.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: MediFuelColors.navy, width: 1.6),
      ),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: MediFuelColors.line),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: const Color(0xFFE8EEF8),
      labelTextStyle: WidgetStateProperty.resolveWith((states) => TextStyle(
            fontSize: 11,
            fontWeight: states.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
          )),
    ),
  );
}