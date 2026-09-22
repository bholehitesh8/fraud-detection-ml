class AnalyticsSummary {
  final bool success;
  final int totalPredictions;
  final int fraudulentPredictions;
  final int safePredictions;
  final double fraudPercentage;
  final double totalVolumeUsd;
  final String currentModel;
  final String systemStatus;
  final String modelStatus;
  final String dbStatus;
  final String apiStatus;
  final Map<String, dynamic> rawJson;

  AnalyticsSummary({
    required this.success,
    required this.totalPredictions,
    required this.fraudulentPredictions,
    required this.safePredictions,
    required this.fraudPercentage,
    required this.totalVolumeUsd,
    required this.currentModel,
    required this.systemStatus,
    required this.modelStatus,
    required this.dbStatus,
    required this.apiStatus,
    required this.rawJson,
  });

  factory AnalyticsSummary.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>? ?? {};
    final sysStatus = json['system_status'] as Map<String, dynamic>? ?? {};
    final apiMap = sysStatus['api'] as Map<String, dynamic>? ?? {};
    final dbMap = sysStatus['database'] as Map<String, dynamic>? ?? {};
    final modelMap = sysStatus['ml_model'] as Map<String, dynamic>? ?? {};

    return AnalyticsSummary(
      success: json['success'] as bool? ?? true,
      totalPredictions: (summary['total_predictions'] as num?)?.toInt() ?? 0,
      fraudulentPredictions: (summary['fraudulent_predictions'] as num?)?.toInt() ?? 0,
      safePredictions: (summary['safe_predictions'] as num?)?.toInt() ?? 0,
      fraudPercentage: (summary['fraud_percentage'] as num?)?.toDouble() ?? 0.0,
      totalVolumeUsd: (summary['total_volume_usd'] as num?)?.toDouble() ?? 0.0,
      currentModel: summary['current_model'] as String? ?? 'ExtraTrees v1.0.0',
      systemStatus: summary['system_status'] as String? ?? 'Operational',
      modelStatus: modelMap['status'] as String? ?? 'Degraded',
      dbStatus: dbMap['status'] as String? ?? 'Connected',
      apiStatus: apiMap['status'] as String? ?? 'Operational',
      rawJson: json,
    );
  }
}
