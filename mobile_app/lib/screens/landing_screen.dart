import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../theme/app_theme.dart';
import '../widgets/app_brand_header.dart';
import '../widgets/system_status_card.dart';
import 'login_screen.dart';

class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Fraud Detection ML'),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline_rounded),
            tooltip: 'System Info',
            onPressed: () => _showAboutModal(context),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const AppBrandHeader(),
              const SizedBox(height: 24),
              const SystemStatusCard(),
              const SizedBox(height: 24),
              _buildFeatureOverview(context),
              const SizedBox(height: 24),
              _buildBackendGatewayCard(context),
              const SizedBox(height: 32),
              _buildActionFooter(context),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureOverview(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.shield_outlined,
                  color: AppTheme.emeraldPrimary,
                  size: 20,
                ),
                SizedBox(width: 10),
                Text(
                  'Module Capabilities',
                  style: TextStyle(
                    color: AppTheme.textHighEmphasis,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _buildCapabilityTile(
              icon: Icons.psychology_outlined,
              title: 'Supervised ML Risk Scoring',
              description:
                  'Trained ensemble model pipelines for multi-factor fraud detection.',
            ),
            const SizedBox(height: 14),
            _buildCapabilityTile(
              icon: Icons.speed_rounded,
              title: 'Sub-second Scoring Engine',
              description:
                  'High-throughput validation designed for transactional streams.',
            ),
            const SizedBox(height: 14),
            _buildCapabilityTile(
              icon: Icons.lock_clock_outlined,
              title: 'Audit Logging & Explainability',
              description:
                  'Feature contribution breakdowns and verifiable security audit logs.',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCapabilityTile({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          margin: const EdgeInsets.only(top: 2),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppTheme.darkGraphiteBackground,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppTheme.darkGraphiteBorder),
          ),
          child: Icon(icon, size: 18, color: AppTheme.emeraldPrimary),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: AppTheme.textHighEmphasis,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                description,
                style: const TextStyle(
                  color: AppTheme.textMediumEmphasis,
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBackendGatewayCard(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.darkGraphiteCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.emeraldPrimary.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.cloud_done_rounded,
                color: AppTheme.emeraldPrimary,
                size: 20,
              ),
              SizedBox(width: 10),
              Text(
                'Live Backend Gateway',
                style: TextStyle(
                  color: AppTheme.textHighEmphasis,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            'Connected to live cloud API. Sign in with analyst or admin credentials to start real-time transaction evaluations.',
            style: TextStyle(
              color: AppTheme.textMediumEmphasis,
              fontSize: 12.5,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),
          SelectableText(
            ApiConfig.baseUrl,
            style: const TextStyle(
              color: AppTheme.tealSecondary,
              fontSize: 12,
              fontFamily: 'monospace',
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionFooter(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ElevatedButton.icon(
          icon: const Icon(Icons.login_rounded, size: 20),
          label: const Text('Operator Login'),
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const LoginScreen()),
            );
          },
        ),
      ],
    );
  }

  void _showAboutModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.darkGraphiteCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Fraud Detection Mobile Client',
              style: TextStyle(
                color: AppTheme.textHighEmphasis,
                fontSize: 18,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Version 1.0.0 (Build 1)\n'
              'Platform: Android Native (Flutter)\n'
              'UI Framework: Material 3\n'
              'Backend: ${ApiConfig.baseUrl}',
              style: const TextStyle(
                color: AppTheme.textMediumEmphasis,
                fontSize: 13,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 20),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('Close'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
