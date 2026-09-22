import 'package:flutter/material.dart';
import '../models/prediction_history_response.dart';
import '../services/api_client.dart';
import '../services/fraud_prediction_service.dart';
import '../theme/app_theme.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  List<PredictionItem> _predictions = [];
  int _totalRecords = 0;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await FraudPredictionService().getPredictionHistory(
        page: 1,
        perPage: 30,
      );
      setState(() {
        _predictions = response.predictions;
        _totalRecords = response.total;
      });
    } on ApiException catch (e) {
      setState(() {
        _errorMessage = e.message;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load transaction history from backend.';
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
        title: const Text('Audit History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Reload',
            onPressed: _isLoading ? null : _fetchHistory,
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _fetchHistory,
          color: AppTheme.emeraldPrimary,
          backgroundColor: AppTheme.darkGraphiteCard,
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: AppTheme.emeraldPrimary),
            SizedBox(height: 16),
            Text(
              'Querying /api/predictions...',
              style: TextStyle(color: AppTheme.textMediumEmphasis),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline_rounded, color: AppTheme.errorRed, size: 40),
              const SizedBox(height: 14),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textHighEmphasis, fontSize: 14),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _fetchHistory,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retry Query'),
              ),
            ],
          ),
        ),
      );
    }

    if (_predictions.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.darkGraphiteCard,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.darkGraphiteBorder),
                ),
                child: const Icon(
                  Icons.receipt_long_outlined,
                  color: AppTheme.textMuted,
                  size: 40,
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                'No Transactions Stored in Database',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppTheme.textHighEmphasis,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'The backend database currently contains 0 scored transactions. Submit a live prediction to record your first real transaction.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: AppTheme.textMediumEmphasis,
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      itemCount: _predictions.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (ctx, index) {
        final item = _predictions[index];
        final isFraud = item.isFraud;
        final statusColor = isFraud ? AppTheme.errorRed : AppTheme.emeraldPrimary;

        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      item.transactionRef,
                      style: const TextStyle(
                        color: AppTheme.textHighEmphasis,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: statusColor, width: 0.8),
                      ),
                      child: Text(
                        isFraud ? 'FRAUD' : 'SAFE',
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${item.transactionType} • ${item.currency}',
                      style: const TextStyle(
                        color: AppTheme.textMediumEmphasis,
                        fontSize: 12.5,
                      ),
                    ),
                    Text(
                      '\$${item.normalizedAmountUsd.toStringAsFixed(2)} USD',
                      style: const TextStyle(
                        color: AppTheme.textHighEmphasis,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                if (item.createdAt != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    item.createdAt!,
                    style: const TextStyle(color: AppTheme.textMuted, fontSize: 11),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
