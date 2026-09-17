import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../auth/application/auth_provider.dart';
import '../application/staff_provider.dart';
import 'staff_notesheet_screen.dart';
import 'staff_registry_screen.dart';
import 'staff_document_ocr_screen.dart';
import 'staff_accreditation_screen.dart';
import 'staff_institution_screen.dart';


class StaffDashboardScreen extends ConsumerWidget {
  const StaffDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statsAsync = ref.watch(adminStatsProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('Staff Admin Portal'),
        elevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.amityBlue, AppColors.amityYellow],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.white),
            onPressed: () {
              ref.read(authProvider.notifier).logout();
              context.go('/');
            },
            tooltip: 'Logout',
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: statsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error loading stats: $err')),
        data: (stats) {
          final pendingWithdrawals = stats['pending_withdrawals'] ?? 0;
          final activeGrievances = stats['active_grievances'] ?? 0;
          final pendingDocuments = stats['pending_documents'] ?? 0;
          final recentActivity = (stats['recent_activity'] as List?) ?? [];

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Main Content Area
              Expanded(
                flex: 3,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Overview',
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: AppColors.amityBlue,
                            ),
                      ).animate().fadeIn().slideX(),
                      const SizedBox(height: 24),

                      // Quick Action Cards
                      Row(
                        children: [
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Withdrawals Queue',
                              value: pendingWithdrawals.toString(),
                              subtitle: 'Pending Approvals',
                              icon: Icons.exit_to_app_rounded,
                              color: AppColors.urgentRed,
                              onTap: () => context.push('/staff/withdrawals'),
                            ).animate().fadeIn(delay: 100.ms).scale(),
                          ),
                          const SizedBox(width: 24),
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Grievance Desk',
                              value: activeGrievances.toString(),
                              subtitle: 'Active Cases',
                              icon: Icons.gavel_rounded,
                              color: const Color(0xFF7B1FA2), // Purple
                              onTap: () => context.push('/staff/grievances'),
                            ).animate().fadeIn(delay: 200.ms).scale(),
                          ),
                          const SizedBox(width: 24),
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Document Review',
                              value: pendingDocuments.toString(),
                              subtitle: 'Awaiting Verification',
                              icon: Icons.verified_user_rounded,
                              color: AppColors.successGreen,
                              onTap: () => context.push('/staff/documents'),
                            ).animate().fadeIn(delay: 300.ms).scale(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),

                      // Phase 23 & 24 Institutional Desks
                      Row(
                        children: [
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Digital Notesheets',
                              value: 'Active',
                              subtitle: 'Hierarchical Chain & In-Flight Edits',
                              icon: Icons.description_rounded,
                              color: AppColors.amityBlue,
                              onTap: () => context.push('/staff/notesheets'),
                            ).animate().fadeIn(delay: 350.ms).scale(),
                          ),
                          const SizedBox(width: 24),
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Status Registry',
                              value: 'Live',
                              subtitle: 'Real-Time Entry Locks & Roster',
                              icon: Icons.shield_rounded,
                              color: Colors.deepOrange,
                              onTap: () => context.push('/staff/registry'),
                            ).animate().fadeIn(delay: 400.ms).scale(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),

                      // Phase 25, 27, 28 Action Cards
                      Row(
                        children: [
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'OCR Document Cockpit',
                              value: 'Live',
                              subtitle: 'Identity Cross-Check & Extraction',
                              icon: Icons.document_scanner_rounded,
                              color: const Color(0xFF1565C0),
                              onTap: () => context.push('/staff/ocr'),
                            ).animate().fadeIn(delay: 450.ms).scale(),
                          ),
                          const SizedBox(width: 24),
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Accreditation Hub',
                              value: 'NAAC',
                              subtitle: 'CO/PO Attainment & Reports',
                              icon: Icons.assessment_rounded,
                              color: const Color(0xFF6A1B9A),
                              onTap: () => context.push('/staff/accreditation'),
                            ).animate().fadeIn(delay: 500.ms).scale(),
                          ),
                          const SizedBox(width: 24),
                          Expanded(
                            child: _buildActionCard(
                              context: context,
                              title: 'Institution Settings',
                              value: 'Config',
                              subtitle: 'White-Label & Clearance Chain',
                              icon: Icons.settings_applications_rounded,
                              color: const Color(0xFF00695C),
                              onTap: () => context.push('/staff/institution'),
                            ).animate().fadeIn(delay: 550.ms).scale(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 48),

                      // Analytics Section
                      Text(
                        'Weekly Processing Volume',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ).animate().fadeIn(delay: 400.ms),
                      const SizedBox(height: 24),
                      Container(
                        height: 300,
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(24),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.05),
                              blurRadius: 20,
                              offset: const Offset(0, 10),
                            ),
                          ],
                        ),
                        child: CustomPaint(
                          size: Size.infinite,
                          painter: _MockChartPainter(),
                        ),
                      ).animate().fadeIn(delay: 500.ms).slideY(begin: 0.1),
                    ],
                  ),
                ),
              ),

              // Side Panel (Recent Activity)
              Container(
                width: 350,
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: Border(left: BorderSide(color: Colors.grey.shade200)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'Recent Activity',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                    ),
                    const Divider(height: 1),
                    Expanded(
                      child: ListView.separated(
                        itemCount: recentActivity.length,
                        separatorBuilder: (ctx, idx) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final activity = recentActivity[index];
                          return ListTile(
                            contentPadding: const EdgeInsets.all(16),
                            leading: CircleAvatar(
                              backgroundColor: AppColors.amityBlue.withValues(alpha: 0.1),
                              child: const Icon(Icons.history_rounded, color: AppColors.amityBlue),
                            ),
                            title: Text(activity['action'] ?? ''),
                            subtitle: Text(activity['time'] ?? ''),
                          ).animate().fadeIn(delay: Duration(milliseconds: 600 + (100 * index)));
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildActionCard({
    required BuildContext context,
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.15),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(24),
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(icon, color: color, size: 32),
                    ),
                    Text(
                      value,
                      style: Theme.of(context).textTheme.displaySmall?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: color,
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(color: Colors.grey.shade600),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MockChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.fill
      ..color = AppColors.amityBlue.withValues(alpha: 0.8);

    final bgPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = Colors.grey.shade100;

    final barWidth = size.width / 14;
    final data = [40, 60, 20, 80, 50, 90, 70]; // Mock height percentages

    for (int i = 0; i < 7; i++) {
      final x = (size.width / 7) * i + (barWidth / 2);
      // Draw background bar
      final bgRect = Rect.fromLTWH(x, 0, barWidth, size.height);
      canvas.drawRRect(RRect.fromRectAndRadius(bgRect, const Radius.circular(8)), bgPaint);

      // Draw data bar
      final barHeight = size.height * (data[i] / 100);
      final y = size.height - barHeight;
      final rect = Rect.fromLTWH(x, y, barWidth, barHeight);
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(8)), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
