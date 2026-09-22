import 'dart:async';
import '../config/api_config.dart';
import '../models/analytics_summary.dart';
import '../models/prediction_history_response.dart';
import '../models/prediction_request.dart';
import '../models/prediction_response.dart';
import 'api_client.dart';

class FraudPredictionService {
  static final FraudPredictionService _instance =
      FraudPredictionService._internal();
  factory FraudPredictionService() => _instance;
  FraudPredictionService._internal();

  final ApiClient _apiClient = ApiClient();

  /// Submits real transaction parameters to the live ML prediction endpoint
  Future<PredictionResponse> predict(PredictionRequest request) async {
    final response = await _apiClient.post(
      ApiConfig.predictEndpoint,
      body: request.toJson(),
    );

    if (response is Map<String, dynamic>) {
      return PredictionResponse.fromJson(response);
    }
    throw ApiException(
      statusCode: 500,
      message: 'Malformed response received from ML prediction service.',
    );
  }

  /// Queries real stored prediction history from the backend database
  Future<PredictionHistoryResponse> getPredictionHistory({
    int page = 1,
    int perPage = 20,
    String? status,
    String? currency,
    String? ref,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'per_page': perPage.toString(),
    };
    if (status != null && status.isNotEmpty) {
      queryParams['status'] = status;
    }
    if (currency != null && currency.isNotEmpty) {
      queryParams['currency'] = currency;
    }
    if (ref != null && ref.isNotEmpty) {
      queryParams['ref'] = ref;
    }

    final response = await _apiClient.get(
      ApiConfig.predictionsEndpoint,
      queryParams: queryParams,
    );

    if (response is Map<String, dynamic>) {
      return PredictionHistoryResponse.fromJson(response);
    }
    throw ApiException(
      statusCode: 500,
      message: 'Failed to retrieve prediction history records.',
    );
  }

  /// Fetches consolidated analytics summary and KPI counters from the backend
  Future<AnalyticsSummary> getAnalyticsSummary({int? days}) async {
    final queryParams = <String, String>{};
    if (days != null) {
      queryParams['days'] = days.toString();
    }

    final response = await _apiClient.get(
      ApiConfig.analyticsSummaryEndpoint,
      queryParams: queryParams,
    );

    if (response is Map<String, dynamic>) {
      return AnalyticsSummary.fromJson(response);
    }
    throw ApiException(
      statusCode: 500,
      message: 'Failed to fetch analytics summary data.',
    );
  }

  /// Checks system and ML model status on the live backend
  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final response = await _apiClient.get(ApiConfig.healthEndpoint);
      if (response is Map<String, dynamic>) {
        return response;
      }
    } on ApiException catch (e) {
      // 500 is returned when status is 'degraded' (e.g. artifact missing)
      return {
        'status': 'degraded',
        'message': e.message,
        'details': e.details,
      };
    }
    return {'status': 'unknown'};
  }
}
