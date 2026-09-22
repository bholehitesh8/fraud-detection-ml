class PredictionRequest {
  final double amount;
  final String transactionType;
  final double oldBalanceOrg;
  final double newBalanceOrig;
  final double oldBalanceDest;
  final double newBalanceDest;
  final String currency;
  final double step;
  final String? senderAccount;
  final String? receiverAccount;

  PredictionRequest({
    required this.amount,
    required this.transactionType,
    required this.oldBalanceOrg,
    required this.newBalanceOrig,
    required this.oldBalanceDest,
    required this.newBalanceDest,
    this.currency = 'USD',
    this.step = 1.0,
    this.senderAccount,
    this.receiverAccount,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'amount': amount,
      'transaction_type': transactionType,
      'old_balance_org': oldBalanceOrg,
      'new_balance_orig': newBalanceOrig,
      'old_balance_dest': oldBalanceDest,
      'new_balance_dest': newBalanceDest,
      'currency': currency,
      'step': step,
    };
    if (senderAccount != null && senderAccount!.trim().isNotEmpty) {
      map['sender_account'] = senderAccount!.trim();
    }
    if (receiverAccount != null && receiverAccount!.trim().isNotEmpty) {
      map['receiver_account'] = receiverAccount!.trim();
    }
    return map;
  }
}
