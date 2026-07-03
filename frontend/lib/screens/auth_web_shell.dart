import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class AuthWebShell extends StatelessWidget {
  static const backgroundAsset =
      'assets/app_images/splash_screen_background.png';

  final Widget child;

  const AuthWebShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: const BoxDecoration(color: Color(0xFFF7FAEF)),
              child: Image.asset(
                backgroundAsset,
                fit: BoxFit.contain,
                alignment: Alignment.centerLeft,
              ),
            ),
          ),
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [
                    Colors.white.withOpacity(0.04),
                    Colors.white.withOpacity(0.24),
                    Colors.white.withOpacity(0.72),
                  ],
                  stops: const [0.0, 0.48, 1.0],
                ),
              ),
            ),
          ),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final isNarrow = constraints.maxWidth < 760;
                return Align(
                  alignment:
                      isNarrow ? Alignment.center : Alignment.centerRight,
                  child: SingleChildScrollView(
                    padding: EdgeInsets.symmetric(
                      horizontal: isNarrow ? 20 : 72,
                      vertical: 28,
                    ),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 430),
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.92),
                          borderRadius: BorderRadius.circular(28),
                          border:
                              Border.all(color: Colors.white.withOpacity(0.72)),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.deepGreen.withOpacity(0.16),
                              blurRadius: 36,
                              offset: const Offset(0, 18),
                            ),
                          ],
                        ),
                        child: child,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
