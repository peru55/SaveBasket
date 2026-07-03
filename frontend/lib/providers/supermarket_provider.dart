import 'package:flutter/material.dart';
import '../models/supermarket.dart';
import '../services/api_service.dart';

class SupermarketProvider with ChangeNotifier {
  final ApiService _api = ApiService();
  List<Supermarket> _items = [];
  bool _isLoading = false;
  String? _error;

  List<Supermarket> get items => _items;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> load() async {
    if (_items.isNotEmpty || _isLoading) return;
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _items = await _api.getSupermarkets();
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  String _normalize(String? name) {
    if (name == null) return '';
    final s = name.toLowerCase().replaceAll('&', ' and ');
    return s.replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();
  }

  Supermarket? findByName(String name) {
    final norm = _normalize(name);
    for (final s in _items) {
      if (_normalize(s.name).contains(norm) ||
          norm.contains(_normalize(s.name))) {
        return s;
      }
    }
    return null;
  }

  String? logoUrlForName(String name) {
    final s = findByName(name);
    return s?.logoUrl;
  }

  // Local asset fallback mapping for commonly-known supermarkets
  String? assetForName(String name) {
    final norm = _normalize(name);
    if (norm.contains('carrefour')) {
      return 'assets/logos/Carrefour-Logo.png';
    }
    if (norm.contains('naivas')) {
      return 'assets/logos/Naivas-Logo.png';
    }
    if (norm.contains('quickmart') ||
        norm.contains('quick mark') ||
        norm.contains('quickmart')) {
      return 'assets/logos/Quickmart-Logo.jpeg';
    }
    if (norm.contains('cleanshelf') || norm.contains('clean shelf')) {
      return 'assets/logos/Cleanshelf-Logo.jpeg';
    }
    if (norm.contains('chandarana')) {
      return 'assets/logos/Chandarana-Foodplus-Logo.jpeg';
    }
    if (norm.contains('eastmatt') || norm.contains('east matt')) {
      return 'assets/logos/Eastmatt-Logo.png';
    }
    return null;
  }
}
