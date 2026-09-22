import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class SystemStatusCard extends StatelessWidget {
  const SystemStatusCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(
                      Icons.hub_outlined,
                      color: AppTheme.emeraldPrimary,
                      size: 20,
                    ),
                    SizedBox(width: 8),
                    Text(
                      'Gateway Connectivity',
                      style: TextStyle(
                        color: AppTheme.textHighEmphasis,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.emeraldPrimary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: AppTheme.emeraldPrimary.withOpacity(0.4),
                      width: 1,
                    ),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircleAvatar(
                        radius: 4,
                        backgroundColor: AppTheme.emeraldPrimary,
                      ),
                      SizedBox(width: 6),
                      Text(
                        'GATEWAY READY',
                        style: TextStyle(
                          color: AppTheme.emeraldPrimary,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),
            _buildStatusRow(
              icon: Icons.layers_outlined,
              label: 'Design System',
              value: 'Material 3 (Fintech Dark)',
            ),
            const SizedBox(height: 12),
            _buildStatusRow(
              icon: Icons.security_rounded,
              label: 'Auth Protocol',
              value: 'Session Cookie (Encrypted)',
            ),
            const SizedBox(height: 12),
            _buildStatusRow(
              icon: Icons.cloud_queue_rounded,
              label: 'Cloud Endpoint',
              value: 'Live (HTTPS / Render)',
              valueColor: AppTheme.tealSecondary,
            ),
          ],
        ),
      ),
    );
  }

  static Widget _buildStatusRow({
    required IconData icon,
    required String label,
    required String value,
    Color? valueColor,
  }) {
    return Row(
      children: [
        Icon(icon, size: 16, color: AppTheme.textMediumEmphasis),
        const SizedBox(width: 10),
        Text(
          label,
          style: const TextStyle(
            color: AppTheme.textMediumEmphasis,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
        const Spacer(),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? AppTheme.textHighEmphasis,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
