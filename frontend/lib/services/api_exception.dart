enum ApiErrorKind { authentication, connection, server }

class ApiException implements Exception {
  final ApiErrorKind kind;
  final String message;
  final int? statusCode;
  final Object? cause;

  const ApiException(
    this.kind,
    this.message, {
    this.statusCode,
    this.cause,
  });

  @override
  String toString() => message;
}
