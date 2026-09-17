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
    final refNo = req['reference_no']?.toString().isNotEmpty == true
        ? req['reference_no'].toString()
        : 'AMITY-WTH-2026-${req['id']}';
    String selectedDept = 'LIBRARY';
    String selectedAction = 'CLEAR';
    double duesAmount = 0.0;
    bool autoOffsetDeposit = true;
    final officerController = TextEditingController(text: 'Prof. Sharma (Officer)');
    final notesController = TextEditingController();
    final duesController = TextEditingController(text: '0');

    showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Row(
                children: [
                  const Icon(Icons.verified_user_rounded, color: AppColors.amityBlue),
                  const SizedBox(width: 8),
                  Text('Department Sign-Off: $refNo'),
                ],
              ),
              content: SizedBox(
                width: 480,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Select Department & Sign-off Action:',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: selectedDept,
                        decoration: const InputDecoration(
                          labelText: 'Auditing Department',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'LIBRARY', child: Text('Central Library')),
                          DropdownMenuItem(value: 'HOSTEL', child: Text('Hostel & Mess Office')),
                          DropdownMenuItem(value: 'ACCOUNTS', child: Text('Finance & Accounts')),
                          DropdownMenuItem(value: 'REGISTRAR', child: Text('Registrar Final Audit')),
                        ],
                        onChanged: (val) {
                          if (val != null) setDialogState(() => selectedDept = val);
                        },
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        initialValue: selectedAction,
                        decoration: const InputDecoration(
                          labelText: 'Decision Action',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 'CLEAR', child: Text('CLEAR (No Pending Obligations)')),
                          DropdownMenuItem(value: 'FLAG_DUES', child: Text('FLAG_DUES (Pending Charges)')),
                        ],
                        onChanged: (val) {
                          if (val != null) setDialogState(() => selectedAction = val);
                        },
                      ),
                      if (selectedAction == 'FLAG_DUES') ...[
                        const SizedBox(height: 16),
                        TextField(
                          controller: duesController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            labelText: 'Outstanding Dues Amount (₹)',
                            border: OutlineInputBorder(),
                            prefixText: '₹ ',
                          ),
                          onChanged: (v) {
                            duesAmount = double.tryParse(v) ?? 0.0;
                          },
                        ),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppColors.successGreen.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppColors.successGreen.withValues(alpha: 0.3)),
                          ),
                          child: CheckboxListTile(
                            value: autoOffsetDeposit,
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              'Smart Offset against Caution Deposit',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                            ),
                            subtitle: const Text(
                              'Deducts fine directly from ₹10,000 security deposit. Eliminates bank challans and clears gate immediately.',
                              style: TextStyle(fontSize: 11),
                            ),
                            onChanged: (val) {
                              setDialogState(() => autoOffsetDeposit = val ?? false);
                            },
                          ),
                        ),
                      ],
                      const SizedBox(height: 16),
                      TextField(
                        controller: officerController,
                        decoration: const InputDecoration(
                          labelText: 'Auditing Officer Name',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: notesController,
                        decoration: const InputDecoration(
                          labelText: 'Audit Remarks / Notes',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton.icon(
                  onPressed: () async {
                    Navigator.of(dialogContext).pop();
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
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              '₹${duesAmount.toStringAsFixed(0)} offset against Caution Deposit. $selectedDept CLEARED!',
                            ),
                            backgroundColor: AppColors.successGreen,
                          ),
                        );
                      }
                    } else {
                      await ref.read(staffActionsProvider).clearDepartmentGate(
                            referenceNo: refNo,
                            department: selectedDept,
                            action: selectedAction,
                            duesAmount: duesAmount,
                            officerName: officerController.text.trim(),
                            notes: notesController.text.trim(),
                          );
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Gate $selectedDept updated to $selectedAction successfully.',
                            ),
                            backgroundColor: AppColors.successGreen,
                          ),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.check),
                  label: const Text('Submit Clearance'),
                  style: FilledButton.styleFrom(backgroundColor: AppColors.amityBlue),
                ),
              ],
            );
          },
        );
      },
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
