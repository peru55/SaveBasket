import 'package:flutter/material.dart';
import '../models/product.dart';
import '../models/basket.dart';
import '../services/api_service.dart';

class BasketProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  
  Basket? _activeBasket;
  List<Product> _searchResults = [];
  List<BasketComparisonResult> _comparisonResults = [];
  bool _isLoading = false;
  String? _errorMessage;

  Basket? get activeBasket => _activeBasket;
  List<Product> get searchResults => _searchResults;
  List<BasketComparisonResult> get comparisonResults => _comparisonResults;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  // Initialize or fetch the active basket
  Future<void> initializeBasket() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // In a prototype, we can check if there's any existing basket on the server,
      // or simply create a new one. For now, we'll try to create a default one.
      // In a production app, we would persist the basket ID locally.
      _activeBasket = await _apiService.createBasket("My Grocery Basket");
      await fetchComparison();
    } catch (e) {
      _errorMessage = "Failed to connect to the backend. Please ensure the Django server is running. Error: $e";
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
      _activeBasket = await _apiService.addItemToBasket(_activeBasket!.id, product.id, quantity);
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
      _activeBasket = await _apiService.removeItemFromBasket(_activeBasket!.id, productId);
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
      _activeBasket = await _apiService.updateItemQuantity(_activeBasket!.id, productId, quantity);
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
