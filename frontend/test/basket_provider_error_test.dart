import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/basket.dart';
import 'package:frontend/providers/basket_provider.dart';
import 'package:frontend/services/api_exception.dart';
import 'package:frontend/services/api_service.dart';

class _ThrowingApiService extends ApiService {
  final ApiException error;

  _ThrowingApiService(this.error);

  @override
  Future<Basket> createBasket(String name) async => throw error;
}

void main() {
  test('maps authentication failures to session expired', () async {
    final provider = BasketProvider(
      apiService: _ThrowingApiService(
        const ApiException(
          ApiErrorKind.authentication,
          'Your session is no longer valid.',
          statusCode: 401,
        ),
      ),
    );

    await provider.initializeBasket();

    expect(provider.backendError?.kind, ApiErrorKind.authentication);
    expect(provider.backendError?.title, 'Session expired');
  });

  test('maps connection failures to backend offline', () async {
    final provider = BasketProvider(
      apiService: _ThrowingApiService(
        const ApiException(
          ApiErrorKind.connection,
          'Could not connect to the backend.',
        ),
      ),
    );

    await provider.initializeBasket();

    expect(provider.backendError?.kind, ApiErrorKind.connection);
    expect(provider.backendError?.title, 'Backend offline');
  });

  test('maps server failures to backend error', () async {
    final provider = BasketProvider(
      apiService: _ThrowingApiService(
        const ApiException(
          ApiErrorKind.server,
          'The backend could not initialize your basket.',
          statusCode: 500,
        ),
      ),
    );

    await provider.initializeBasket();

    expect(provider.backendError?.kind, ApiErrorKind.server);
    expect(provider.backendError?.title, 'Backend error');
  });
}
