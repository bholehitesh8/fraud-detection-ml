import 'dart:async';
import '../config/api_config.dart';
import '../models/user_model.dart';
import 'api_client.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  final ApiClient _apiClient = ApiClient();

  UserModel? _currentUser;
  UserModel? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null && _apiClient.hasSession;

  /// Authenticates with the real backend using identifier (username/email) and password
  Future<UserModel> login({
    required String identifier,
    required String password,
  }) async {
    final response = await _apiClient.post(
      ApiConfig.loginEndpoint,
      body: {
        'identifier': identifier.trim(),
        'password': password,
      },
    );

    if (response is Map<String, dynamic> && response['success'] == true) {
      final userJson = response['user'] as Map<String, dynamic>;
      _currentUser = UserModel.fromJson(userJson);
      return _currentUser!;
    } else {
      final errMsg = (response is Map<String, dynamic>)
          ? (response['error'] ?? 'Authentication failed')
          : 'Unexpected login response';
      throw ApiException(statusCode: 401, message: errMsg);
    }
  }

  /// Verifies current user session against /api/auth/me
  Future<UserModel?> checkSession() async {
    if (!_apiClient.hasSession) {
      _currentUser = null;
      return null;
    }

    try {
      final response = await _apiClient.get(ApiConfig.meEndpoint);
      if (response is Map<String, dynamic> && response['authenticated'] == true) {
        final userJson = response['user'] as Map<String, dynamic>;
        _currentUser = UserModel.fromJson(userJson);
        return _currentUser;
      }
    } catch (_) {
      // Session invalid or expired
    }

    _currentUser = null;
    _apiClient.clearSession();
    return null;
  }

  /// Logs out of the current session on the backend
  Future<void> logout() async {
    try {
      await _apiClient.post(ApiConfig.logoutEndpoint);
    } catch (_) {
      // Ignored if network disconnects during logout
    } finally {
      _currentUser = null;
      _apiClient.clearSession();
    }
  }
}
