import 'package:flutter/material.dart';
import '../models/prediction_request.dart';
import '../models/prediction_response.dart';
import '../services/api_client.dart';
import '../services/fraud_prediction_service.dart';
import '../theme/app_theme.dart';

class PredictionScreen extends StatefulWidget {
  const PredictionScreen({super.key});

  @override
  State<PredictionScreen> createState() => _PredictionScreenState();
}

class _PredictionScreenState extends State<PredictionScreen> {
  final _formKey = GlobalKey<FormState>();

  final _amountController = TextEditingController(text: '9500.0');
  final _oldBalanceOrgController = TextEditingController(text: '10000.0');
  final _newBalanceOrigController = TextEditingController(text: '500.0');
  final _oldBalanceDestController = TextEditingController(text: '0.0');
  final _newBalanceDestController = TextEditingController(text: '9500.0');
  final _senderAccountController = TextEditingController(text: 'AC-10293');
  final _receiverAccountController = TextEditingController(text: 'MC-94821');

  String _selectedType = 'TRANSFER';
  String _selectedCurrency = 'USD';
  double _step = 1.0;

  bool _isLoading = false;
  PredictionResponse? _predictionResult;
  String? _errorMessage;
  String? _errorDetails;

  @override
  void dispose() {
    _amountController.dispose();
    _oldBalanceOrgController.dispose();
    _newBalanceOrigController.dispose();
    _oldBalanceDestController.dispose();
    _newBalanceDestController.dispose();
    _senderAccountController.dispose();
    _receiverAccountController.dispose();
    super.dispose();
  }

  Future<void> _submitPrediction() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _errorDetails = null;
      _predictionResult = null;
    });

    final request = PredictionRequest(
      amount: double.tryParse(_amountController.text) ?? 0.0,
      transactionType: _selectedType,
      oldBalanceOrg: double.tryParse(_oldBalanceOrgController.text) ?? 0.0,
      newBalanceOrig: double.tryParse(_newBalanceOrigController.text) ?? 0.0,
      oldBalanceDest: double.tryParse(_oldBalanceDestController.text) ?? 0.0,
      newBalanceDest: double.tryParse(_newBalanceDestController.text) ?? 0.0,
      currency: _selectedCurrency,
      step: _step,
      senderAccount: _senderAccountController.text.trim(),
      receiverAccount: _receiverAccountController.text.trim(),
    );

    try {
      final result = await FraudPredictionService().predict(request);
      setState(() {
        _predictionResult = result;
      });
    } on ApiException catch (e) {
      setState(() {
        _errorMessage = e.message;
        _errorDetails = e.details ??
            (e.validationErrors.isNotEmpty
                ? e.validationErrors.join('\n')
                : null);
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to score transaction. Check network connection.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Real-time Scoring'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildFormSection(),
              const SizedBox(height: 20),
              if (_isLoading) _buildLoadingCard(),
              if (_errorMessage != null) _buildErrorCard(),
              if (_predictionResult != null) _buildResultCard(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFormSection() {
    return Form(
      key: _formKey,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.assessment_outlined, color: AppTheme.emeraldPrimary, size: 22),
                  SizedBox(width: 10),
                  Text(
                    'Transaction Parameters',
                    style: TextStyle(
                      color: AppTheme.textHighEmphasis,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Transaction Type & Currency Row
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: DropdownButtonFormField<String>(
                      value: _selectedType,
                      decoration: const InputDecoration(labelText: 'Type'),
                      dropdownColor: AppTheme.darkGraphiteCard,
                      items: const [
                        DropdownMenuItem(value: 'TRANSFER', child: Text('TRANSFER')),
                        DropdownMenuItem(value: 'PAYMENT', child: Text('PAYMENT')),
                        DropdownMenuItem(value: 'CASH_OUT', child: Text('CASH_OUT')),
                        DropdownMenuItem(value: 'DEBIT', child: Text('DEBIT')),
                        DropdownMenuItem(value: 'CASH_IN', child: Text('CASH_IN')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _selectedType = val);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 1,
                    child: DropdownButtonFormField<String>(
                      value: _selectedCurrency,
                      decoration: const InputDecoration(labelText: 'Currency'),
                      dropdownColor: AppTheme.darkGraphiteCard,
                      items: const [
                        DropdownMenuItem(value: 'USD', child: Text('USD')),
                        DropdownMenuItem(value: 'INR', child: Text('INR')),
                        DropdownMenuItem(value: 'EUR', child: Text('EUR')),
                        DropdownMenuItem(value: 'GBP', child: Text('GBP')),
                      ],
                      onChanged: (val) {
                        if (val != null) setState(() => _selectedCurrency = val);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Amount
              TextFormField(
                controller: _amountController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                style: const TextStyle(color: AppTheme.textHighEmphasis),
                decoration: const InputDecoration(
                  labelText: 'Transaction Amount',
                  prefixIcon: Icon(Icons.attach_money_rounded, color: AppTheme.emeraldPrimary),
                ),
                validator: (val) {
                  final parsed = double.tryParse(val ?? '');
                  if (parsed == null || parsed <= 0) {
                    return 'Enter a valid positive amount';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 14),

              // Origin Balances Row
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _oldBalanceOrgController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: AppTheme.textHighEmphasis),
                      decoration: const InputDecoration(labelText: 'Old Balance (Org)'),
                      validator: (val) =>
                          double.tryParse(val ?? '') == null ? 'Required' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _newBalanceOrigController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: AppTheme.textHighEmphasis),
                      decoration: const InputDecoration(labelText: 'New Balance (Orig)'),
                      validator: (val) =>
                          double.tryParse(val ?? '') == null ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Destination Balances Row
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _oldBalanceDestController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: AppTheme.textHighEmphasis),
                      decoration: const InputDecoration(labelText: 'Old Balance (Dest)'),
                      validator: (val) =>
                          double.tryParse(val ?? '') == null ? 'Required' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _newBalanceDestController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: AppTheme.textHighEmphasis),
                      decoration: const InputDecoration(labelText: 'New Balance (Dest)'),
                      validator: (val) =>
                          double.tryParse(val ?? '') == null ? 'Required' : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              ElevatedButton.icon(
                onPressed: _isLoading ? null : _submitPrediction,
                icon: const Icon(Icons.bolt_rounded, size: 20),
                label: const Text('Execute ML Inference'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLoadingCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTheme.darkGraphiteCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.emeraldPrimary.withOpacity(0.3)),
      ),
      child: const Column(
        children: [
          CircularProgressIndicator(color: AppTheme.emeraldPrimary),
          SizedBox(height: 16),
          Text(
            'Calling /api/predict on live engine...',
            style: TextStyle(
              color: AppTheme.textHighEmphasis,
              fontWeight: FontWeight.w600,
            ),
          ),
          SizedBox(height: 4),
          Text(
            'Applying trained preprocessor pipeline and classifier model',
            style: TextStyle(color: AppTheme.textMediumEmphasis, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.errorRed.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.errorRed.withOpacity(0.5), width: 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.warning_amber_rounded, color: AppTheme.errorRed, size: 24),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _errorMessage ?? 'API Error',
                  style: const TextStyle(
                    color: AppTheme.textHighEmphasis,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          if (_errorDetails != null) ...[
            const SizedBox(height: 8),
            Text(
              _errorDetails!,
              style: const TextStyle(
                color: AppTheme.textMediumEmphasis,
                fontSize: 12,
                fontFamily: 'monospace',
                height: 1.35,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildResultCard() {
    final result = _predictionResult!;
    final isFraud = result.isFraud;
    final badgeColor = isFraud ? AppTheme.errorRed : AppTheme.emeraldPrimary;

    return Card(
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: badgeColor.withOpacity(0.5), width: 1.5),
        ),
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(
                      isFraud ? Icons.gpp_bad_rounded : Icons.verified_user_rounded,
                      color: badgeColor,
                      size: 26,
                    ),
                    const SizedBox(width: 10),
                    Text(
                      result.predictionLabel,
                      style: TextStyle(
                        color: badgeColor,
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.1,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: badgeColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: badgeColor, width: 1),
                  ),
                  child: Text(
                    result.riskLevel,
                    style: TextStyle(
                      color: badgeColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),

            _buildDetailRow('Transaction Ref', result.transactionRef),
            const SizedBox(height: 8),
            _buildDetailRow(
              'Fraud Probability',
              result.fraudProbability != null
                  ? '${(result.fraudProbability! * 100).toStringAsFixed(2)}%'
                  : 'N/A',
            ),
            const SizedBox(height: 8),
            _buildDetailRow(
              'Confidence Score',
              result.confidenceScore != null
                  ? '${result.confidenceScore!.toStringAsFixed(1)}%'
                  : 'N/A',
            ),
            const SizedBox(height: 8),
            _buildDetailRow(
              'Amount Normalized',
              '\$${result.normalizedAmountUsd.toStringAsFixed(2)} USD',
            ),
            const SizedBox(height: 8),
            _buildDetailRow('Inference Latency', '${result.latencyMs.toStringAsFixed(2)} ms'),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(color: AppTheme.textMediumEmphasis, fontSize: 13),
        ),
        Text(
          value,
          style: const TextStyle(
            color: AppTheme.textHighEmphasis,
            fontSize: 13,
            fontWeight: FontWeight.w600,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}
