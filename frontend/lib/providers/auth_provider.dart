import 'dart:async';
import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _service = AuthService();
  bool _loggedIn = false;
  Timer? _refreshTimer;

  bool get loggedIn => _loggedIn;

  Future<void> init() async {
    try {
      _loggedIn = await _service.isLoggedIn();
    } catch (e) {
      debugPrint('AuthProvider.init() error reading storage: $e');
      _loggedIn = false;
    }
    if (_loggedIn) _startAutoRefresh();
    notifyListeners();
  }

  Future<Map<String, dynamic>> login(String username, String password) async {
    final res = await _service.login(username, password);
    if (res['success'] == true) {
      _loggedIn = true;
      _startAutoRefresh();
      notifyListeners();
    }
    return res;
  }

  Future<Map<String, dynamic>> register(
      String username, String email, String password) async {
    return _service.register(username, email, password);
  }

  Future<void> logout() async {
    await _service.logout();
    _stopAutoRefresh();
    _loggedIn = false;
    notifyListeners();
  }

  Future<bool> refresh() async {
    final ok = await _service.refreshToken();
    if (ok) {
      _loggedIn = true;
      if (_refreshTimer == null) _startAutoRefresh();
      notifyListeners();
    } else {
      _stopAutoRefresh();
      _loggedIn = false;
      notifyListeners();
    }
    return ok;
  }

  void _startAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(const Duration(minutes: 12), (_) async {
      await refresh();
    });
  }

  void _stopAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
  }

  @override
  void dispose() {
    _stopAutoRefresh();
    super.dispose();
  }
}
