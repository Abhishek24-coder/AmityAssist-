import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:flutter_animate/flutter_animate.dart';
import '../../../core/api_client.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../../core/utils/download_service.dart';
import '../../../core/services/page_context_service.dart';
import '../../auth/application/auth_provider.dart';
import 'withdrawal_providers.dart';

class WithdrawalHomeScreen extends ConsumerWidget {
  const WithdrawalHomeScreen({super.key});

  Future<void> _handleInitiate(BuildContext context, WidgetRef ref) async {
    final auth = ref.read(authProvider);
    if (!auth.isAuthenticated || auth.studentId == null || auth.isStaff) {
      showDialog(
        context: context,
        builder: (dialogCtx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.lock_person_rounded, color: AppColors.primary),
              SizedBox(width: 8),
              Text('Student Sign-In Required', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
          content: const Text(
            'Official university withdrawal, clearance gate tracking, and fee refund calculations require verified student identity.\n\nPlease sign in with your student credentials to proceed.',
            style: TextStyle(height: 1.4),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text('Cancel'),
            ),
            FilledButton.icon(
              onPressed: () {
                Navigator.pop(dialogCtx);
                context.push('/login');
              },
              icon: const Icon(Icons.login_rounded, size: 18),
              label: const Text('Sign In as Student'),
            ),
          ],
        ),
      );
      return;
    }

    // Check if student already has an active withdrawal request (enforce strictly once at a time)
    try {
      final dio = ref.read(apiClientProvider);
      final resp = await dio.get('/withdrawal/status/${auth.studentId}');
      final data = resp.data as Map<String, dynamic>;
      final hasRequest = data['has_request'] == true;
      final request = data['request'] as Map<String, dynamic>?;
      final status = (request?['status'] ?? '').toString().toLowerCase();
      final isTerminal = status == 'completed' || status == 'rejected' || status == 'cancelled';

      if (hasRequest && !isTerminal) {
        final refNo = request?['reference_no'] ?? 'AMITY-WTH';
        if (context.mounted) {
          showDialog(
            context: context,
            builder: (dialogCtx) => AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              title: const Row(
                children: [
                  Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 28),
                  SizedBox(width: 8),
                  Text('Active Request In Progress', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('You already have an active withdrawal request ($refNo).'),
                  const SizedBox(height: 12),
                  const Text(
                    'University regulations permit only one active withdrawal application per student at a time. Please track your current clearance status or wait for final sign-off.',
                    style: TextStyle(fontSize: 13, color: Colors.grey, height: 1.3),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogCtx),
                  child: const Text('Close'),
                ),
                FilledButton.icon(
                  onPressed: () {
                    Navigator.pop(dialogCtx);
                    context.push('/request-status');
                  },
                  icon: const Icon(Icons.track_changes_rounded, size: 18),
                  label: const Text('Track Current Request'),
                ),
              ],
            ),
          );
        }
        return;
      }
    } catch (_) {}

    if (context.mounted) {
      context.push('/withdrawal/flow');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final guide = ref.watch(withdrawalGuideProvider);

    final scaffold = Scaffold(
      appBar: AppBar(
        title: const Text('Withdrawal Services'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: FilledButton.icon(
              onPressed: () => _handleInitiate(context, ref),
              icon: const Icon(Icons.arrow_forward_rounded, size: 16),
              label: const Text('Initiate Withdrawal'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
              ),
            ),
          ),
        ],
      ),
      body: guide.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('Unable to load withdrawal guide: $error'),
          ),
        ),
        data: (data) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Quick Hero Action Banner
              Container(
                margin: const EdgeInsets.only(bottom: 14),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.primary, Color(0xFF26467A)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: 0.25),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(Icons.assignment_turned_in_rounded, color: Colors.white, size: 28),
                    ),
                    const SizedBox(width: 14),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Ready to Apply?',
                            style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                          SizedBox(height: 2),
                          Text(
                            'Start your 4-gate automated clearance and calculate refund eligibility.',
                            style: TextStyle(color: Colors.white70, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () => _handleInitiate(context, ref),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: AppColors.primary,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      child: const Text('Start Now', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ),
              _SectionCard(
                title: data.title,
                subtitle: data.summary,
                child: Text(data.principle),
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Digital Clearance Pipeline',
                subtitle: 'Parallel 4-department clearance. Zero physical running between offices.',
                child: Column(
                  children: [
                    _ClearanceGateTile(
                      title: 'Gate 1: Central Library',
                      subtitle: 'Book returns, outstanding book dues check',
                      icon: Icons.local_library_rounded,
                    ),
                    const Divider(height: 12),
                    _ClearanceGateTile(
                      title: 'Gate 2: Hostel & Mess Administration',
                      subtitle: 'Room vacation verification, mess dues',
                      icon: Icons.hotel_rounded,
                    ),
                    const Divider(height: 12),
                    _ClearanceGateTile(
                      title: 'Gate 3: Finance & Accounts Office',
                      subtitle: 'UGC refund percentage calculation, smart fee offsetting',
                      icon: Icons.account_balance_wallet_rounded,
                    ),
                    const Divider(height: 12),
                    _ClearanceGateTile(
                      title: 'Gate 4: Registrar Final Audit',
                      subtitle: 'Digital sign-off, TC/Migration issuance authorization',
                      icon: Icons.verified_user_rounded,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Required Documents',
                subtitle: 'Generated from the official withdrawal procedure',
                child: Column(
                  children: data.documents
                      .map(
                        (document) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(
                            document.mandatory ? Icons.assignment_turned_in : Icons.assignment_outlined,
                          ),
                          title: Text(document.name),
                          subtitle: Text(document.description),
                          trailing: Text(document.mandatory ? 'Required' : 'If needed'),
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Official Steps',
                subtitle: 'Follow the procedure without skipping stages',
                child: Column(
                  children: data.steps
                      .map(
                        (step) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: CircleAvatar(child: Text('${step.stepNumber}')),
                          title: Text(step.title),
                          subtitle: Text('${step.department}\n${step.timelineText}\n${step.description}'),
                          isThreeLine: true,
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Form Repository',
                subtitle: 'Official forms for download or kiosk printing',
                child: Column(
                  children: data.forms
                      .map(
                        (form) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.description_outlined),
                          title: Text(form.name),
                          subtitle: Text('${form.issuingDepartment}\n${form.description}'),
                          trailing: IconButton(
                            tooltip: 'Download ${form.name}',
                            icon: const Icon(Icons.download_rounded),
                            onPressed: () {
                              DownloadService.downloadFile(
                                form.fullDownloadUrl,
                                fileName: form.name,
                              );
                            },
                          ),
                          isThreeLine: true,
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 12),
              _SectionCard(
                title: 'Timeline Guidance',
                subtitle: 'Official timeline bands, not predictions',
                child: Column(
                  children: data.officialTimeline
                      .map(
                        (band) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.schedule_outlined),
                          title: Text(band.stage),
                          subtitle: Text(band.timeline),
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: 16),
              Center(
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => _handleInitiate(context, ref),
                    icon: const Icon(Icons.add_task_rounded),
                    label: const Text('Initiate Official Withdrawal Application', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.teal,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 80),
            ],
          );
        },
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _handleInitiate(context, ref),
        backgroundColor: AppColors.teal,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_task_rounded),
        label: const Text('Initiate Withdrawal'),
      ),
    );

    final highlight = ref.watch(buttonHighlightProvider);
    final isTargeted = highlight != null && highlight.toLowerCase().contains('withdrawal');

    if (isTargeted) {
      return Stack(
        children: [
          scaffold,
          Positioned(
            bottom: 16,
            left: 16,
            child: IgnorePointer(
              child: Container(
                width: 200,
                height: 56,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(color: Colors.blueAccent, width: 3),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.blueAccent.withValues(alpha: 0.5),
                      blurRadius: 20,
                      spreadRadius: 4,
                    ),
                  ],
                ),
              ).animate(onPlay: (controller) => controller.repeat(reverse: true)).scale(
                    begin: const Offset(1.0, 1.0),
                    end: const Offset(1.08, 1.08),
                    duration: 600.ms,
                  ),
            ),
          ),
        ],
      );
    }

    return scaffold;
  }
}

class _ClearanceGateTile extends StatelessWidget {
  const _ClearanceGateTile({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: Theme.of(context).colorScheme.primary, size: 22),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(subtitle),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 4),
            Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
            const Divider(height: 24),
            child,
          ],
        ),
      ),
    );
  }
}
