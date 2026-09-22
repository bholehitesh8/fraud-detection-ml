import 'dart:async';
import 'dart:convert';
import 'dart:io';
import '../config/api_config.dart';

/// Structured custom exception for API errors returned by the Flask backend
class ApiException implements Exception {
  final int statusCode;
  final String message;
  final String? errorType;
  final String? details;
  final List<String> validationErrors;

  ApiException({
    required this.statusCode,
    required this.message,
    this.errorType,
    this.details,
    this.validationErrors = const [],
  });

  @override
  String toString() {
    if (validationErrors.isNotEmpty) {
      return '$message: ${validationErrors.join(", ")}';
    }
    if (details != null && details!.isNotEmpty) {
      return '$message ($details)';
    }
    return message;
  }
}

/// Centralized API HTTP Client handling HTTPS, cookies, timeouts, and JSON
class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  final HttpClient _httpClient = HttpClient()
    ..connectionTimeout = ApiConfig.connectTimeout;

  String? _sessionCookie;

  String? get sessionCookie => _sessionCookie;
  bool get hasSession => _sessionCookie != null && _sessionCookie!.isNotEmpty;

  void setSessionCookie(String? cookie) {
    _sessionCookie = cookie;
  }

  void clearSession() {
    _sessionCookie = null;
  }

  /// Sends an HTTPS GET request
  Future<dynamic> get(String url, {Map<String, String>? queryParams}) async {
    Uri uri = Uri.parse(url);
    if (queryParams != null && queryParams.isNotEmpty) {
      uri = uri.replace(queryParameters: queryParams);
    }
    return _sendRequest('GET', uri);
  }

  /// Sends an HTTPS POST request
  Future<dynamic> post(String url, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse(url);
    return _sendRequest('POST', uri, body: body);
  }

  Future<dynamic> _sendRequest(
    String method,
    Uri uri, {
    Map<String, dynamic>? body,
  }) async {
    try {
      final request = await _httpClient.openUrl(method, uri).timeout(
        ApiConfig.connectTimeout,
        onTimeout: () => throw TimeoutException(
          'Connection to backend timed out after ${ApiConfig.connectTimeout.inSeconds} seconds.',
        ),
      );

      // Apply standard headers
      request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');

      // Forward session cookie for authenticated requests
      if (_sessionCookie != null && _sessionCookie!.isNotEmpty) {
        request.headers.set(HttpHeaders.cookieHeader, _sessionCookie!);
      }

      // Write JSON payload for POST
      if (body != null) {
        final payload = utf8.encode(jsonEncode(body));
        request.headers.set(HttpHeaders.contentLengthHeader, payload.length.toString());
        request.add(payload);
      }

      final response = await request.close().timeout(
        ApiConfig.receiveTimeout,
        onTimeout: () => throw TimeoutException(
          'Backend response timed out after ${ApiConfig.receiveTimeout.inSeconds} seconds.',
        ),
      );

      // Extract and update session cookies from Set-Cookie headers
      final setCookieHeaders = response.headers[HttpHeaders.setCookieHeader];
      if (setCookieHeaders != null && setCookieHeaders.isNotEmpty) {
        for (final cookieStr in setCookieHeaders) {
          if (cookieStr.contains('session=')) {
            // Extract the session=... token part
            final parts = cookieStr.split(';');
            for (final part in parts) {
              if (part.trim().startsWith('session=')) {
                _sessionCookie = part.trim();
                break;
              }
            }
          }
        }
      }

      final responseBody = await response.transform(utf8.decoder).join();
      dynamic parsedJson;
      if (responseBody.isNotEmpty) {
        try {
          parsedJson = jsonDecode(responseBody);
        } catch (_) {
          parsedJson = {'raw': responseBody};
        }
      }

      // Handle HTTP status codes
      final statusCode = response.statusCode;
      if (statusCode >= 200 && statusCode < 300) {
        return parsedJson;
      }

      // Parse structured error responses from Flask
      String errorMessage = 'Server error ($statusCode)';
      String? errorType;
      String? details;
      List<String> validationErrors = [];

      if (parsedJson is Map<String, dynamic>) {
        errorMessage = parsedJson['error'] ??
            parsedJson['message'] ??
            parsedJson['details'] ??
            errorMessage;
        errorType = parsedJson['error_type'];
        details = parsedJson['details'];

        if (parsedJson['errors'] is List) {
          validationErrors = (parsedJson['errors'] as List)
              .map((e) => e.toString())
              .toList();
        }
      }

      throw ApiException(
        statusCode: statusCode,
        message: errorMessage,
        errorType: errorType,
        details: details,
        validationErrors: validationErrors,
      );
    } on SocketException catch (e) {
      throw ApiException(
        statusCode: 0,
        message: 'Unable to connect to backend. Please check network connection.',
        details: e.message,
      );
    } on TimeoutException catch (e) {
      throw ApiException(
        statusCode: 408,
        message: e.message ?? 'Request timed out.',
      );
    } on HandshakeException catch (e) {
      throw ApiException(
        statusCode: 0,
        message: 'SSL/TLS handshake error connecting to backend.',
        details: e.message,
      );
    }
  }
}
