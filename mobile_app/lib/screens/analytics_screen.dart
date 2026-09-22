import 'package:flutter/material.dart';
import '../models/analytics_summary.dart';
import '../services/api_client.dart';
import '../services/fraud_prediction_service.dart';
import '../theme/app_theme.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  AnalyticsSummary? _analytics;

  @override
  void initState() {
    super.initState();
    _fetchAnalytics();
  }

  Future<void> _fetchAnalytics() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final summary = await FraudPredictionService().getAnalyticsSummary();
      setState(() {
        _analytics = summary;
      });
    } on ApiException catch (e) {
      setState(() {
        _errorMessage = e.message;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load analytics summary from backend.';
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
        title: const Text('Live Analytics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _fetchAnalytics,
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _fetchAnalytics,
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
              'Querying /api/analytics/summary...',
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
                onPressed: _fetchAnalytics,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final data = _analytics!;

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // KPI Metric Grid
          Row(
            children: [
              Expanded(
                child: _buildKpiCard(
                  label: 'Total Scored',
                  value: '${data.totalPredictions}',
                  icon: Icons.numbers_rounded,
                  accentColor: AppTheme.tealSecondary,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: _buildKpiCard(
                  label: 'Fraud Flagged',
                  value: '${data.fraudulentPredictions}',
                  icon: Icons.warning_amber_rounded,
                  accentColor: AppTheme.errorRed,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _buildKpiCard(
                  label: 'Fraud Rate',
                  value: '${data.fraudPercentage.toStringAsFixed(1)}%',
                  icon: Icons.percent_rounded,
                  accentColor: AppTheme.warningAmber,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: _buildKpiCard(
                  label: 'Volume (USD)',
                  value: '\$${data.totalVolumeUsd.toStringAsFixed(0)}',
                  icon: Icons.attach_money_rounded,
                  accentColor: AppTheme.emeraldPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // ML Architecture & Pipeline Details
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.memory_rounded, color: AppTheme.emeraldPrimary, size: 20),
                      SizedBox(width: 10),
                      Text(
                        'Backend Service Diagnostics',
                        style: TextStyle(
                          color: AppTheme.textHighEmphasis,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Divider(),
                  const SizedBox(height: 14),
                  _buildDiagRow('Active Model', data.currentModel),
                  const SizedBox(height: 10),
                  _buildDiagRow(
                    'Inference Status',
                    data.modelStatus,
                    color: data.modelStatus.toLowerCase() == 'loaded'
                        ? AppTheme.emeraldPrimary
                        : AppTheme.warningAmber,
                  ),
                  const SizedBox(height: 10),
                  _buildDiagRow(
                    'Audit Database',
                    data.dbStatus,
                    color: AppTheme.emeraldPrimary,
                  ),
                  const SizedBox(height: 10),
                  _buildDiagRow(
                    'REST API Gateway',
                    data.apiStatus,
                    color: AppTheme.emeraldPrimary,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKpiCard({
    required String label,
    required String value,
    required IconData icon,
    required Color accentColor,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: accentColor, size: 22),
            const SizedBox(height: 12),
            Text(
              value,
              style: const TextStyle(
                color: AppTheme.textHighEmphasis,
                fontSize: 22,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(
                color: AppTheme.textMediumEmphasis,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDiagRow(String label, String value, {Color? color}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(color: AppTheme.textMediumEmphasis, fontSize: 13),
        ),
        Text(
          value,
          style: TextStyle(
            color: color ?? AppTheme.textHighEmphasis,
            fontSize: 13,
            fontWeight: FontWeight.w600,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}
