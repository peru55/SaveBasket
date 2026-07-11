import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb, kReleaseMode;

class ApiConfig {
  static const String _configuredOrigin =
      String.fromEnvironment('API_BASE_URL');

  /// Production builds must provide:
  /// `--dart-define=API_BASE_URL=https://api.example.com`
  static String get origin => resolveOrigin(
        configured: _configuredOrigin,
        isWeb: kIsWeb,
        isAndroid: _isAndroid,
        isRelease: kReleaseMode,
      );

  static String get apiBaseUrl => '$origin/api';

  static bool get _isAndroid {
    if (kIsWeb) return false;
    return Platform.isAndroid;
  }

  static String resolveOrigin({
    required String configured,
    required bool isWeb,
    required bool isAndroid,
    required bool isRelease,
  }) {
    final normalized = configured.trim().replaceAll(RegExp(r'/+$'), '');
    if (normalized.isNotEmpty) {
      final uri = Uri.tryParse(normalized);
      if (isRelease &&
          (uri == null || uri.scheme != 'https' || uri.host.isEmpty)) {
        throw ArgumentError.value(
          configured,
          'API_BASE_URL',
          'Release API_BASE_URL must be a valid HTTPS origin',
        );
      }
      return normalized;
    }

    if (isRelease) {
      throw StateError(
        'Release builds require --dart-define=API_BASE_URL=https://api.example.com',
      );
    }
    if (isAndroid) return _developmentOrigin('10.0.2.2');
    if (isWeb) return _developmentOrigin('localhost');
    return _developmentOrigin('localhost');
  }

  static String _developmentOrigin(String host) =>
      Uri(scheme: 'http', host: host, port: 8000)
          .toString()
          .replaceAll(RegExp(r'/+$'), '');
}
