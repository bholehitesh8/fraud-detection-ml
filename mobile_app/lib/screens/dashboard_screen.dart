import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../services/auth_service.dart';
import '../theme/app_theme.dart';
import 'analytics_screen.dart';
import 'history_screen.dart';
import 'landing_screen.dart';
import 'prediction_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _currentIndex = 0;

  final List<Widget> _pages = const [
    PredictionScreen(),
    HistoryScreen(),
    AnalyticsScreen(),
    _SettingsTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: AppTheme.darkGraphiteSurface,
          indicatorColor: AppTheme.emeraldPrimary.withOpacity(0.2),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const IconThemeData(color: AppTheme.emeraldPrimary);
            }
            return const IconThemeData(color: AppTheme.textMediumEmphasis);
          }),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const TextStyle(
                color: AppTheme.emeraldPrimary,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              );
            }
            return const TextStyle(
              color: AppTheme.textMediumEmphasis,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            );
          }),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.bolt_outlined),
              selectedIcon: Icon(Icons.bolt_rounded),
              label: 'Scoring',
            ),
            NavigationDestination(
              icon: Icon(Icons.history_outlined),
              selectedIcon: Icon(Icons.history_rounded),
              label: 'History',
            ),
            NavigationDestination(
              icon: Icon(Icons.insights_outlined),
              selectedIcon: Icon(Icons.insights_rounded),
              label: 'Analytics',
            ),
            NavigationDestination(
              icon: Icon(Icons.account_circle_outlined),
              selectedIcon: Icon(Icons.account_circle_rounded),
              label: 'Account',
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsTab extends StatelessWidget {
  const _SettingsTab();

  Future<void> _handleLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.darkGraphiteCard,
        title: const Text('Confirm Disconnect'),
        content: const Text('Are you sure you want to end your session?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.errorRed),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await AuthService().logout();
      if (!context.mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LandingScreen()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = AuthService().currentUser;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Operator Profile'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppTheme.darkGraphiteBackground,
                          shape: BoxShape.circle,
                          border: Border.all(color: AppTheme.emeraldPrimary, width: 1.5),
                        ),
                        child: const Icon(
                          Icons.person_outline_rounded,
                          color: AppTheme.emeraldPrimary,
                          size: 36,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        user?.username ?? 'Analyst',
                        style: const TextStyle(
                          color: AppTheme.textHighEmphasis,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        user?.email ?? 'operator@fraudguard.local',
                        style: const TextStyle(
                          color: AppTheme.textMediumEmphasis,
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.tealSecondary.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.tealSecondary, width: 0.8),
                        ),
                        child: Text(
                          (user?.role ?? 'ANALYST').toUpperCase(),
                          style: const TextStyle(
                            color: AppTheme.tealSecondary,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Backend Gateway Configuration',
                        style: TextStyle(
                          color: AppTheme.textHighEmphasis,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Divider(),
                      const SizedBox(height: 12),
                      const Text(
                        'Base URL',
                        style: TextStyle(color: AppTheme.textMediumEmphasis, fontSize: 12),
                      ),
                      const SizedBox(height: 4),
                      SelectableText(
                        ApiConfig.baseUrl,
                        style: const TextStyle(
                          color: AppTheme.textHighEmphasis,
                          fontSize: 13,
                          fontFamily: 'monospace',
                        ),
                      ),
                      const SizedBox(height: 14),
                      const Text(
                        'Authentication Mechanism',
                        style: TextStyle(color: AppTheme.textMediumEmphasis, fontSize: 12),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Flask Encrypted Session Cookie (Cookie: session=...)',
                        style: TextStyle(
                          color: AppTheme.textHighEmphasis,
                          fontSize: 12.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              OutlinedButton.icon(
                onPressed: () => _handleLogout(context),
                icon: const Icon(Icons.logout_rounded, color: AppTheme.errorRed),
                label: const Text('Disconnect & Sign Out', style: TextStyle(color: AppTheme.errorRed)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppTheme.errorRed),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
