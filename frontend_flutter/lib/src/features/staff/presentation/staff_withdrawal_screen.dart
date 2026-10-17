import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../application/staff_provider.dart';

class StaffWithdrawalScreen extends ConsumerStatefulWidget {
  const StaffWithdrawalScreen({super.key});

  @override
  ConsumerState<StaffWithdrawalScreen> createState() => _StaffWithdrawalScreenState();
}

class _StaffWithdrawalScreenState extends ConsumerState<StaffWithdrawalScreen> {
  final Set<int> _selectedIds = {};
  String _filterStatus = 'PENDING';

  @override
  Widget build(BuildContext context) {
    final requestsAsync = ref.watch(adminRequestsProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('Withdrawals Queue & Digital Clearance'),
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
            child: Row(
              children: [
                _buildTab('PENDING', 'Pending'),
                const SizedBox(width: 8),
                _buildTab('APPROVED', 'Approved'),
                const SizedBox(width: 8),
                _buildTab('REJECTED', 'Rejected'),
                const Spacer(),
                if (_selectedIds.isNotEmpty && _filterStatus == 'PENDING')
                  FilledButton.icon(
                    onPressed: () async {
                      await ref.read(staffActionsProvider).batchApproveRequests(_selectedIds.toList());
                      setState(() => _selectedIds.clear());
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Batch approval successful')),
                        );
                      }
                    },
                    icon: const Icon(Icons.check_circle_rounded),
                    label: Text('Approve Selected (${_selectedIds.length})'),
                    style: FilledButton.styleFrom(backgroundColor: AppColors.successGreen),
                  ).animate().fadeIn().scale(),
              ],
            ),
          ),
        ),
      ),
      body: requestsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error: $err')),
        data: (requests) {
          final filtered = requests
              .where((r) => r['status'].toString().toUpperCase() == _filterStatus)
              .toList();

          if (filtered.isEmpty) {
            return const Center(child: Text('No requests found.'));
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 10,
                  )
                ],
              ),
              child: DataTable(
                headingRowColor: WidgetStateProperty.all(Colors.grey.shade50),
                columns: const [
                  DataColumn(label: Text('ID')),
                  DataColumn(label: Text('Student ID')),
                  DataColumn(label: Text('Reason')),
                  DataColumn(label: Text('Date')),
                  DataColumn(label: Text('Status')),
                  DataColumn(label: Text('Actions')),
                ],
                rows: filtered.map((req) {
                  final id = req['id'] as int;
                  final isSelected = _selectedIds.contains(id);

                  return DataRow(
                    selected: isSelected,
                    onSelectChanged: _filterStatus == 'PENDING'
                        ? (selected) {
                            setState(() {
                              if (selected == true) {
                                _selectedIds.add(id);
                              } else {
                                _selectedIds.remove(id);
                              }
                            });
                          }
                        : null,
                    cells: [
                      DataCell(Text('#$id')),
                      DataCell(
                        Text(
                          req['student_id']?.toString() ?? '',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                      DataCell(Text(req['reason']?.toString() ?? '')),
                      DataCell(Text(req['date']?.toString() ?? '')),
                      DataCell(
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          decoration: BoxDecoration(
                            color: _getStatusColor(req['status'].toString()).withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            req['status'].toString(),
                            style: TextStyle(
                              color: _getStatusColor(req['status'].toString()),
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                      DataCell(
                        Row(
                          children: [
                            if (_filterStatus == 'PENDING') ...[
                              TextButton(
                                onPressed: () {
                                  ref.read(staffActionsProvider).updateRequestStatus(id, 'approved');
                                },
                                child: const Text('Approve', style: TextStyle(color: AppColors.successGreen)),
                              ),
                              TextButton(
                                onPressed: () {
                                  ref.read(staffActionsProvider).updateRequestStatus(id, 'rejected');
                                },
                                child: const Text('Reject', style: TextStyle(color: AppColors.urgentRed)),
                              ),
                            ],
                            IconButton(
                              icon: const Icon(Icons.rule_folder_outlined, color: AppColors.amityBlue),
                              tooltip: 'Department Clearance Sign-off',
                              onPressed: () => _showClearanceDialog(context, req),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ).animate().fadeIn().slideY(begin: 0.05),
          );
        },
      ),
    );
  }

  void _showClearanceDialog(BuildContext context, Map<dynamic, dynamic> req) {
    _showDossierAndClearanceDialog(context, req);
  }

  void _showDossierAndClearanceDialog(BuildContext context, Map<dynamic, dynamic> req) {
    final rawId = req['id'];
    final int id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '0') ?? 0;
    final refNo = req['reference_no']?.toString().isNotEmpty == true
        ? req['reference_no'].toString()
        : 'AMITY-WTH-2026-$id';

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        int selectedTabIndex = 0; // 0: Documents & Checklist, 1: Clearance Gates, 2: Send Message & History
        Map<String, dynamic>? dossier;
        bool isLoading = true;
        String? loadError;

        // Form state for Clearance
        String selectedDept = 'LIBRARY';
        String selectedAction = 'CLEAR';
        double duesAmount = 0.0;
        bool autoOffsetDeposit = true;
        final officerController = TextEditingController(text: 'Staff Desk Officer');
        final notesController = TextEditingController();
        final duesController = TextEditingController(text: '0');

        // Form state for Message
        final messageController = TextEditingController();
        String selectedNewStatus = 'KEEP_CURRENT';

        return StatefulBuilder(
          builder: (context, setDialogState) {
            void loadDossier() async {
              try {
                final data = await ref.read(staffActionsProvider).fetchRequestReviewDetails(id);
                setDialogState(() {
                  dossier = data;
                  isLoading = false;
                });
              } catch (e) {
                setDialogState(() {
                  loadError = e.toString();
                  isLoading = false;
                });
              }
            }

            if (isLoading && dossier == null && loadError == null) {
              loadDossier();
            }

            final studentMap = (dossier?['student'] as Map?) ?? (dossier?['request'] as Map?) ?? {};
            final documents = (dossier?['documents'] as List? ?? []);
            final checklist = (dossier?['checklist'] as List? ?? []);
            final gates = (dossier?['gates'] as List? ?? []);
            final events = (dossier?['events'] as List? ?? []);
            final currentStatus = (dossier?['request']?['status'] ?? req['status'] ?? 'pending').toString().toUpperCase();

            return AlertDialog(
              backgroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              titlePadding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
              contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              title: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.amityBlue.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.folder_shared_rounded, color: AppColors.amityBlue, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              'Withdrawal Dossier & Clearance',
                              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                            ),
                            const Spacer(),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                              decoration: BoxDecoration(
                                color: _getStatusColor(currentStatus).withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                currentStatus,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: _getStatusColor(currentStatus),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Ref: $refNo • Student: ${studentMap['student_name'] ?? studentMap['name'] ?? req['student_id']} (${studentMap['course'] ?? 'UG'} Sem ${studentMap['semester'] ?? '1'})',
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              content: SizedBox(
                width: 640,
                height: 520,
                child: isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : Column(
                        children: [
                          // Tab selector bar
                          Container(
                            decoration: BoxDecoration(
                              color: Colors.grey.shade100,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            padding: const EdgeInsets.all(4),
                            child: Row(
                              children: [
                                Expanded(
                                  child: InkWell(
                                    onTap: () => setDialogState(() => selectedTabIndex = 0),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(vertical: 8),
                                      decoration: BoxDecoration(
                                        color: selectedTabIndex == 0 ? Colors.white : Colors.transparent,
                                        borderRadius: BorderRadius.circular(8),
                                        boxShadow: selectedTabIndex == 0
                                            ? [BoxShadow(color: Colors.black12, blurRadius: 4, offset: const Offset(0, 1))]
                                            : null,
                                      ),
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Icon(Icons.rate_review_outlined,
                                              size: 16,
                                              color: selectedTabIndex == 0 ? AppColors.amityBlue : Colors.grey.shade600),
                                          const SizedBox(width: 6),
                                          Text(
                                            'Document Review & Checklist',
                                            style: TextStyle(
                                              fontSize: 13,
                                              fontWeight: selectedTabIndex == 0 ? FontWeight.bold : FontWeight.w500,
                                              color: selectedTabIndex == 0 ? AppColors.amityBlue : Colors.grey.shade700,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                                Expanded(
                                  child: InkWell(
                                    onTap: () => setDialogState(() => selectedTabIndex = 1),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(vertical: 8),
                                      decoration: BoxDecoration(
                                        color: selectedTabIndex == 1 ? Colors.white : Colors.transparent,
                                        borderRadius: BorderRadius.circular(8),
                                        boxShadow: selectedTabIndex == 1
                                            ? [BoxShadow(color: Colors.black12, blurRadius: 4, offset: const Offset(0, 1))]
                                            : null,
                                      ),
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Icon(Icons.verified_user_outlined,
                                              size: 16,
                                              color: selectedTabIndex == 1 ? AppColors.amityBlue : Colors.grey.shade600),
                                          const SizedBox(width: 6),
                                          Text(
                                            'Clearance Gates',
                                            style: TextStyle(
                                              fontSize: 13,
                                              fontWeight: selectedTabIndex == 1 ? FontWeight.bold : FontWeight.w500,
                                              color: selectedTabIndex == 1 ? AppColors.amityBlue : Colors.grey.shade700,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                                Expanded(
                                  child: InkWell(
                                    onTap: () => setDialogState(() => selectedTabIndex = 2),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(vertical: 8),
                                      decoration: BoxDecoration(
                                        color: selectedTabIndex == 2 ? Colors.white : Colors.transparent,
                                        borderRadius: BorderRadius.circular(8),
                                        boxShadow: selectedTabIndex == 2
                                            ? [BoxShadow(color: Colors.black12, blurRadius: 4, offset: const Offset(0, 1))]
                                            : null,
                                      ),
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Icon(Icons.send_rounded,
                                              size: 16,
                                              color: selectedTabIndex == 2 ? AppColors.amityBlue : Colors.grey.shade600),
                                          const SizedBox(width: 6),
                                          Text(
                                            'Send Status Message',
                                            style: TextStyle(
                                              fontSize: 13,
                                              fontWeight: selectedTabIndex == 2 ? FontWeight.bold : FontWeight.w500,
                                              color: selectedTabIndex == 2 ? AppColors.amityBlue : Colors.grey.shade700,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          Expanded(
                            child: SingleChildScrollView(
                              child: selectedTabIndex == 0
                                  ? _buildDocumentsAndChecklistTab(
                                      reqId: id,
                                      documents: documents,
                                      checklist: checklist,
                                      onRefresh: () {
                                        setDialogState(() => isLoading = true);
                                        loadDossier();
                                      },
                                    )
                                  : selectedTabIndex == 1
                                      ? _buildClearanceGatesTab(
                                          refNo: refNo,
                                          gates: gates,
                                          selectedDept: selectedDept,
                                          selectedAction: selectedAction,
                                          duesAmount: duesAmount,
                                          autoOffsetDeposit: autoOffsetDeposit,
                                          officerController: officerController,
                                          notesController: notesController,
                                          duesController: duesController,
                                          onDeptChanged: (v) => setDialogState(() => selectedDept = v),
                                          onActionChanged: (v) => setDialogState(() => selectedAction = v),
                                          onDuesChanged: (v) => duesAmount = v,
                                          onOffsetChanged: (v) => setDialogState(() => autoOffsetDeposit = v),
                                          onSubmit: () async {
                                            if (selectedAction == 'FLAG_DUES' && autoOffsetDeposit && duesAmount > 0) {
                                              await ref.read(staffActionsProvider).offsetDepartmentDues(
                                                    referenceNo: refNo,
                                                    department: selectedDept,
                                                    amount: duesAmount,
                                                    reason: notesController.text.trim().isNotEmpty
                                                        ? notesController.text.trim()
                                                        : 'Fine offset against caution deposit',
                                                    authorizedBy: officerController.text.trim(),
                                                  );
                                            } else {
                                              await ref.read(staffActionsProvider).clearDepartmentGate(
                                                    referenceNo: refNo,
                                                    department: selectedDept,
                                                    action: selectedAction,
                                                    duesAmount: duesAmount,
                                                    officerName: officerController.text.trim(),
                                                    notes: notesController.text.trim(),
                                                  );
                                            }
                                            setDialogState(() => isLoading = true);
                                            loadDossier();
                                          },
                                        )
                                      : _buildSendMessageTab(
                                          reqId: id,
                                          events: events,
                                          messageController: messageController,
                                          selectedNewStatus: selectedNewStatus,
                                          onStatusChanged: (v) => setDialogState(() => selectedNewStatus = v),
                                          onSend: () async {
                                            final msg = messageController.text.trim();
                                            if (msg.isEmpty) return;
                                            await ref.read(staffActionsProvider).sendRequestStatusMessage(
                                                  reqId: id,
                                                  message: msg,
                                                  status: selectedNewStatus == 'KEEP_CURRENT' ? null : selectedNewStatus.toLowerCase(),
                                                );
                                            messageController.clear();
                                            setDialogState(() => isLoading = true);
                                            loadDossier();
                                          },
                                        ),
                            ),
                          ),
                        ],
                      ),
              ),
              actionsPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Close Dossier'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Widget _buildDocumentsAndChecklistTab({
    required int reqId,
    required List documents,
    required List checklist,
    required VoidCallback onRefresh,
  }) {
    final completedChecklistCount = checklist.where((c) {
      final s = (c is Map ? (c['status'] ?? '') : '').toString().toLowerCase();
      return s == 'completed' || s == 'verified';
    }).length;
    final totalChecklistCount = checklist.length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section 1: Document Review
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Row(
              children: [
                Icon(Icons.rate_review_rounded, size: 18, color: AppColors.amityBlue),
                SizedBox(width: 8),
                Text(
                  'Document Review',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ],
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
              decoration: BoxDecoration(
                color: AppColors.amityBlue.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                '${documents.length} File(s)',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.amityBlue),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (documents.isEmpty)
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.amber.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.amber.shade200),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, color: Colors.amber.shade800, size: 20),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'No documents uploaded yet by the student for this request.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ],
            ),
          )
        else
          ...documents.map((doc) {
            final docMap = doc is Map ? Map<String, dynamic>.from(doc) : <String, dynamic>{};
            final docId = docMap['id'] is int ? docMap['id'] as int : int.tryParse(docMap['id']?.toString() ?? '0') ?? 0;
            final docStatus = (docMap['verification_status'] ?? docMap['status'] ?? 'pending').toString().toLowerCase();
            final docName = docMap['document_name'] ?? docMap['filename'] ?? docMap['file_name'] ?? 'Withdrawal Document';
            final docType = docMap['document_type'] ?? docMap['classification'] ?? 'Official Submission';

            Color statusColor = AppColors.amityYellow;
            if (docStatus == 'verified' || docStatus == 'accepted') statusColor = AppColors.successGreen;
            if (docStatus == 'rejected' || docStatus == 'fraud_detected') statusColor = AppColors.urgentRed;

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Row(
                children: [
                  Icon(Icons.picture_as_pdf_rounded, color: AppColors.urgentRed, size: 28),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(docName.toString(), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            Text('Type: $docType • ', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                              decoration: BoxDecoration(
                                color: statusColor.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                docStatus.toUpperCase(),
                                style: TextStyle(fontSize: 10, color: statusColor, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        tooltip: 'Inspect OCR & Details',
                        icon: const Icon(Icons.find_in_page_outlined, color: AppColors.amityBlue, size: 20),
                        onPressed: () => _showDocumentInspectDialog(context, docMap, reqId, onRefresh),
                      ),
                      if (docStatus != 'verified' && docStatus != 'accepted')
                        IconButton(
                          tooltip: 'Accept & Verify Document',
                          icon: const Icon(Icons.check_circle_outline, color: AppColors.successGreen, size: 20),
                          onPressed: () async {
                            await ref.read(staffActionsProvider).reviewRequestDocument(
                                  reqId: reqId,
                                  docId: docId,
                                  action: 'verified',
                                  notes: 'Document inspected and verified by staff.',
                                );
                            onRefresh();
                          },
                        ),
                      if (docStatus != 'rejected')
                        IconButton(
                          tooltip: 'Reject Document',
                          icon: const Icon(Icons.cancel_outlined, color: AppColors.urgentRed, size: 20),
                          onPressed: () async {
                            final reasonController = TextEditingController();
                            final confirmed = await showDialog<bool>(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                title: const Text('Reject Document'),
                                content: TextField(
                                  controller: reasonController,
                                  decoration: const InputDecoration(
                                    labelText: 'Rejection Reason / Clarification',
                                    border: OutlineInputBorder(),
                                  ),
                                ),
                                actions: [
                                  TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                                  FilledButton(
                                    style: FilledButton.styleFrom(backgroundColor: AppColors.urgentRed),
                                    onPressed: () => Navigator.pop(ctx, true),
                                    child: const Text('Reject'),
                                  ),
                                ],
                              ),
                            );
                            if (confirmed == true) {
                              await ref.read(staffActionsProvider).reviewRequestDocument(
                                    reqId: reqId,
                                    docId: docId,
                                    action: 'rejected',
                                    notes: reasonController.text.trim().isNotEmpty
                                        ? reasonController.text.trim()
                                        : 'Document rejected due to clarity/validity issues.',
                                  );
                              onRefresh();
                            }
                          },
                        ),
                    ],
                  ),
                ],
              ),
            );
          }),
        const SizedBox(height: 18),

        // Section 2: Interactive Clearance Checklist
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                const Icon(Icons.checklist_rounded, size: 18, color: AppColors.primary),
                const SizedBox(width: 8),
                const Text(
                  'Workflow Clearance Checklist',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: (completedChecklistCount == totalChecklistCount && totalChecklistCount > 0)
                        ? AppColors.successGreen.withValues(alpha: 0.15)
                        : Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    '$completedChecklistCount/$totalChecklistCount Verified',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: (completedChecklistCount == totalChecklistCount && totalChecklistCount > 0)
                          ? AppColors.successGreen
                          : Colors.grey.shade700,
                    ),
                  ),
                ),
              ],
            ),
            if (checklist.isNotEmpty)
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  side: const BorderSide(color: AppColors.successGreen),
                ),
                onPressed: () async {
                  await ref.read(staffActionsProvider).verifyAllChecklist(reqId: reqId);
                  for (final it in checklist) {
                    if (it is Map) it['status'] = 'completed';
                  }
                  onRefresh();
                },
                icon: const Icon(Icons.done_all_rounded, size: 14, color: AppColors.successGreen),
                label: const Text('Verify All', style: TextStyle(fontSize: 11, color: AppColors.successGreen, fontWeight: FontWeight.bold)),
              ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          'Check off clearance requirements after reviewing physical or uploaded records:',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
        const SizedBox(height: 8),
        if (checklist.isEmpty)
          Text('No checklist items defined.', style: TextStyle(fontSize: 12, color: Colors.grey.shade600))
        else
          ...checklist.map((item) {
            final itemMap = item is Map ? Map<String, dynamic>.from(item) : <String, dynamic>{};
            final itemId = itemMap['id'] is int ? itemMap['id'] as int : int.tryParse(itemMap['id']?.toString() ?? '0') ?? 0;
            final label = itemMap['label'] ?? itemMap['description'] ?? itemMap['name'] ?? 'Checklist Item';
            final status = (itemMap['status'] ?? 'pending').toString().toLowerCase();
            final isDone = status == 'completed' || status == 'verified' || itemMap['completed'] == true;

            return InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: () async {
                final newStatus = isDone ? 'pending' : 'completed';
                itemMap['status'] = newStatus;
                onRefresh();
                await ref.read(staffActionsProvider).updateChecklistItem(
                  reqId: reqId,
                  itemId: itemId,
                  status: newStatus,
                );
                onRefresh();
              },
              child: Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: isDone ? AppColors.successGreen.withValues(alpha: 0.05) : Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: isDone ? AppColors.successGreen.withValues(alpha: 0.35) : Colors.grey.shade300,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isDone ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
                      size: 20,
                      color: isDone ? AppColors.successGreen : Colors.grey.shade400,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            label.toString(),
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: isDone ? FontWeight.w600 : FontWeight.w500,
                              decoration: isDone ? TextDecoration.lineThrough : null,
                              color: isDone ? Colors.grey.shade600 : Colors.black87,
                            ),
                          ),
                          if (itemMap['description'] != null && itemMap['description'].toString().isNotEmpty && itemMap['description'] != label)
                            Text(
                              itemMap['description'].toString(),
                              style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                            ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isDone ? AppColors.successGreen.withValues(alpha: 0.12) : Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        isDone ? 'COMPLETED' : 'PENDING',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: isDone ? AppColors.successGreen : Colors.grey.shade600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        if (completedChecklistCount == totalChecklistCount && totalChecklistCount > 0)
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.successGreen.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.successGreen.withValues(alpha: 0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.verified_rounded, color: AppColors.successGreen, size: 20),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'All clearance checklist items have been checked and verified.',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.successGreen),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  void _showDocumentInspectDialog(
    BuildContext context,
    Map<String, dynamic> docMap,
    int reqId,
    VoidCallback onRefresh,
  ) {
    final docId = docMap['id'] is int ? docMap['id'] as int : int.tryParse(docMap['id']?.toString() ?? '0') ?? 0;
    final docName = docMap['document_name'] ?? docMap['filename'] ?? docMap['file_name'] ?? 'Withdrawal Document';
    final docType = docMap['document_type'] ?? docMap['classification'] ?? 'Official Submission';
    final docStatus = (docMap['verification_status'] ?? docMap['status'] ?? 'pending').toString().toLowerCase();
    final fraudNotes = docMap['verification_notes'] ?? docMap['fraud_flags'];
    final identityMatch = docMap['ocr_identity_match'] ?? 'NOT_EVALUATED';
    final ocrData = docMap['ocr_data'] is Map ? Map<String, dynamic>.from(docMap['ocr_data'] as Map) : null;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.find_in_page_rounded, color: AppColors.amityBlue, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text('Inspect: $docName', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildInspectRow('Document Type:', docType.toString()),
                _buildInspectRow('Current Status:', docStatus.toUpperCase()),
                _buildInspectRow('Identity Match:', identityMatch.toString()),
                if (fraudNotes != null && fraudNotes.toString().isNotEmpty)
                  _buildInspectRow('Verification Notes:', fraudNotes.toString(), isAlert: true),
                if (ocrData != null) ...[
                  const Divider(height: 20),
                  const Text('OCR Extraction Data', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  const SizedBox(height: 6),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      ocrData.entries.map((e) => '${e.key}: ${e.value}').join('\n'),
                      style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close')),
          if (docStatus != 'verified')
            FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: AppColors.successGreen),
              onPressed: () async {
                Navigator.pop(ctx);
                await ref.read(staffActionsProvider).reviewRequestDocument(
                      reqId: reqId,
                      docId: docId,
                      action: 'verified',
                      notes: 'Verified during detailed dossier inspection.',
                    );
                onRefresh();
              },
              icon: const Icon(Icons.check_rounded, size: 16),
              label: const Text('Verify Document'),
            ),
        ],
      ),
    );
  }

  Widget _buildInspectRow(String label, String value, {bool isAlert = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 130, child: Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.bold))),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: isAlert ? AppColors.urgentRed : Colors.black87,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClearanceGatesTab({
    required String refNo,
    required List gates,
    required String selectedDept,
    required String selectedAction,
    required double duesAmount,
    required bool autoOffsetDeposit,
    required TextEditingController officerController,
    required TextEditingController notesController,
    required TextEditingController duesController,
    required ValueChanged<String> onDeptChanged,
    required ValueChanged<String> onActionChanged,
    required ValueChanged<double> onDuesChanged,
    required ValueChanged<bool> onOffsetChanged,
    required Future<void> Function() onSubmit,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '4 Sequential Department Clearance Gates',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        ...gates.map((g) {
          final gMap = g is Map ? Map<String, dynamic>.from(g) : <String, dynamic>{};
          final dept = gMap['department'] ?? 'DEPT';
          final status = (gMap['status'] ?? 'PENDING').toString().toUpperCase();
          final dues = double.tryParse(gMap['dues_amount']?.toString() ?? '0') ?? 0.0;
          final isCleared = status == 'CLEARED';

          return Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: isCleared ? AppColors.successGreen.withValues(alpha: 0.06) : Colors.grey.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isCleared ? AppColors.successGreen.withValues(alpha: 0.3) : Colors.grey.shade200,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  isCleared ? Icons.check_circle_rounded : Icons.pending_actions_rounded,
                  color: isCleared ? AppColors.successGreen : AppColors.amityYellow,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    dept.toString(),
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                ),
                if (dues > 0)
                  Text(
                    'Dues: ₹${dues.toStringAsFixed(0)} ',
                    style: const TextStyle(fontSize: 12, color: AppColors.urgentRed, fontWeight: FontWeight.bold),
                  ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: isCleared ? AppColors.successGreen : AppColors.amityYellow.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    status,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: isCleared ? Colors.white : Colors.black87,
                    ),
                  ),
                ),
              ],
            ),
          );
        }),
        const Divider(height: 24),
        const Text(
          'Sign-off on Clearance Gate:',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          initialValue: selectedDept,
          decoration: const InputDecoration(labelText: 'Auditing Department', border: OutlineInputBorder()),
          items: const [
            DropdownMenuItem(value: 'LIBRARY', child: Text('Central Library')),
            DropdownMenuItem(value: 'HOSTEL', child: Text('Hostel & Mess Office')),
            DropdownMenuItem(value: 'ACCOUNTS', child: Text('Finance & Accounts')),
            DropdownMenuItem(value: 'REGISTRAR', child: Text('Registrar Final Audit')),
          ],
          onChanged: (val) {
            if (val != null) onDeptChanged(val);
          },
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: selectedAction,
          decoration: const InputDecoration(labelText: 'Sign-off Action', border: OutlineInputBorder()),
          items: const [
            DropdownMenuItem(value: 'CLEAR', child: Text('CLEAR (No Pending Obligations)')),
            DropdownMenuItem(value: 'FLAG_DUES', child: Text('FLAG_DUES (Outstanding Charges)')),
          ],
          onChanged: (val) {
            if (val != null) onActionChanged(val);
          },
        ),
        if (selectedAction == 'FLAG_DUES') ...[
          const SizedBox(height: 12),
          TextField(
            controller: duesController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Outstanding Dues Amount (₹)',
              border: OutlineInputBorder(),
              prefixText: '₹ ',
            ),
            onChanged: (v) => onDuesChanged(double.tryParse(v) ?? 0.0),
          ),
          const SizedBox(height: 8),
          CheckboxListTile(
            value: autoOffsetDeposit,
            contentPadding: EdgeInsets.zero,
            title: const Text('Smart Offset against Caution Deposit', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
            subtitle: const Text('Deducts fine directly from ₹10,000 security deposit without freezing clearance.', style: TextStyle(fontSize: 11)),
            onChanged: (val) => onOffsetChanged(val ?? false),
          ),
        ],
        const SizedBox(height: 12),
        TextField(
          controller: officerController,
          decoration: const InputDecoration(labelText: 'Auditing Officer Name', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: notesController,
          decoration: const InputDecoration(labelText: 'Audit Remarks / Notes', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: onSubmit,
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Submit Gate Sign-off'),
            style: FilledButton.styleFrom(backgroundColor: AppColors.amityBlue),
          ),
        ),
      ],
    );
  }

  Widget _buildSendMessageTab({
    required int reqId,
    required List events,
    required TextEditingController messageController,
    required String selectedNewStatus,
    required ValueChanged<String> onStatusChanged,
    required Future<void> Function() onSend,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Send Real-Time Status Update to Student',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 6),
        Text(
          'This message will appear directly on the student\'s Request Status card and AI counselor tracker.',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: messageController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Official Message to Student',
            hintText: 'e.g., Central Library cleared with 0 dues. Accounts desk is processing refund voucher.',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: selectedNewStatus,
          decoration: const InputDecoration(labelText: 'Update Overall Workflow Status', border: OutlineInputBorder()),
          items: const [
            DropdownMenuItem(value: 'KEEP_CURRENT', child: Text('Keep Current Status')),
            DropdownMenuItem(value: 'UNDER_REVIEW', child: Text('Set Status: Under Review')),
            DropdownMenuItem(value: 'APPROVED', child: Text('Set Status: Approved')),
            DropdownMenuItem(value: 'REJECTED', child: Text('Set Status: Rejected')),
          ],
          onChanged: (val) {
            if (val != null) onStatusChanged(val);
          },
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: onSend,
            icon: const Icon(Icons.send_rounded),
            label: const Text('Send Update to Student'),
            style: FilledButton.styleFrom(backgroundColor: AppColors.amityBlue),
          ),
        ),
        const Divider(height: 28),
        const Text(
          'Workflow Audit & Message History',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
        ),
        const SizedBox(height: 8),
        if (events.isEmpty)
          Text('No events recorded yet.', style: TextStyle(fontSize: 12, color: Colors.grey.shade600))
        else
          ...events.reversed.map((ev) {
            final evMap = ev is Map ? Map<String, dynamic>.from(ev) : <String, dynamic>{};
            final actor = evMap['actor'] ?? 'System';
            final desc = evMap['description'] ?? evMap['title'] ?? '';
            final time = evMap['timestamp']?.toString().split('T').first ?? '';

            return Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'By: $actor',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppColors.amityBlue),
                      ),
                      Text(time, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(desc.toString(), style: const TextStyle(fontSize: 12)),
                ],
              ),
            );
          }),
      ],
    );
  }

  Widget _buildTab(String status, String label) {
    final isSelected = _filterStatus == status;
    return ActionChip(
      label: Text(label),
      backgroundColor: isSelected ? AppColors.amityBlue : Colors.grey.shade200,
      labelStyle: TextStyle(
        color: isSelected ? Colors.white : Colors.black87,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
      ),
      onPressed: () {
        setState(() {
          _filterStatus = status;
          _selectedIds.clear();
        });
      },
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toUpperCase()) {
      case 'APPROVED':
        return AppColors.successGreen;
      case 'REJECTED':
        return AppColors.urgentRed;
      default:
        return AppColors.amityYellow;
    }
  }
}
