import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'auth_service.dart';
import '../models/product.dart';
import '../models/supermarket.dart';
import '../models/basket.dart';

class ApiService {
  final http.Client _client = http.Client();
  final AuthService _auth = AuthService();

  // Determine backend URL based on platform
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000/api';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000/api';
    } catch (_) {}
    return 'http://localhost:8000/api';
  }

  Future<List<Supermarket>> getSupermarkets() async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = <String, String>{};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.get(Uri.parse('$baseUrl/supermarkets/'), headers: headers);
    });
    if (resp.statusCode == 200) {
      List jsonResponse = json.decode(utf8.decode(resp.bodyBytes));
      return jsonResponse.map((item) => Supermarket.fromJson(item)).toList();
    }
    throw Exception('Failed to load supermarkets');
  }

  Future<List<Branch>> getBranches({String? supermarketId}) async {
    String url = '$baseUrl/branches/';
    if (supermarketId != null) url += '?supermarket_id=$supermarketId';
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = <String, String>{};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.get(Uri.parse(url), headers: headers);
    });
    if (resp.statusCode == 200) {
      List jsonResponse = json.decode(utf8.decode(resp.bodyBytes));
      return jsonResponse.map((item) => Branch.fromJson(item)).toList();
    }
    throw Exception('Failed to load branches');
  }

  Future<List<Product>> searchProducts(String query, {String? category}) async {
    if (query.isEmpty) return [];
    final uri = Uri.parse('$baseUrl/products/').replace(queryParameters: {
      'search': query,
      if (category != null && category.isNotEmpty) 'category': category,
    });

    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = <String, String>{};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.get(uri, headers: headers);
    });
    if (resp.statusCode == 200) {
      List jsonResponse = json.decode(utf8.decode(resp.bodyBytes));
      return jsonResponse.map((item) => Product.fromJson(item)).toList();
    }
    throw Exception('Failed to search products');
  }

  Future<Basket> createBasket(String name) async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = {'Content-Type': 'application/json'};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.post(Uri.parse('$baseUrl/baskets/'), headers: headers, body: json.encode({'name': name}));
    });
    if (resp.statusCode == 201) return Basket.fromJson(json.decode(utf8.decode(resp.bodyBytes)));
    throw Exception('Failed to create basket');
  }

  Future<Basket> getBasket(String basketId) async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = <String, String>{};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.get(Uri.parse('$baseUrl/baskets/$basketId/'), headers: headers);
    });
    if (resp.statusCode == 200) return Basket.fromJson(json.decode(utf8.decode(resp.bodyBytes)));
    throw Exception('Failed to load basket');
  }

  Future<Basket> addItemToBasket(String basketId, String productId, int quantity) async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = {'Content-Type': 'application/json'};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.post(Uri.parse('$baseUrl/baskets/$basketId/add_item/'), headers: headers, body: json.encode({'product_id': productId, 'quantity': quantity}));
    });
    if (resp.statusCode == 200) return Basket.fromJson(json.decode(utf8.decode(resp.bodyBytes)));
    throw Exception('Failed to add item to basket');
  }

  Future<Basket> removeItemFromBasket(String basketId, String productId) async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = {'Content-Type': 'application/json'};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.post(Uri.parse('$baseUrl/baskets/$basketId/remove_item/'), headers: headers, body: json.encode({'product_id': productId}));
    });
    if (resp.statusCode == 200) return Basket.fromJson(json.decode(utf8.decode(resp.bodyBytes)));
    throw Exception('Failed to remove item from basket');
  }

  Future<Basket> updateItemQuantity(String basketId, String productId, int quantity) async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = {'Content-Type': 'application/json'};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.post(Uri.parse('$baseUrl/baskets/$basketId/update_item_quantity/'), headers: headers, body: json.encode({'product_id': productId, 'quantity': quantity}));
    });
    if (resp.statusCode == 200) return Basket.fromJson(json.decode(utf8.decode(resp.bodyBytes)));
    throw Exception('Failed to update quantity');
  }

  Future<List<BasketComparisonResult>> compareBasket(String basketId) async {
    final resp = await _withAuth(() async {
      final token = await _auth.getAccessToken();
      final headers = <String, String>{};
      if (token != null) headers['Authorization'] = 'Bearer $token';
      return _client.get(Uri.parse('$baseUrl/baskets/$basketId/compare/'), headers: headers);
    });
    if (resp.statusCode == 200) {
      List jsonResponse = json.decode(utf8.decode(resp.bodyBytes));
      return jsonResponse.map((item) => BasketComparisonResult.fromJson(item)).toList();
    }
    throw Exception('Failed to compare basket prices');
  }

  Future<http.Response> _withAuth(Future<http.Response> Function() fn) async {
    // Attach token to headers by reading from AuthService and recreating request inside fn
    http.Response resp = await fn();
    if (resp.statusCode == 401) {
      final refreshed = await _auth.refreshToken();
      if (refreshed) {
        resp = await fn();
        return resp;
      }
      await _auth.clearTokens();
    }
    return resp;
  }
}
