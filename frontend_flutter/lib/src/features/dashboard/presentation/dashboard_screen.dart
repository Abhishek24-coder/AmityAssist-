import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../../core/widgets/uniassist_logo.dart';
import '../../auth/application/auth_provider.dart';
import '../../notifications/application/notifications_provider.dart';
import '../../student/application/student_provider.dart';
import '../../staff/application/institution_modules_provider.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final studentAsync = ref.watch(studentProfileProvider);
    final unreadCount = ref.watch(unreadNotificationCountProvider);
    final modules = ref.watch(institutionModulesProvider).value ?? const {};

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 76,
        title: const UniAssistLogo(size: 42, showWordmark: true),
        actions: [
          _NotificationButton(count: unreadCount),
          const SizedBox(width: 8),
          IconButton(
            tooltip: 'End session',
            icon: const Icon(Icons.logout_rounded),
            onPressed: () {
              ref.read(authProvider.notifier).logout();
              context.go('/');
            },
          ),
          const SizedBox(width: 20),
        ],
      ),
      body: SafeArea(
        top: false,
        child: studentAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => _ErrorPanel(message: 'Unable to load dashboard: $error'),
          data: (student) {
            if (student == null) {
              return const _ErrorPanel(message: 'No student profile is active.');
            }
            final activeServices = _services(context, modules);

            return SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(28, 20, 28, 36),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _IdentityPanel(student: student).animate().fadeIn(duration: 350.ms).slideY(begin: 0.04),
                  const SizedBox(height: 22),
                  _MetricsRow(student: student).animate().fadeIn(delay: 100.ms, duration: 350.ms),
                  const SizedBox(height: 28),
                  Text('Student Services', style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 14),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final width = constraints.maxWidth;
                      final columns = width >= 1100 ? 4 : width >= 720 ? 3 : 2;
                      return GridView.count(
                        crossAxisCount: columns,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        mainAxisSpacing: 14,
                        crossAxisSpacing: 14,
                        childAspectRatio: width >= 720 ? 1.45 : 1.05,
                        children: activeServices
                            .asMap()
                            .entries
                            .map((entry) => entry.value.animate().fadeIn(
                                  delay: Duration(milliseconds: entry.key * 45),
                                  duration: 260.ms,
                                ))
                            .toList(),
                      );
                    },
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  List<Widget> _services(BuildContext context, Map<String, bool> modules) {
    final list = <Widget>[];

    if (modules['withdrawal'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Withdrawal',
          subtitle: 'Guidance, checklist, forms, status',
          icon: Icons.assignment_return_rounded,
          color: AppColors.danger,
          route: '/withdrawal',
        ),
      );
    }

    if (modules['academics'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Academics',
          subtitle: 'CGPA, attendance, exams, back papers',
          icon: Icons.menu_book_rounded,
          color: AppColors.primary,
          route: '/academics',
        ),
      );
    }

    if (modules['scholarships'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Scholarships',
          subtitle: 'Eligibility and applications',
          icon: Icons.workspace_premium_rounded,
          color: AppColors.gold,
          route: '/scholarship',
        ),
      );
    }

    if (modules['grievance'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Grievances',
          subtitle: 'File and track student issues',
          icon: Icons.rule_rounded,
          color: const Color(0xFF6F4CB2),
          route: '/grievance',
        ),
      );
    }

    if (modules['documents'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Documents',
          subtitle: 'Upload, OCR, verification status',
          icon: Icons.source_rounded,
          color: AppColors.teal,
          route: '/documents',
        ),
      );
    }

    list.add(
      _ServiceTile(
        title: 'Request Status',
        subtitle: 'Track workflow progress',
        icon: Icons.timeline_rounded,
        color: const Color(0xFF2E6EB5),
        route: '/request-status',
      ),
    );

    if (modules['notices'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Notices',
          subtitle: 'Personalized university updates',
          icon: Icons.campaign_rounded,
          color: const Color(0xFFB96922),
          route: '/notices',
        ),
      );
    }

    if (modules['forms'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'Download Forms',
          subtitle: 'Official formats, applications & requisitions',
          icon: Icons.folder_open_rounded,
          color: const Color(0xFF0F766E),
          route: '/forms',
        ),
      );
    }

    if (modules['voice_ai'] ?? true) {
      list.add(
        _ServiceTile(
          title: 'AI Digital Counselor',
          subtitle: 'Instant voice & chat advisor for live request tracking, procedures & policy clearances',
          icon: Icons.support_agent_rounded,
          color: AppColors.teal,
          route: '/chat',
          badge: '24/7 AI',
        ),
      );
    }

    return list;
  }
}

class _IdentityPanel extends StatelessWidget {
  const _IdentityPanel({required this.student});

  final StudentProfile student;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.line),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 760;
          final details = [
            _Detail(label: 'Student ID', value: student.id),
            _Detail(label: 'Course', value: student.course),
            _Detail(label: 'Branch', value: student.branch),
            _Detail(label: 'Semester', value: '${student.semester}'),
            _Detail(label: 'Hostel', value: student.hostelStatus),
          ];

          return Flex(
            direction: compact ? Axis.vertical : Axis.horizontal,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (compact)
                _IdentityCopy(student: student)
              else
                Expanded(
                  flex: 2,
                  child: _IdentityCopy(student: student),
                ),
              if (!compact) const SizedBox(width: 28) else const SizedBox(height: 18),
              if (compact)
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: details.map((item) => _InfoPill(detail: item)).toList(),
                )
              else
                Expanded(
                  flex: 3,
                  child: Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: details.map((item) => _InfoPill(detail: item)).toList(),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _IdentityCopy extends StatelessWidget {
  const _IdentityCopy({required this.student});

  final StudentProfile student;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Welcome, ${student.name}', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text(
          'Use the kiosk to complete university services without waiting at multiple counters.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.muted),
        ),
      ],
    );
  }
}

class _MetricsRow extends StatelessWidget {
  const _MetricsRow({required this.student});

  final StudentProfile student;

  @override
  Widget build(BuildContext context) {
    final paid = student.feeStatus.toLowerCase().contains('paid') || student.feeStatus.toLowerCase().contains('clear');
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 720;
        final cards = [
          _MetricCard(label: 'CGPA', value: student.cgpa.toStringAsFixed(2), icon: Icons.trending_up_rounded, color: AppColors.teal),
          _MetricCard(label: 'Attendance', value: '${student.attendance}%', icon: Icons.event_available_rounded, color: AppColors.primary),
          _MetricCard(label: 'Fee Status', value: student.feeStatus, icon: Icons.account_balance_wallet_rounded, color: paid ? AppColors.success : AppColors.danger),
        ];
        if (compact) {
          return Column(
            children: cards.map((card) => Padding(padding: const EdgeInsets.only(bottom: 12), child: card)).toList(),
          );
        }
        return Row(
          children: cards
              .map((card) => Expanded(child: Padding(padding: const EdgeInsets.only(right: 12), child: card)))
              .toList(),
        );
      },
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value, required this.icon, required this.color});

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: color, size: 27),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 4),
                  Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.titleLarge),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ServiceTile extends StatelessWidget {
  const _ServiceTile({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.route,
    this.badge,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final String route;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => context.push(route),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, color: color, size: 27),
                  ),
                  const Spacer(),
                  if (badge != null)
                    Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        badge!,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          color: color,
                        ),
                      ),
                    ),
                  const Icon(Icons.arrow_forward_rounded, color: AppColors.muted),
                ],
              ),
              const Spacer(),
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 6),
              Text(subtitle, maxLines: 2, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
      ),
    );
  }
}

class _NotificationButton extends StatelessWidget {
  const _NotificationButton({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        IconButton(
          tooltip: 'Notifications',
          icon: const Icon(Icons.notifications_outlined),
          onPressed: () => context.push('/notifications'),
        ),
        if (count > 0)
          Positioned(
            top: 14,
            right: 8,
            child: Container(
              width: 18,
              height: 18,
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                color: AppColors.danger,
                shape: BoxShape.circle,
              ),
              child: Text(
                count > 9 ? '9+' : '$count',
                style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800),
              ),
            ),
          ),
      ],
    );
  }
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({required this.detail});

  final _Detail detail;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 150),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.primarySoft,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(detail.label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 2),
          Text(detail.value, maxLines: 1, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

class _Detail {
  const _Detail({required this.label, required this.value});

  final String label;
  final String value;
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(message, style: Theme.of(context).textTheme.titleMedium),
        ),
      ),
    );
  }
}
