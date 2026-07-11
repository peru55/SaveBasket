import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/config/api_config.dart';

void main() {
  group('ApiConfig.resolveOrigin', () {
    test('normalizes an injected production origin', () {
      expect(
        ApiConfig.resolveOrigin(
          configured: 'https://api.example.com/',
          isWeb: true,
          isAndroid: false,
          isRelease: true,
        ),
        'https://api.example.com',
      );
    });

    test('uses localhost for web development', () {
      expect(
        ApiConfig.resolveOrigin(
          configured: '',
          isWeb: true,
          isAndroid: false,
          isRelease: false,
        ),
        'http://localhost:8000',
      );
    });

    test('uses the emulator host for Android development', () {
      expect(
        ApiConfig.resolveOrigin(
          configured: '',
          isWeb: false,
          isAndroid: true,
          isRelease: false,
        ),
        'http://10.0.2.2:8000',
      );
    });

    test('rejects a release build without an injected origin', () {
      expect(
        () => ApiConfig.resolveOrigin(
          configured: '',
          isWeb: true,
          isAndroid: false,
          isRelease: true,
        ),
        throwsStateError,
      );
    });

    test('rejects a non-HTTPS production origin', () {
      expect(
        () => ApiConfig.resolveOrigin(
          configured: 'http://api.example.com',
          isWeb: true,
          isAndroid: false,
          isRelease: true,
        ),
        throwsArgumentError,
      );
    });
  });
}
