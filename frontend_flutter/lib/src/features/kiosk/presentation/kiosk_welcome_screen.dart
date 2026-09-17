import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../../core/widgets/uniassist_logo.dart';
import 'assistant_fab.dart';

class KioskWelcomeScreen extends ConsumerStatefulWidget {
  const KioskWelcomeScreen({super.key});

  @override
  ConsumerState<KioskWelcomeScreen> createState() => _KioskWelcomeScreenState();
}

class _KioskWelcomeScreenState extends ConsumerState<KioskWelcomeScreen> {
  late Timer _clockTimer;
  DateTime _now = DateTime.now();
  bool _showSplash = true;

  @override
  void initState() {
    super.initState();
    _clockTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
    
    // Hide splash screen after 3 seconds
    Future.delayed(const Duration(milliseconds: 3000), () {
      if (mounted) {
        setState(() => _showSplash = false);
      }
    });
  }

  @override
  void dispose() {
    _clockTimer.cancel();
    super.dispose();
  }

  String _formatTime(DateTime dt) {
    final hour = dt.hour.toString().padLeft(2, '0');
    final minute = dt.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  String _formatDate(DateTime dt) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return '${days[dt.weekday - 1]}, ${months[dt.month - 1]} ${dt.day}, ${dt.year}';
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 800;

    return Stack(
      children: [
        Scaffold(
          floatingActionButton: const AssistantFab(),
          floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
          body: SafeArea(
            child: Column(
              children: [
                // Top Kiosk Header Bar
                _KioskTopBar(
                  timeStr: _formatTime(_now),
                  dateStr: _formatDate(_now),
                ),

                // Main Content Body
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 900),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'Welcome to UniAssist',
                              style: TextStyle(
                                fontSize: isCompact ? 32 : 46,
                                fontWeight: FontWeight.w900,
                                color: AppColors.ink,
                                letterSpacing: -0.5,
                              ),
                              textAlign: TextAlign.center,
                            ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1),
                            const SizedBox(height: 12),
                            Text(
                              'Choose how you would like to continue',
                              style: TextStyle(
                                fontSize: isCompact ? 18 : 22,
                                fontWeight: FontWeight.w500,
                                color: AppColors.muted,
                              ),
                              textAlign: TextAlign.center,
                            ).animate(delay: 200.ms).fadeIn(duration: 400.ms),
                            
                            SizedBox(height: isCompact ? 40 : 60),

                            // Two Large Cards
                            if (isCompact)
                              Column(
                                children: [
                                  _KioskCard(
                                    title: 'PUBLIC SERVICES',
                                    subtitle: 'No Login Required',
                                    icon: Icons.account_balance_rounded,
                                    iconColor: AppColors.teal,
                                    onTap: () => context.go('/services'),
                                  ).animate(delay: 400.ms).fadeIn().slideX(begin: -0.1),
                                  const SizedBox(height: 24),
                                  _KioskCard(
                                    title: 'STUDENT / STAFF',
                                    subtitle: 'Secure Login',
                                    icon: Icons.badge_outlined,
                                    iconColor: AppColors.primary,
                                    onTap: () => context.go('/login'),
                                  ).animate(delay: 500.ms).fadeIn().slideX(begin: 0.1),
                                ],
                              )
                            else
                              Row(
                                children: [
                                  Expanded(
                                    child: _KioskCard(
                                      title: 'PUBLIC SERVICES',
                                      subtitle: 'No Login Required',
                                      icon: Icons.account_balance_rounded,
                                      iconColor: AppColors.teal,
                                      onTap: () => context.go('/services'),
                                    ).animate(delay: 400.ms).fadeIn().slideX(begin: -0.1),
                                  ),
                                  const SizedBox(width: 32),
                                  Expanded(
                                    child: _KioskCard(
                                      title: 'STUDENT / STAFF',
                                      subtitle: 'Secure Login',
                                      icon: Icons.badge_outlined,
                                      iconColor: AppColors.primary,
                                      onTap: () => context.go('/login'),
                                    ).animate(delay: 500.ms).fadeIn().slideX(begin: 0.1),
                                  ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // Kiosk Footer Info Bar
                const _KioskBottomFooter(),
              ],
            ),
          ),
        ),

        // Splash Screen Overlay
        if (_showSplash)
          Positioned.fill(
            child: Container(
              color: Colors.white,
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.support_agent_rounded,
                      size: 100,
                      color: AppColors.primary,
                    ).animate().fadeIn(duration: 600.ms).scale(duration: 600.ms, curve: Curves.easeOutBack),
                    const SizedBox(height: 32),
                    const Text(
                      'Welcome to UniAssist',
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w800,
                        color: AppColors.ink,
                      ),
                    ).animate(delay: 500.ms).fadeIn(duration: 400.ms).slideY(begin: 0.2),
                    const SizedBox(height: 12),
                    const Text(
                      'Your friendly digital guide to everything on campus.',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                        color: AppColors.muted,
                      ),
                    ).animate(delay: 1000.ms).fadeIn(duration: 400.ms),
                  ],
                ).animate(delay: 2400.ms).fadeOut(duration: 500.ms),
              ),
            ),
          ),
      ],
    );
  }
}

class _KioskTopBar extends StatelessWidget {
  const _KioskTopBar({
    required this.timeStr,
    required this.dateStr,
  });

  final String timeStr;
  final String dateStr;

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 850;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      decoration: const BoxDecoration(
        color: AppColors.panel,
        border: Border(bottom: BorderSide(color: AppColors.line)),
      ),
      child: Row(
        children: [
          const UniAssistLogo(size: 34, showWordmark: true),
          const Spacer(),
          if (!isCompact) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.line),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.location_on_outlined, size: 16, color: AppColors.primary),
                  const SizedBox(width: 6),
                  const Text('Main Campus Kiosk', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.ink)),
                  const SizedBox(width: 10),
                  const Text('•', style: TextStyle(color: AppColors.muted)),
                  const SizedBox(width: 10),
                  Text('$dateStr  $timeStr', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.muted)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _KioskCard extends StatelessWidget {
  const _KioskCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.iconColor,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color iconColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        height: 280,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.line, width: 2),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 90,
              height: 90,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: iconColor, size: 48),
            ),
            const SizedBox(height: 24),
            Text(
              title,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w900,
                color: AppColors.ink,
                letterSpacing: 0.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: AppColors.muted,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _KioskBottomFooter extends StatelessWidget {
  const _KioskBottomFooter();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      decoration: const BoxDecoration(
        color: AppColors.panel,
        border: Border(top: BorderSide(color: AppColors.line)),
      ),
      child: Row(
        children: const [
          Icon(Icons.lock_clock_outlined, size: 16, color: AppColors.muted),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Sessions clear automatically after 5 minutes of inactivity for privacy.',
              style: TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w600),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          SizedBox(width: 12),
          Text(
            'UniAssist Self-Service Kiosk v2.0',
            style: TextStyle(fontSize: 13, color: AppColors.muted, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}
