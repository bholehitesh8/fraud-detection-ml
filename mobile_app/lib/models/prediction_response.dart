class PredictionResponse {
  final String status;
  final String transactionRef;
  final bool isFraud;
  final int predictedClass;
  final String predictionLabel;
  final double? fraudProbability;
  final double? confidenceScore;
  final String riskLevel;
  final String currency;
  final double originalAmount;
  final double normalizedAmountUsd;
  final double exchangeRate;
  final Map<String, dynamic>? modelInfo;
  final String modelStatus;
  final String validationStatus;
  final String timestamp;
  final double latencyMs;

  PredictionResponse({
    required this.status,
    required this.transactionRef,
    required this.isFraud,
    required this.predictedClass,
    required this.predictionLabel,
    this.fraudProbability,
    this.confidenceScore,
    required this.riskLevel,
    required this.currency,
    required this.originalAmount,
    required this.normalizedAmountUsd,
    required this.exchangeRate,
    this.modelInfo,
    this.modelStatus = 'Loaded',
    this.validationStatus = 'Passed',
    required this.timestamp,
    required this.latencyMs,
  });

  factory PredictionResponse.fromJson(Map<String, dynamic> json) {
    return PredictionResponse(
      status: json['status'] as String? ?? 'success',
      transactionRef: json['transaction_ref'] as String? ?? '',
      isFraud: json['is_fraud'] as bool? ?? false,
      predictedClass: (json['predicted_class'] as num?)?.toInt() ?? 0,
      predictionLabel: json['prediction_label'] as String? ?? 'LEGITIMATE',
      fraudProbability: (json['fraud_probability'] as num?)?.toDouble(),
      confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
      riskLevel: json['risk_level'] as String? ?? 'LOW',
      currency: json['currency'] as String? ?? 'USD',
      originalAmount: (json['original_amount'] as num?)?.toDouble() ?? 0.0,
      normalizedAmountUsd: (json['normalized_amount_usd'] as num?)?.toDouble() ?? 0.0,
      exchangeRate: (json['exchange_rate'] as num?)?.toDouble() ?? 1.0,
      modelInfo: json['model_info'] as Map<String, dynamic>?,
      modelStatus: json['model_status'] as String? ?? 'Loaded',
      validationStatus: json['validation_status'] as String? ?? 'Passed',
      timestamp: json['timestamp'] as String? ?? '',
      latencyMs: (json['latency_ms'] as num?)?.toDouble() ?? 0.0,
    );
  }
}
