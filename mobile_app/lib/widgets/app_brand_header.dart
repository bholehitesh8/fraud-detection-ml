import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class AppBrandHeader extends StatelessWidget {
  const AppBrandHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.darkGraphiteCard,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppTheme.emeraldPrimary.withOpacity(0.4),
                  width: 1.2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.emeraldPrimary.withOpacity(0.12),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: const Icon(
                Icons.security_rounded,
                color: AppTheme.emeraldPrimary,
                size: 28,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Text(
                        'FRAUDGUARD',
                        style: TextStyle(
                          color: AppTheme.textHighEmphasis,
                          fontSize: 19,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppTheme.emeraldPrimary.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: AppTheme.emeraldPrimary.withOpacity(0.3),
                            width: 0.8,
                          ),
                        ),
                        child: const Text(
                          'ML CORE',
                          style: TextStyle(
                            color: AppTheme.emeraldPrimary,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'Real-Time Financial Intelligence Engine',
                    style: TextStyle(
                      color: AppTheme.textMediumEmphasis,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}
