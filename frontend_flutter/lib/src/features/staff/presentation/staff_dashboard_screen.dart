import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../auth/application/auth_provider.dart';
import '../application/staff_provider.dart';

class StaffDashboardScreen extends ConsumerWidget {
  const StaffDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statsAsync = ref.watch(adminStatsProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        toolbarHeight: 70,
        titleSpacing: 24,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFF3B82F6).withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF3B82F6).withValues(alpha: 0.4)),
              ),
              child: const Icon(Icons.security, color: Color(0xFF60A5FA), size: 22),
            ),
            const SizedBox(width: 14),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    const Text(
                      'Staff Admin Portal',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFF334155)),
                      ),
                      child: const Text(
                        'ADMIN CONSOLE',
                        style: TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                const Text(
                  'Campus Operations, Workflow Clearance & Institutional Analytics',
                  style: TextStyle(
                    fontSize: 12,
                    color: Color(0xFF94A3B8),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ],
        ),
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [
                Color(0xFF0F172A),
                Color(0xFF1E293B),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border(
              bottom: BorderSide(color: Color(0xFF334155), width: 1),
            ),
          ),
        ),
        actions: [
          // User Profile Chip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF334155),
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.person_rounded, color: Colors.white, size: 16),
                SizedBox(width: 6),
                Text(
                  'Registrar Staff',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),

          // Logout Button
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Color(0xFFEF4444), size: 20),
            onPressed: () {
              ref.read(authProvider.notifier).logout();
              context.go('/');
            },
            tooltip: 'Logout Session',
          ),
          const SizedBox(width: 20),
        ],
      ),
      body: statsAsync.when(
        loading: () => const Center(
          child: CircularProgressIndicator(color: Color(0xFF2563EB)),
        ),
        error: (err, _) => Center(
          child: Text('Error loading stats: $err', style: const TextStyle(color: Colors.red)),
        ),
        data: (stats) {
          final pendingWithdrawals = stats['pending_withdrawals'] ?? 0;
          final activeGrievances = stats['active_grievances'] ?? 0;
          final pendingDocuments = stats['pending_documents'] ?? 0;
          final recentActivity = (stats['recent_activity'] as List?) ?? [];

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Main Dashboard Area
              Expanded(
                flex: 3,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Section Header with Quick Refresh
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: const [
                              Text(
                                'Executive Overview',
                                style: TextStyle(
                                  fontSize: 26,
                                  fontWeight: FontWeight.w900,
                                  color: Color(0xFF0F172A),
                                  letterSpacing: -0.5,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Real-time counters across digital clearance, forms, and compliance',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Color(0xFF64748B),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: const Color(0xFFE2E8F0)),
                            ),
                            child: Row(
                              children: const [
                                Icon(Icons.sync_rounded, size: 16, color: Color(0xFF2563EB)),
                                SizedBox(width: 6),
                                Text(
                                  'Auto-Sync Active',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: Color(0xFF2563EB),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ).animate().fadeIn().slideX(begin: -0.02),
                      const SizedBox(height: 28),

                      // Row 1: Priority Workflow Desks
                      Row(
                        children: [
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Withdrawals Queue',
                              value: pendingWithdrawals.toString(),
                              subtitle: 'Pending Approvals',
                              tag: 'PRIORITY',
                              icon: Icons.exit_to_app_rounded,
                              cardColor: const Color(0xFFEF4444),
                              onTap: () => context.push('/staff/withdrawals'),
                            ).animate().fadeIn(delay: 100.ms).scale(),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Grievance Desk',
                              value: activeGrievances.toString(),
                              subtitle: 'Active Cases',
                              tag: '48H SLA',
                              icon: Icons.gavel_rounded,
                              cardColor: const Color(0xFF8B5CF6),
                              onTap: () => context.push('/staff/grievances'),
                            ).animate(delay: 200.ms).fadeIn().scale(),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Document Review',
                              value: pendingDocuments.toString(),
                              subtitle: 'Awaiting Verification',
                              tag: 'ALL CLEAR',
                              icon: Icons.verified_user_rounded,
                              cardColor: const Color(0xFF10B981),
                              onTap: () => context.push('/staff/documents'),
                            ).animate(delay: 300.ms).fadeIn().scale(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),

                      // Row 2: Institutional Registers
                      Row(
                        children: [
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Digital Notesheets',
                              value: 'Active',
                              subtitle: 'Hierarchical Chain & In-Flight Edits',
                              tag: 'ROSTER',
                              icon: Icons.description,
                              cardColor: const Color(0xFF1E40AF),
                              onTap: () => context.push('/staff/notesheets'),
                            ).animate(delay: 350.ms).fadeIn().scale(),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Status Registry',
                              value: 'Live',
                              subtitle: 'Real-Time Entry Locks & Roster',
                              tag: 'MONITOR',
                              icon: Icons.verified_user_rounded,
                              cardColor: const Color(0xFFF97316),
                              onTap: () => context.push('/staff/registry'),
                            ).animate(delay: 400.ms).fadeIn().scale(),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Procedure Setup Wizard',
                              value: 'Builder',
                              subtitle: 'Custom Workflows & SLA Rules',
                              tag: 'ENGINE',
                              icon: Icons.auto_fix_high_rounded,
                              cardColor: const Color(0xFF0D9488),
                              onTap: () => context.push('/staff/procedures'),
                            ).animate(delay: 450.ms).fadeIn().scale(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),

                      // Row 3: Compliance & Extraction Hubs
                      Row(
                        children: [
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'OCR Document Cockpit',
                              value: 'Live',
                              subtitle: 'Identity Cross-Check & Extraction',
                              tag: 'AI ENGINE',
                              icon: Icons.document_scanner_rounded,
                              cardColor: const Color(0xFF2563EB),
                              onTap: () => context.push('/staff/ocr'),
                            ).animate(delay: 500.ms).fadeIn().scale(),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Accreditation Hub',
                              value: 'NAAC',
                              subtitle: 'CO/PO Attainment & Reports',
                              tag: 'AUDIT',
                              icon: Icons.verified_rounded,
                              cardColor: const Color(0xFF7C3AED),
                              onTap: () => context.push('/staff/accreditation'),
                            ).animate(delay: 550.ms).fadeIn().scale(),
                          ),
                          const SizedBox(width: 20),
                          Expanded(
                            child: _buildModernActionCard(
                              context: context,
                              title: 'Institution Settings',
                              value: 'Config',
                              subtitle: 'White-Label & Clearance Chain',
                              tag: 'SYSTEM',
                              icon: Icons.apartment_rounded,
                              cardColor: const Color(0xFF0F766E),
                              onTap: () => context.push('/staff/institution'),
                            ).animate(delay: 600.ms).fadeIn().scale(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 44),

                      // Weekly Processing Volume Analytics
                      Container(
                        padding: const EdgeInsets.all(28),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.03),
                              blurRadius: 20,
                              offset: const Offset(0, 10),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: const [
                                    Text(
                                      'Weekly Processing Volume',
                                      style: TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.w800,
                                        color: Color(0xFF0F172A),
                                      ),
                                    ),
                                    SizedBox(height: 4),
                                    Text(
                                      'Cumulative daily student clearance and request resolutions',
                                      style: TextStyle(
                                        fontSize: 13,
                                        color: Color(0xFF64748B),
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ],
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFEFF6FF),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(color: const Color(0xFFBFDBFE)),
                                  ),
                                  child: const Text(
                                    '410 Cases Resolved • 98.4% On-Time SLA',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w800,
                                      color: Color(0xFF1D4ED8),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 28),
                            SizedBox(
                              height: 240,
                              child: CustomPaint(
                                size: Size.infinite,
                                painter: _ModernChartPainter(),
                              ),
                            ),
                          ],
                        ),
                      ).animate().fadeIn(delay: 650.ms).slideY(begin: 0.05),
                    ],
                  ),
                ),
              ),

              // Side Panel (Recent Institutional Activity)
              Container(
                width: 380,
                decoration: const BoxDecoration(
                  color: Colors.white,
                  border: Border(left: BorderSide(color: Color(0xFFE2E8F0))),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: const BoxDecoration(
                        border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: const [
                              Icon(Icons.bolt_rounded, color: Color(0xFFF59E0B), size: 22),
                              SizedBox(width: 8),
                              Text(
                                'Recent Activity',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF0F172A),
                                ),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF1F5F9),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Text(
                              'REAL-TIME',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF475569),
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: recentActivity.isNotEmpty ? recentActivity.length : _fallbackActivities.length,
                        separatorBuilder: (ctx, idx) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final item = recentActivity.isNotEmpty
                              ? recentActivity[index]
                              : _fallbackActivities[index];

                          // Resolve dynamic icon and color if from backend
                          IconData resolvedIcon = Icons.history_rounded;
                          Color resolvedColor = const Color(0xFF2563EB);

                          if (item['icon'] is IconData) {
                            resolvedIcon = item['icon'] as IconData;
                          } else {
                            final type = (item['type'] ?? '').toString().toLowerCase();
                            if (type == 'notesheet') {
                              resolvedIcon = Icons.description_rounded;
                              resolvedColor = const Color(0xFF8B5CF6);
                            } else if (type == 'offset') {
                              resolvedIcon = Icons.account_balance_wallet_rounded;
                              resolvedColor = const Color(0xFF0D9488);
                            } else if (type == 'withdrawal') {
                              resolvedIcon = Icons.assignment_turned_in_rounded;
                              resolvedColor = const Color(0xFF2563EB);
                            } else if (type == 'grievance') {
                              resolvedIcon = Icons.gavel_rounded;
                              resolvedColor = const Color(0xFFF59E0B);
                            }
                          }

                          if (item['color'] is Color) {
                            resolvedColor = item['color'] as Color;
                          }

                          return Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8FAFC),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: const Color(0xFFE2E8F0)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  width: 38,
                                  height: 38,
                                  decoration: BoxDecoration(
                                    color: resolvedColor.withValues(alpha: 0.1),
                                    shape: BoxShape.circle,
                                  ),
                                  child: Icon(
                                    resolvedIcon,
                                    color: resolvedColor,
                                    size: 20,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        item['action'] ?? '',
                                        style: const TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w700,
                                          color: Color(0xFF0F172A),
                                          height: 1.3,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Row(
                                        children: [
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFFE2E8F0),
                                              borderRadius: BorderRadius.circular(4),
                                            ),
                                            child: Text(
                                              item['dept'] ?? 'Registry',
                                              style: const TextStyle(
                                                fontSize: 10,
                                                fontWeight: FontWeight.w700,
                                                color: Color(0xFF475569),
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          Text(
                                            item['time'] ?? 'Just now',
                                            style: const TextStyle(
                                              fontSize: 11,
                                              color: Color(0xFF94A3B8),
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ).animate().fadeIn(delay: Duration(milliseconds: 100 * index)).slideX(begin: 0.05);
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

  Widget _buildModernActionCard({
    required BuildContext context,
    required String title,
    required String value,
    required String subtitle,
    required String tag,
    required IconData icon,
    required Color cardColor,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFE2E8F0), width: 1.2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.03),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: cardColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: cardColor, size: 24),
                  ),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      color: cardColor,
                      letterSpacing: -0.5,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF0F172A),
                        letterSpacing: -0.2,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                      color: cardColor.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      tag,
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                        color: cardColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF64748B),
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }

  static final List<Map<String, dynamic>> _fallbackActivities = [
    {
      'action': 'Gate 2 (Accounts) cleared for Withdrawal #TK-904',
      'dept': 'Accounts Desk',
      'time': '2m ago',
      'icon': Icons.check_circle_rounded,
      'color': const Color(0xFF10B981),
    },
    {
      'action': 'Form AC-04 Attendance Condonation filed by STU001',
      'dept': 'Dean Office',
      'time': '14m ago',
      'icon': Icons.assignment_turned_in_rounded,
      'color': const Color(0xFF2563EB),
    },
    {
      'action': 'Smart Caution Deposit Offset ₹200 for Duplicate ID',
      'dept': 'Finance Section',
      'time': '32m ago',
      'icon': Icons.account_balance_wallet_rounded,
      'color': const Color(0xFF0D9488),
    },
    {
      'action': 'Urgent Grievance #GRV-102 routed to Proctor Cell',
      'dept': 'Proctor Office',
      'time': '1h ago',
      'icon': Icons.gavel_rounded,
      'color': const Color(0xFF8B5CF6),
    },
    {
      'action': 'Semester 4 Clearance sign-off verified for 28 students',
      'dept': 'Exam Cell',
      'time': '2h ago',
      'icon': Icons.verified_rounded,
      'color': const Color(0xFF3B82F6),
    },
    {
      'action': 'Digital Notesheet #NS-DISC-2026-088 approved by Proctor Cell',
      'dept': 'Proctor Office',
      'time': '3h ago',
      'icon': Icons.description_rounded,
      'color': const Color(0xFF8B5CF6),
    },
  ];
}

class _ModernChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final barBgPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = const Color(0xFFF1F5F9);

    final lineGridPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0
      ..color = const Color(0xFFE2E8F0);

    // Draw subtle horizontal grid lines
    for (int i = 1; i <= 3; i++) {
      final y = (size.height - 30) * (i / 4);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), lineGridPaint);
    }

    final days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Today'];
    final data = [42, 68, 28, 88, 54, 94, 76]; // Processed counts

    final double availableHeight = size.height - 36;
    final double barWidth = (size.width / days.length) * 0.44;

    for (int i = 0; i < days.length; i++) {
      final double slotWidth = size.width / days.length;
      final double x = slotWidth * i + (slotWidth - barWidth) / 2;

      // Draw background pillar
      final bgRect = Rect.fromLTWH(x, 0, barWidth, availableHeight);
      canvas.drawRRect(
        RRect.fromRectAndRadius(bgRect, const Radius.circular(8)),
        barBgPaint,
      );

      // Draw active gradient bar
      final double barHeight = availableHeight * (data[i] / 100);
      final double y = availableHeight - barHeight;
      final activeRect = Rect.fromLTWH(x, y, barWidth, barHeight);

      final isPeak = i == 5; // Friday peak
      final barPaint = Paint()
        ..shader = LinearGradient(
          colors: isPeak
              ? [const Color(0xFF3B82F6), const Color(0xFF1D4ED8)]
              : [const Color(0xFF60A5FA), const Color(0xFF2563EB)],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ).createShader(activeRect);

      canvas.drawRRect(
        RRect.fromRectAndRadius(activeRect, const Radius.circular(8)),
        barPaint,
      );

      // Draw label text
      final textSpan = TextSpan(
        text: days[i],
        style: TextStyle(
          color: i == 6 ? const Color(0xFF1D4ED8) : const Color(0xFF64748B),
          fontSize: 12,
          fontWeight: i == 6 ? FontWeight.w800 : FontWeight.w600,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(
        canvas,
        Offset(x + (barWidth - textPainter.width) / 2, size.height - 20),
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
