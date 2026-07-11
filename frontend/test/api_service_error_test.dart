import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/services/api_exception.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/auth_service.dart';

class _TestAuthService extends AuthService {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<bool> refreshToken() async => false;

  @override
  Future<void> clearTokens() async {}
}

void main() {
  ApiService serviceReturning(int statusCode) {
    final body = statusCode == 201
        ? jsonEncode({
            'id': 'basket-1',
            'name': 'Test Basket',
            'items': <Object>[],
            'created_at': '2026-07-12T00:00:00Z',
          })
        : jsonEncode({'detail': 'not exposed'});
    return ApiService(
      client: MockClient((_) async => http.Response(body, statusCode)),
      authService: _TestAuthService(),
    );
  }

  test('returns a basket for a 201 response', () async {
    final basket = await serviceReturning(201).createBasket('Test Basket');

    expect(basket.id, 'basket-1');
  });

  for (final statusCode in [401, 403]) {
    test('classifies $statusCode as authentication failure', () async {
      expect(
        () => serviceReturning(statusCode).createBasket('Test Basket'),
        throwsA(
          isA<ApiException>()
              .having(
                  (error) => error.kind, 'kind', ApiErrorKind.authentication)
              .having((error) => error.statusCode, 'statusCode', statusCode),
        ),
      );
    });
  }

  test('classifies another HTTP failure as a server failure', () async {
    expect(
      () => serviceReturning(500).createBasket('Test Basket'),
      throwsA(
        isA<ApiException>()
            .having((error) => error.kind, 'kind', ApiErrorKind.server)
            .having((error) => error.statusCode, 'statusCode', 500),
      ),
    );
  });

  test('classifies a client failure before response as connection failure',
      () async {
    final service = ApiService(
      client: MockClient((request) async {
        throw http.ClientException('connection refused', request.url);
      }),
      authService: _TestAuthService(),
    );

    expect(
      () => service.createBasket('Test Basket'),
      throwsA(
        isA<ApiException>()
            .having((error) => error.kind, 'kind', ApiErrorKind.connection)
            .having((error) => error.statusCode, 'statusCode', isNull),
      ),
    );
  });
}
