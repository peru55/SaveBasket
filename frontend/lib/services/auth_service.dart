import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthService {
  // Determine backend URL based on platform (web vs emulator/device)
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    } catch (_) {}
    return 'http://localhost:8000';
  }
  final _storage = const FlutterSecureStorage();

  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl/api/auth/token/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );
      final data = resp.body.isNotEmpty ? jsonDecode(resp.body) : null;
      if (resp.statusCode == 200 && data != null) {
        await setAccessToken(data['access']);
        await setRefreshToken(data['refresh']);
        return {'success': true};
      }
      return {'success': false, 'error': data ?? 'Unexpected response: ${resp.statusCode}'};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<Map<String, dynamic>> register(String username, String email, String password) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl/api/auth/register/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'email': email, 'password': password}),
      );
      final data = resp.body.isNotEmpty ? jsonDecode(resp.body) : null;
      if (resp.statusCode == 201) {
        return {'success': true, 'data': data};
      }
      return {'success': false, 'error': data ?? 'Unexpected response: ${resp.statusCode}'};
    } catch (e) {
      return {'success': false, 'error': e.toString()};
    }
  }

  Future<bool> refreshToken() async {
    final refresh = await getRefreshToken();
    if (refresh == null) return false;
    final resp = await http.post(
      Uri.parse('$baseUrl/api/auth/token/refresh/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh': refresh}),
    );
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body);
      await setAccessToken(data['access']);
      return true;
    }
    // refresh failed; clear tokens
    await clearTokens();
    return false;
  }

  Future<void> logout() async {
    await clearTokens();
  }

  Future<void> setAccessToken(String? token) async {
    if (token == null) return;
    await _storage.write(key: 'access', value: token);
  }

  Future<void> setRefreshToken(String? token) async {
    if (token == null) return;
    await _storage.write(key: 'refresh', value: token);
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: 'access');
  }

  Future<String?> getRefreshToken() async {
    return _storage.read(key: 'refresh');
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access');
    await _storage.delete(key: 'refresh');
  }

  Future<bool> isLoggedIn() async {
    final token = await getAccessToken();
    return token != null;
  }
}
