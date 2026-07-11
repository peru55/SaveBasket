import 'package:flutter/material.dart';
import '../models/product.dart';
import '../models/basket.dart';
import '../services/api_exception.dart';
import '../services/api_service.dart';

class BackendErrorState {
  final ApiErrorKind kind;
  final String title;
  final String message;

  const BackendErrorState({
    required this.kind,
    required this.title,
    required this.message,
  });

  factory BackendErrorState.fromApiException(ApiException error) {
    switch (error.kind) {
      case ApiErrorKind.authentication:
        return const BackendErrorState(
          kind: ApiErrorKind.authentication,
          title: 'Session expired',
          message:
              'Your saved login no longer matches this database. Sign in again to continue.',
        );
      case ApiErrorKind.connection:
        return const BackendErrorState(
          kind: ApiErrorKind.connection,
          title: 'Backend offline',
          message:
              'Could not reach Django. Start the backend and verify the configured API address.',
        );
      case ApiErrorKind.server:
        return const BackendErrorState(
          kind: ApiErrorKind.server,
          title: 'Backend error',
          message:
              'Django responded but could not initialize your basket. Try again or check the server logs.',
        );
    }
  }
}

class BasketProvider with ChangeNotifier {
  final ApiService _apiService;

  BasketProvider({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  Basket? _activeBasket;
  List<Product> _searchResults = [];
  List<BasketComparisonResult> _comparisonResults = [];
  bool _isLoading = false;
  String? _errorMessage;
  BackendErrorState? _backendError;

  Basket? get activeBasket => _activeBasket;
  List<Product> get searchResults => _searchResults;
  List<BasketComparisonResult> get comparisonResults => _comparisonResults;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  BackendErrorState? get backendError => _backendError;

  // Initialize or fetch the active basket
  Future<void> initializeBasket() async {
    _isLoading = true;
    _errorMessage = null;
    _backendError = null;
    notifyListeners();

    try {
      // In a prototype, we can check if there's any existing basket on the server,
      // or simply create a new one. For now, we'll try to create a default one.
      // In a production app, we would persist the basket ID locally.
      _activeBasket = await _apiService.createBasket("My Grocery Basket");
      await fetchComparison();
    } on ApiException catch (error) {
      _backendError = BackendErrorState.fromApiException(error);
      _errorMessage = _backendError!.message;
    } catch (e) {
      _backendError = const BackendErrorState(
        kind: ApiErrorKind.server,
        title: 'Backend error',
        message:
            'The app could not initialize your basket. Try again or check the server logs.',
      );
      _errorMessage = _backendError!.message;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Search products by query
  Future<void> searchProducts(String query) async {
    if (query.isEmpty) {
      _searchResults = [];
      notifyListeners();
      return;
    }

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _searchResults = await _apiService.searchProducts(query);
    } catch (e) {
      _errorMessage = "Failed to load products: $e";
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Add a product to the active basket
  Future<void> addItem(Product product, {int quantity = 1}) async {
    if (_activeBasket == null) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _activeBasket = await _apiService.addItemToBasket(
          _activeBasket!.id, product.id, quantity);
      await fetchComparison();
    } catch (e) {
      _errorMessage = "Failed to add item: $e";
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Remove a product from the active basket
  Future<void> removeItem(String productId) async {
    if (_activeBasket == null) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _activeBasket =
          await _apiService.removeItemFromBasket(_activeBasket!.id, productId);
      await fetchComparison();
    } catch (e) {
      _errorMessage = "Failed to remove item: $e";
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Update item quantity in the active basket
  Future<void> updateQuantity(String productId, int quantity) async {
    if (_activeBasket == null) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _activeBasket = await _apiService.updateItemQuantity(
          _activeBasket!.id, productId, quantity);
      await fetchComparison();
    } catch (e) {
      _errorMessage = "Failed to update quantity: $e";
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // Fetch real-time comparisons for the active basket
  Future<void> fetchComparison() async {
    if (_activeBasket == null) return;
    try {
      _comparisonResults = await _apiService.compareBasket(_activeBasket!.id);
    } catch (e) {
      debugPrint("Error fetching basket comparisons: $e");
    }
  }
}
