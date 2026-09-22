class ApiConfig {
  /// Base URL of the live Fraud Detection backend
  static const String defaultBaseUrl = 'https://fraud-detection-ml-m6ne.onrender.com';

  /// Centralized base URL configuration (can be updated dynamically if needed)
  static String baseUrl = defaultBaseUrl;

  // Timeout Configurations
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Endpoints
  static String get healthEndpoint => '$baseUrl/api/health';
  static String get loginEndpoint => '$baseUrl/api/auth/login';
  static String get logoutEndpoint => '$baseUrl/api/auth/logout';
  static String get meEndpoint => '$baseUrl/api/auth/me';
  static String get predictEndpoint => '$baseUrl/api/predict';
  static String get predictionsEndpoint => '$baseUrl/api/predictions';
  static String singlePredictionEndpoint(String id) => '$baseUrl/api/predictions/$id';
  static String get statsEndpoint => '$baseUrl/api/stats';
  static String get analyticsSummaryEndpoint => '$baseUrl/api/analytics/summary';

  // Standard Headers
  static Map<String, String> defaultHeaders({String? sessionCookie}) {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (sessionCookie != null && sessionCookie.isNotEmpty) {
      headers['Cookie'] = sessionCookie;
    }
    return headers;
  }
}
