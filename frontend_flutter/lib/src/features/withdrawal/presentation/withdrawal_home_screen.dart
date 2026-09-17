import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/utils/download_service.dart';
import 'withdrawal_providers.dart';

class WithdrawalHomeScreen extends ConsumerWidget {
  const WithdrawalHomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final guide = ref.watch(withdrawalGuideProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Withdrawal Services'),
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
            ],
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/withdrawal/flow'),
        icon: const Icon(Icons.add),
        label: const Text('Initiate Withdrawal'),
      ),
    );
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
