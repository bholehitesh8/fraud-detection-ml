class PredictionItem {
  final int id;
  final String transactionRef;
  final double step;
  final String transactionType;
  final double amount;
  final String currency;
  final double normalizedAmountUsd;
  final bool isFraud;
  final int predictedClass;
  final double? confidenceScore;
  final String riskLevel;
  final String? createdAt;
  final String? senderAccount;
  final String? receiverAccount;

  PredictionItem({
    required this.id,
    required this.transactionRef,
    required this.step,
    required this.transactionType,
    required this.amount,
    required this.currency,
    required this.normalizedAmountUsd,
    required this.isFraud,
    required this.predictedClass,
    this.confidenceScore,
    required this.riskLevel,
    this.createdAt,
    this.senderAccount,
    this.receiverAccount,
  });

  factory PredictionItem.fromJson(Map<String, dynamic> json) {
    return PredictionItem(
      id: json['id'] as int? ?? 0,
      transactionRef: json['transaction_ref'] as String? ?? '',
      step: (json['step'] as num?)?.toDouble() ?? 1.0,
      transactionType: json['transaction_type'] as String? ?? 'PAYMENT',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency'] as String? ?? 'USD',
      normalizedAmountUsd: (json['normalized_amount_usd'] as num?)?.toDouble() ?? 0.0,
      isFraud: json['is_fraud'] as bool? ?? false,
      predictedClass: (json['predicted_class'] as num?)?.toInt() ?? 0,
      confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
      riskLevel: json['risk_level'] as String? ?? 'LOW',
      createdAt: json['created_at'] as String?,
      senderAccount: json['sender_account'] as String?,
      receiverAccount: json['receiver_account'] as String?,
    );
  }
}

class PredictionHistoryResponse {
  final bool success;
  final int count;
  final int page;
  final int perPage;
  final int total;
  final int totalPages;
  final List<PredictionItem> predictions;

  PredictionHistoryResponse({
    required this.success,
    required this.count,
    required this.page,
    required this.perPage,
    required this.total,
    required this.totalPages,
    required this.predictions,
  });

  factory PredictionHistoryResponse.fromJson(Map<String, dynamic> json) {
    final rawList = json['predictions'] as List<dynamic>? ?? [];
    final items = rawList
        .map((e) => PredictionItem.fromJson(e as Map<String, dynamic>))
        .toList();

    return PredictionHistoryResponse(
      success: json['success'] as bool? ?? true,
      count: (json['count'] as num?)?.toInt() ?? items.length,
      page: (json['page'] as num?)?.toInt() ?? 1,
      perPage: (json['per_page'] as num?)?.toInt() ?? 20,
      total: (json['total'] as num?)?.toInt() ?? items.length,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 1,
      predictions: items,
    );
  }
}
