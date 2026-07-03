import 'package:flutter/material.dart';

class AppColors {
  static const ink = Color(0xFF17201A);
  static const muted = Color(0xFF66736B);
  static const line = Color(0xFFE2E8E3);
  static const canvas = Color(0xFFF6F7F2);
  static const card = Color(0xFFFFFFFF);
  static const green = Color(0xFF168A4A);
  static const deepGreen = Color(0xFF0F3D2E);
  static const mint = Color(0xFFE5F4EA);
  static const lime = Color(0xFFC7F25C);
  static const amber = Color(0xFFEAA321);
  static const amberSoft = Color(0xFFFFF3D7);
  static const coral = Color(0xFFE95D45);
}

class AppRadii {
  static const small = 10.0;
  static const medium = 14.0;
  static const large = 20.0;
}

class AppTheme {
  static ThemeData get light {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.green,
      primary: AppColors.green,
      secondary: AppColors.deepGreen,
      surface: AppColors.card,
      brightness: Brightness.light,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.canvas,
      fontFamily: 'Inter',
      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontSize: 30, height: 1.05, fontWeight: FontWeight.w800, color: AppColors.ink),
        headlineMedium: TextStyle(fontSize: 22, height: 1.15, fontWeight: FontWeight.w800, color: AppColors.ink),
        titleLarge: TextStyle(fontSize: 18, height: 1.2, fontWeight: FontWeight.w800, color: AppColors.ink),
        titleMedium: TextStyle(fontSize: 15, height: 1.25, fontWeight: FontWeight.w700, color: AppColors.ink),
        bodyLarge: TextStyle(fontSize: 15, height: 1.45, color: AppColors.ink),
        bodyMedium: TextStyle(fontSize: 13, height: 1.35, color: AppColors.muted),
        labelLarge: TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: AppColors.canvas,
        foregroundColor: AppColors.ink,
        surfaceTintColor: Colors.transparent,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.deepGreen,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadii.medium)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        hintStyle: const TextStyle(color: AppColors.muted),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.medium),
          borderSide: const BorderSide(color: AppColors.green, width: 1.5),
        ),
      ),
    );
  }
}

class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color color;
  final Border? border;

  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.color = AppColors.card,
    this.border,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(AppRadii.large),
        border: border ?? Border.all(color: AppColors.line),
        boxShadow: [
          BoxShadow(
            color: AppColors.ink.withOpacity(0.04),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}
