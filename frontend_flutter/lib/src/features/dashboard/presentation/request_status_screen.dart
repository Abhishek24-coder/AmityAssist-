import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../core/api_client.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../../core/utils/download_service.dart';
import '../../auth/application/auth_provider.dart';

/// Fetch all active workflows for the student.
final workflowsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final studentId = ref.watch(authProvider).studentId;
  if (studentId == null) return [];

  final dio = ref.watch(apiClientProvider);
  try {
    final response = await dio.get('/workflows', queryParameters: {
      'student_id': studentId,
    });
    return (response.data as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  } catch (e) {
    // Fallback: try the status endpoint
    try {
      final response = await dio.get('/status/$studentId');
      final data = response.data as Map<String, dynamic>;
      if (data['has_request'] == true) {
        return [data];
      }
    } catch (_) {}
    return [];
  }
});

class RequestStatusScreen extends ConsumerWidget {
  const RequestStatusScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final workflowsAsync = ref.watch(workflowsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Request Status')),
      body: workflowsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error: $err')),
        data: (workflows) {
          if (workflows.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.inbox_outlined, size: 64, color: Colors.grey.shade400),
                  const SizedBox(height: 16),
                  Text('No active requests', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text(
                    'Your withdrawal, grievance, and scholarship\nworkflows will appear here.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(workflowsProvider),
            child: ListView.builder(
              itemCount: workflows.length,
              padding: const EdgeInsets.all(16),
              itemBuilder: (context, index) {
                final wf = workflows[index];
                return _WorkflowCard(workflow: wf)
                    .animate()
                    .fadeIn(
                      delay: Duration(milliseconds: 80 * index),
                      duration: 350.ms,
                    )
                    .slideY(begin: 0.08);
              },
            ),
          );
        },
      ),
    );
  }
}

class _WorkflowCard extends StatelessWidget {
  const _WorkflowCard({required this.workflow});
  final Map<String, dynamic> workflow;

  @override
  Widget build(BuildContext context) {
    final type = (workflow['procedure_type'] ?? workflow['type'] ?? 'request')
        .toString()
        .toUpperCase();
    final status = workflow['status'] ?? 'UNKNOWN';
    final refNo = workflow['workflow_id'] ?? workflow['reference_no'] ?? '';
    final department = workflow['current_department'] ?? '';
    final reason = workflow['reason'] ?? '';
    final checklist = workflow['checklist'] as List? ?? [];
    final statusFlow = workflow['status_flow'] as List? ?? [];
    final gates = workflow['gates'] as List? ?? [];
    final voucher = workflow['voucher'] is Map
        ? Map<String, dynamic>.from(workflow['voucher'] as Map)
        : null;

    final typeColor = switch (type) {
      'WITHDRAWAL' => AppColors.urgentRed,
      'GRIEVANCE' => const Color(0xFF7B1FA2),
      'SCHOLARSHIP' => const Color(0xFFF9A825),
      _ => AppColors.amityBlue,
    };

    final typeIcon = switch (type) {
      'WITHDRAWAL' => Icons.exit_to_app_rounded,
      'GRIEVANCE' => Icons.gavel_rounded,
      'SCHOLARSHIP' => Icons.workspace_premium_rounded,
      _ => Icons.track_changes_rounded,
    };

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: typeColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(typeIcon, color: typeColor, size: 26),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '$type Workflow',
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                      ),
                      if (refNo.toString().isNotEmpty)
                        Text(
                          'Ref: $refNo',
                          style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                        ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: typeColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    status.toString().toUpperCase().replaceAll('_', ' '),
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: typeColor,
                    ),
                  ),
                ),
              ],
            ),

            if (department.toString().isNotEmpty) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  const Icon(Icons.business_rounded, size: 16, color: Colors.grey),
                  const SizedBox(width: 6),
                  Text(
                    'Current: $department',
                    style: TextStyle(fontSize: 14, color: Colors.grey.shade700),
                  ),
                ],
              ),
            ],

            if (reason.toString().isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                'Reason: $reason',
                style: TextStyle(fontSize: 14, color: Colors.grey.shade700),
              ),
            ],

            // Status flow timeline
            if (statusFlow.isNotEmpty) ...[
              const Divider(height: 24),
              _WorkflowTimeline(statusFlow: statusFlow, currentStatus: status.toString()),
            ],

            // Digital Clearance Gates (Phase 21)
            if (gates.isNotEmpty) ...[
              const Divider(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Department Clearance Gates',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.amityBlue.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      '4-Stage Audit',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.amityBlue),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              _ClearanceGatesWidget(gates: gates),
            ],

            // Clearance Voucher Details
            if (voucher != null) ...[
              const Divider(height: 24),
              _ClearanceVoucherCard(voucher: voucher),
            ],

            // Checklist
            if (checklist.isNotEmpty) ...[
              const Divider(height: 24),
              Text('Checklist', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...checklist.map((item) {
                final itemMap = item is Map ? Map<String, dynamic>.from(item) : <String, dynamic>{};
                final name = itemMap['name'] ?? itemMap['item'] ?? 'Item';
                final completed = itemMap['completed'] ?? false;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    children: [
                      Icon(
                        completed ? Icons.check_circle : Icons.radio_button_unchecked,
                        size: 20,
                        color: completed ? AppColors.successGreen : Colors.grey,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          name.toString(),
                          style: TextStyle(
                            fontSize: 14,
                            decoration: completed ? TextDecoration.lineThrough : null,
                            color: completed ? Colors.grey : null,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}

class _ClearanceGatesWidget extends StatelessWidget {
  const _ClearanceGatesWidget({required this.gates});
  final List gates;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: gates.map((g) {
        final gate = g is Map ? Map<String, dynamic>.from(g) : <String, dynamic>{};
        final dept = gate['department']?.toString().toUpperCase() ?? '';
        final status = gate['status']?.toString().toUpperCase() ?? 'PENDING';
        final dues = (gate['dues_amount'] as num?)?.toDouble() ?? 0.0;
        final officer = gate['officer_name']?.toString() ?? '';
        final notes = gate['notes']?.toString() ?? '';

        final isCleared = status == 'CLEARED';
        final isFlagged = status == 'FLAG_DUES';

        final icon = isCleared
            ? Icons.check_circle_rounded
            : (isFlagged ? Icons.warning_amber_rounded : Icons.pending_outlined);

        final color = isCleared
            ? AppColors.successGreen
            : (isFlagged ? AppColors.amityYellow : Colors.grey);

        final deptLabel = switch (dept) {
          'LIBRARY' => 'Central Library',
          'HOSTEL' => 'Hostel & Mess Office',
          'ACCOUNTS' => 'Finance & Accounts',
          'REGISTRAR' => 'Registrar Audit',
          _ => dept,
        };

        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.07),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              Icon(icon, color: color, size: 22),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      deptLabel,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                    ),
                    if (officer.isNotEmpty)
                      Text('Signed by: $officer', style: TextStyle(fontSize: 11, color: Colors.grey.shade700)),
                    if (notes.isNotEmpty)
                      Text('Note: $notes', style: TextStyle(fontSize: 11, color: Colors.grey.shade700)),
                  ],
                ),
              ),
              if (dues > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.urgentRed.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    '₹${dues.toStringAsFixed(0)} Dues',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.urgentRed),
                  ),
                )
              else
                Text(
                  status,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _ClearanceVoucherCard extends StatelessWidget {
  const _ClearanceVoucherCard({required this.voucher});
  final Map<String, dynamic> voucher;

  @override
  Widget build(BuildContext context) {
    final refNo = voucher['reference_no'] ?? '';
    final refund = (voucher['net_refundable_amount'] as num?)?.toDouble() ?? 0.0;
    final caution = (voucher['caution_deposit_balance'] as num?)?.toDouble() ?? 10000.0;
    final clause = voucher['ordinance_clause'] ?? '';
    final offsetDeduction = (10000.0 - caution).clamp(0.0, 10000.0);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.amityBlue.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.receipt_long_rounded, color: AppColors.amityBlue, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Digital Clearance Voucher',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.amityBlue),
              ),
              const Spacer(),
              if (refNo.toString().isNotEmpty)
                Text(
                  refNo.toString(),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Estimated Net Refund:', style: TextStyle(fontSize: 13, color: Colors.grey)),
              Text(
                '₹${refund.toStringAsFixed(2)}',
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppColors.successGreen),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Refundable Caution Deposit:', style: TextStyle(fontSize: 13, color: Colors.grey)),
              Text(
                '₹${caution.toStringAsFixed(2)}',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.ink),
              ),
            ],
          ),
          if (offsetDeduction > 0) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.amityYellow.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_fix_high_rounded, size: 14, color: AppColors.amityYellow),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Smart Offset: ₹${offsetDeduction.toStringAsFixed(0)} deducted from deposit. Zero offline payment required.',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.brown),
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (clause.toString().isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              'Ordinance: $clause',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
            ),
          ],
          if (refNo.toString().isNotEmpty) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () {
                  DownloadService.downloadFile(
                    'http://127.0.0.1:8000/api/withdrawal/$refNo/slip',
                    fileName: 'TOKEN-$refNo.pdf',
                  );
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Downloading Official QR Token Slip for $refNo...'),
                      backgroundColor: AppColors.amityBlue,
                    ),
                  );
                },
                icon: const Icon(Icons.qr_code_2_rounded, size: 18),
                label: const Text('Download / Print QR Token Slip'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.amityBlue,
                  side: const BorderSide(color: AppColors.amityBlue),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _WorkflowTimeline extends StatelessWidget {
  const _WorkflowTimeline({required this.statusFlow, required this.currentStatus});
  final List statusFlow;
  final String currentStatus;

  @override
  Widget build(BuildContext context) {
    final currentIdx = statusFlow.indexWhere(
      (s) => s.toString().toLowerCase() == currentStatus.toLowerCase(),
    );

    return SizedBox(
      height: 64,
      child: Row(
        children: List.generate(statusFlow.length * 2 - 1, (i) {
          if (i.isOdd) {
            final stepIdx = i ~/ 2;
            final isActive = stepIdx < currentIdx;
            return Expanded(
              child: Container(
                height: 3,
                color: isActive ? AppColors.successGreen : Colors.grey.shade300,
              ),
            );
          }

          final stepIdx = i ~/ 2;
          final isActive = stepIdx <= currentIdx;
          final isCurrent = stepIdx == currentIdx;
          final label = statusFlow[stepIdx]
              .toString()
              .replaceAll('_', '\n')
              .toUpperCase();

          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: isCurrent ? 26 : 20,
                height: isCurrent ? 26 : 20,
                decoration: BoxDecoration(
                  color: isActive ? AppColors.successGreen : Colors.grey.shade300,
                  shape: BoxShape.circle,
                  border:
                      isCurrent ? Border.all(color: AppColors.successGreen, width: 3) : null,
                ),
                child:
                    isActive ? const Icon(Icons.check, size: 12, color: Colors.white) : null,
              ),
              const SizedBox(height: 4),
              SizedBox(
                width: 60,
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 8,
                    fontWeight: isCurrent ? FontWeight.w700 : FontWeight.w400,
                    color: isActive ? AppColors.successGreen : Colors.grey,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}
