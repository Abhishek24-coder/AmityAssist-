import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api_client.dart';
import '../../../core/api_config.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../auth/application/auth_provider.dart';
import 'digital_signature_dialog.dart';

extension AuthStateRoleExtension on AuthState {
  String? get role => staffRole;
}

class StaffNotesheetScreen extends ConsumerStatefulWidget {
  const StaffNotesheetScreen({super.key});

  @override
  ConsumerState<StaffNotesheetScreen> createState() => _StaffNotesheetScreenState();
}

class _StaffNotesheetScreenState extends ConsumerState<StaffNotesheetScreen> {
  bool _isLoading = true;
  List<dynamic> _notesheets = [];
  String? _selectedCategory;
  String _currentStageFilter = 'ALL';

  final List<String> _stages = ['SUPERVISOR', 'HOD', 'HOI', 'PRO_VC', 'VC'];

  @override
  void initState() {
    super.initState();
    _fetchNotesheets();
  }

  Future<void> _fetchNotesheets() async {
    setState(() => _isLoading = true);
    try {
      final dio = ref.read(apiClientProvider);
      final params = <String, dynamic>{};
      if (_currentStageFilter != 'ALL') {
        params['stage'] = _currentStageFilter;
      }
      if (_selectedCategory != null && _selectedCategory != 'All') {
        params['category'] = _selectedCategory;
      }

      final res = await dio.get('/notesheets', queryParameters: params);
      if (mounted) {
        final data = res.data as Map<String, dynamic>;
        setState(() {
          _notesheets = data['notesheets'] ?? [];
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _performAction(String refNo, String action, String stage, {String? customComments}) async {
    try {
      final dio = ref.read(apiClientProvider);
      final officerName = ref.read(authProvider).staffUsername ?? 'Senior Administrative Officer';
      final res = await dio.post(
        '/notesheets/$refNo/action',
        data: {
          'officer_id': officerName,
          'officer_name': officerName,
          'role': stage,
          'action': action,
          'comments': customComments ?? 'Signed and processed via Staff Digital Notesheet Cockpit',
        },
      );

      if (mounted) {
        if (res.statusCode == 200) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Notesheet $refNo marked: $action'),
              backgroundColor: AppColors.successGreen,
            ),
          );
          _fetchNotesheets();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Action failed: ${res.data}'),
              backgroundColor: AppColors.urgentRed,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            backgroundColor: AppColors.urgentRed,
          ),
        );
      }
    }
  }

  Future<void> _handleAction(BuildContext context, Map<String, dynamic> notesheet, String action) async {
    final refNo = notesheet['reference_no']?.toString() ?? '';
    final stage = (notesheet['current_stage'] ?? 'SUPERVISOR').toString().toUpperCase();
    final userRole = ref.read(authProvider).role ?? stage;
    final officerName = ref.read(authProvider).staffUsername ?? 'Authorized Officer';

    if (action == 'REJECT') {
      final commentsController = TextEditingController();
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.red),
              SizedBox(width: 8),
              Text('Confirm Rejection', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Are you sure you want to reject notesheet $refNo? This will halt the approval hierarchy.'),
              const SizedBox(height: 12),
              TextField(
                controller: commentsController,
                decoration: const InputDecoration(
                  labelText: 'Rejection Reason / Comments',
                  border: OutlineInputBorder(),
                  hintText: 'e.g. Incomplete supporting transcripts.',
                ),
                maxLines: 2,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Confirm Reject'),
            ),
          ],
        ),
      );

      if (confirmed == true) {
        await _performAction(
          refNo,
          'REJECT',
          userRole,
          customComments: commentsController.text.trim().isNotEmpty
              ? commentsController.text.trim()
              : 'Rejected at $stage stage by $userRole ($officerName)',
        );
      }
      return;
    }

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => DigitalSignatureDialog(
        officerName: officerName,
        officerRole: userRole,
        stage: stage,
      ),
    );

    if (result != null) {
      final comments = "${result['comments']} [${result['signature']}]";
      await _performAction(refNo, action, userRole, customComments: comments);
    }
  }

  void _showInFlightEditDialog(BuildContext context, Map<String, dynamic> notesheet) {
    final refNo = notesheet['reference_no']?.toString() ?? '';
    final content = notesheet['content'] is Map ? Map<String, dynamic>.from(notesheet['content'] as Map) : <String, dynamic>{};
    final stage = (notesheet['current_stage'] ?? 'SUPERVISOR').toString().toUpperCase();
    final userRole = ref.read(authProvider).role ?? stage;
    final officerName = ref.read(authProvider).staffUsername ?? 'Staff Officer';

    String selectedField = content.keys.isNotEmpty ? content.keys.first : 'course_code';
    final valueController = TextEditingController(text: content[selectedField]?.toString() ?? '');
    final reasonController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.edit_note_rounded, color: Colors.blue.shade800),
                ),
                const SizedBox(width: 10),
                const Text('In-Flight Collaborative Edit', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ],
            ),
            content: SizedBox(
              width: 500,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('File Ref: $refNo • Current Stage: $stage', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                    const SizedBox(height: 16),
                    const Text('Select Field to Correct', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    const SizedBox(height: 6),
                    if (content.isNotEmpty)
                      DropdownButtonFormField<String>(
                        initialValue: selectedField,
                        decoration: const InputDecoration(border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
                        items: content.keys.map((k) => DropdownMenuItem(value: k, child: Text(k.replaceAll('_', ' ').toUpperCase()))).toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setDialogState(() {
                              selectedField = val;
                              valueController.text = content[val]?.toString() ?? '';
                            });
                          }
                        },
                      )
                    else
                      TextField(
                        decoration: const InputDecoration(labelText: 'Field Name', border: OutlineInputBorder()),
                        onChanged: (val) => selectedField = val.trim(),
                      ),
                    const SizedBox(height: 14),
                    const Text('Updated Value', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: valueController,
                      decoration: const InputDecoration(
                        hintText: 'Enter corrected value (e.g. CSE101)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 14),
                    const Text('Mandatory Audit Justification (Min 5 chars)', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Color(0xFFB45309))),
                    const SizedBox(height: 6),
                    TextField(
                      controller: reasonController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        hintText: 'e.g. Corrected course code typo from CS101 to standard CSE101',
                        border: OutlineInputBorder(),
                        filled: true,
                        fillColor: Color(0xFFFFFBEB),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Cancel'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
                onPressed: () async {
                  final reason = reasonController.text.trim();
                  if (reason.length < 5) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('A detailed audit reason (at least 5 characters) is mandatory.'),
                        backgroundColor: AppColors.urgentRed,
                      ),
                    );
                    return;
                  }
                  Navigator.pop(ctx);
                  try {
                    final dio = ref.read(apiClientProvider);
                    final res = await dio.post(
                      '/notesheets/$refNo/edit-field',
                      data: {
                        'officer_id': officerName,
                        'officer_role': userRole,
                        'field_name': selectedField,
                        'new_value': valueController.text.trim(),
                        'reason': reason,
                      },
                    );
                    if (mounted) {
                      final msg = res.data is Map ? res.data['message']?.toString() : null;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(msg ?? 'Field updated with audit annotation.'),
                          backgroundColor: AppColors.successGreen,
                        ),
                      );
                      _fetchNotesheets();
                    }
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Failed to update field: $e'),
                          backgroundColor: AppColors.urgentRed,
                        ),
                      );
                    }
                  }
                },
                child: const Text('Apply In-Flight Edit'),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildActionControls(BuildContext context, Map<String, dynamic> notesheet, WidgetRef ref) {
    final currentStage = (notesheet['current_stage'] ?? 'SUPERVISOR').toString().toUpperCase();
    final status = (notesheet['status'] ?? 'IN_REVIEW').toString().toUpperCase();
    final userRole = ref.watch(authProvider).role ?? 'Staff';

    // If already approved or rejected, render completed status badge
    if (status == 'APPROVED') {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.green.shade50, borderRadius: BorderRadius.circular(8)),
        child: const Row(
          children: [
            Icon(Icons.verified_rounded, color: Colors.green),
            SizedBox(width: 8),
            Text(
              'Notesheet Completed: Executive Seal Applied by Vice Chancellor.',
              style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green),
            ),
          ],
        ),
      );
    }

    // Check if current logged-in user matches the stage authority
    final isMyTurn = (currentStage == 'SUPERVISOR' && userRole == 'Supervisor') ||
                     (currentStage == 'HOD' && userRole == 'HOD') ||
                     (currentStage == 'HOI' && (userRole == 'Dean' || userRole == 'HOI')) ||
                     (currentStage == 'PRO_VC' && userRole == 'Pro-VC') ||
                     (currentStage == 'VC' && userRole == 'Vice Chancellor') ||
                     userRole == 'Administrator';

    if (!isMyTurn) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(8)),
        child: Row(
          children: [
            const Icon(Icons.lock_clock_rounded, color: Colors.orange),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Awaiting sign-off by $currentStage authority. You are logged in as $userRole (View Only).',
                style: const TextStyle(fontSize: 12, color: Colors.brown),
              ),
            ),
          ],
        ),
      );
    }

    // Active Buttons for Authorized Officer
    final isFinalStage = (currentStage == 'VC');
    final nextStageLabel = switch (currentStage) {
      'SUPERVISOR' => 'Forward to HOD',
      'HOD' => 'Forward to Dean (HOI)',
      'HOI' => 'Forward to Pro-VC',
      'PRO_VC' => 'Forward to Vice Chancellor',
      _ => 'Apply Final Approval Seal',
    };

    return Row(
      children: [
        // 1. In-Flight Edit Button (For HOD and above)
        if (['HOD', 'HOI', 'PRO_VC', 'VC'].contains(currentStage))
          OutlinedButton.icon(
            onPressed: () => _showInFlightEditDialog(context, notesheet),
            icon: const Icon(Icons.edit_note_rounded, size: 18),
            label: const Text('Correct Typo / Edit'),
            style: OutlinedButton.styleFrom(foregroundColor: Colors.blue.shade800),
          ),
        const Spacer(),
        // 2. Reject Button
        TextButton.icon(
          onPressed: () => _handleAction(context, notesheet, 'REJECT'),
          icon: const Icon(Icons.close_rounded, color: Colors.red),
          label: const Text('Reject', style: TextStyle(color: Colors.red)),
        ),
        const SizedBox(width: 8),
        // 3. Sign & Advance / Seal Button
        FilledButton.icon(
          onPressed: () => _handleAction(context, notesheet, isFinalStage ? 'APPROVE' : 'FORWARD'),
          icon: Icon(isFinalStage ? Icons.verified_rounded : Icons.arrow_forward_rounded, size: 18),
          label: Text(nextStageLabel),
          style: FilledButton.styleFrom(backgroundColor: isFinalStage ? Colors.green.shade700 : AppColors.primary),
        ),
      ],
    );
  }

  void _openSignatureFlow(String refNo, String stage) async {
    final userRole = ref.read(authProvider).role ?? stage;
    final officerName = ref.read(authProvider).staffUsername ?? 'Dr. Suresh Sharma';
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => DigitalSignatureDialog(
        officerName: officerName,
        officerRole: userRole,
        stage: stage,
      ),
    );

    if (result != null) {
      final comments = "${result['comments']} [${result['signature']}]";
      _performAction(refNo, stage == 'VC' ? 'APPROVE' : 'FORWARD', userRole, customComments: comments);
    }
  }

  void _showCreateNotesheetDialog() {
    final titleController = TextEditingController();
    final studentIdController = TextEditingController();
    final departmentController = TextEditingController(text: 'Academic Affairs');
    final clauseController = TextEditingController(text: 'Ordinance 14 (Student Governance)');
    final bodyController = TextEditingController();
    String selectedCategory = 'Academic';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return Dialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Container(
              width: 650,
              padding: const EdgeInsets.all(26),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppColors.amityBlue.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(Icons.note_add_rounded, color: AppColors.amityBlue, size: 26),
                        ),
                        const SizedBox(width: 14),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Initiate Digital Notesheet',
                                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Hierarchical official approval track (Supervisor ➔ HOD ➔ HOI ➔ Pro-VC ➔ VC)',
                                style: TextStyle(fontSize: 12, color: Colors.black54),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    const Text('Category', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    const SizedBox(height: 6),
                    DropdownButtonFormField<String>(
                      initialValue: selectedCategory,
                      decoration: const InputDecoration(border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
                      items: ['Academic', 'Disciplinary', 'Fee Concession', 'Course Exemption', 'General']
                          .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                          .toList(),
                      onChanged: (val) {
                        if (val != null) setDialogState(() => selectedCategory = val);
                      },
                    ),
                    const SizedBox(height: 16),
                    const Text('Subject / Title', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: titleController,
                      decoration: const InputDecoration(
                        hintText: 'e.g. Special Approval for Course Exemption and Fee Waiver',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Student ID (Optional)', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                              const SizedBox(height: 6),
                              TextField(
                                controller: studentIdController,
                                decoration: const InputDecoration(
                                  hintText: 'e.g. STU001',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Originating Department', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                              const SizedBox(height: 6),
                              TextField(
                                controller: departmentController,
                                decoration: const InputDecoration(
                                  hintText: 'e.g. Academic Affairs / Examination Cell',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Text('Applicable Ordinance Clause / Rule', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: clauseController,
                      decoration: const InputDecoration(
                        hintText: 'e.g. Ordinance 18.2 / UGC 2026 Guidelines',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text('Proposal & Recommendation Body', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: bodyController,
                      maxLines: 5,
                      decoration: const InputDecoration(
                        hintText: 'Enter comprehensive case details, findings, justification, and proposed action...',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx),
                          child: const Text('Cancel'),
                        ),
                        const SizedBox(width: 12),
                        FilledButton.icon(
                          style: FilledButton.styleFrom(
                            backgroundColor: AppColors.amityBlue,
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          ),
                          icon: const Icon(Icons.send_rounded, size: 18),
                          label: const Text('Create & Dispatch Notesheet'),
                          onPressed: () async {
                            final title = titleController.text.trim();
                            final body = bodyController.text.trim();
                            final messenger = ScaffoldMessenger.of(context);
                            if (title.length < 3 || body.isEmpty) {
                              messenger.showSnackBar(
                                const SnackBar(content: Text('Please provide both Title and Proposal details.')),
                              );
                              return;
                            }
                            Navigator.pop(ctx);
                            try {
                              final dio = ref.read(apiClientProvider);
                              final payload = {
                                'title': title,
                                'category': selectedCategory,
                                'created_by': 'STAFF_OFFICER',
                                'creator_name': 'Senior Administrative Officer',
                                'creator_role': 'SUPERVISOR',
                                'student_id': studentIdController.text.trim().isNotEmpty ? studentIdController.text.trim() : null,
                                'initial_stage': 'SUPERVISOR',
                                'content': {
                                  'student_id': studentIdController.text.trim().isNotEmpty ? studentIdController.text.trim() : 'N/A',
                                  'department': departmentController.text.trim(),
                                  'ordinance_clause': clauseController.text.trim(),
                                  'proposal_summary': body,
                                  'recommended_action': 'Recommended for consideration by competent hierarchical authority.',
                                },
                                'comments': 'Initiated via Digital Notesheet Cockpit',
                              };
                              final res = await dio.post('/notesheets', data: payload);
                              if (!mounted) return;
                              if (res.statusCode == 200) {
                                messenger.showSnackBar(
                                  const SnackBar(
                                    content: Text('Digital Notesheet initiated successfully!'),
                                    backgroundColor: AppColors.successGreen,
                                  ),
                                );
                                _fetchNotesheets();
                              }
                            } catch (e) {
                              if (!mounted) return;
                              messenger.showSnackBar(
                                SnackBar(content: Text('Failed to create notesheet: $e'), backgroundColor: AppColors.urgentRed),
                              );
                            }
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  void _showFullWordDocumentDialog(Map<String, dynamic> ns) {
    final content = ns['content'] is Map ? Map<String, dynamic>.from(ns['content'] as Map) : <String, dynamic>{};
    final refNo = ns['reference_no'] ?? '';
    final title = ns['title'] ?? 'Official Academic Notesheet';
    final category = ns['category'] ?? 'General';
    final stage = ns['current_stage'] ?? 'SUPERVISOR';
    final status = ns['status'] ?? 'IN_REVIEW';
    final isEditable = status == 'IN_REVIEW';

    final controllers = <String, TextEditingController>{};
    for (final entry in content.entries) {
      controllers[entry.key] = TextEditingController(text: entry.value?.toString() ?? '');
    }
    final reasonController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Container(
          width: 820,
          height: 850,
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              // Document Modal Top Bar
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                decoration: const BoxDecoration(
                  color: Color(0xFF0F172A),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.description_rounded, color: Colors.white, size: 22),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Word Document Viewer & In-Flight Editor: $refNo',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14),
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            'Status: $status • Current Approval Stage: $stage',
                            style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Download DOCX
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Color(0xFF475569)),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                      icon: const Icon(Icons.description, size: 14, color: Color(0xFF60A5FA)),
                      label: const Text('DOCX', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      onPressed: () {
                        final url = ApiConfig.fullUrl('/api/notesheets/$refNo/docx');
                        launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                      },
                    ),
                    const SizedBox(width: 8),
                    // Download PDF
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFEF4444),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      ),
                      icon: const Icon(Icons.picture_as_pdf, size: 14, color: Colors.white),
                      label: const Text('PDF', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      onPressed: () {
                        final url = ApiConfig.fullUrl('/api/notesheets/$refNo/pdf');
                        launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                      },
                    ),
                    const SizedBox(width: 10),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white, size: 20),
                      onPressed: () => Navigator.pop(ctx),
                      tooltip: 'Close Document',
                    ),
                  ],
                ),
              ),

              // Word A4 Paper Viewport
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Center(
                    child: Container(
                      width: 740,
                      padding: const EdgeInsets.all(40),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(4),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.1),
                            blurRadius: 18,
                            offset: const Offset(0, 6),
                          ),
                        ],
                        border: Border.all(color: const Color(0xFFCBD5E1)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Official University Crest Header
                          Center(
                            child: Column(
                              children: [
                                const Text(
                                  'AMITY UNIVERSITY',
                                  style: TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w900,
                                    color: Color(0xFF0F172A),
                                    letterSpacing: 1.5,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                const Text(
                                  'OFFICIAL ACADEMIC & ADMINISTRATIVE NOTESHEET',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                    color: Color(0xFF1D4ED8),
                                    letterSpacing: 1.0,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                Container(
                                  width: double.infinity,
                                  height: 2,
                                  color: const Color(0xFF1D4ED8),
                                ),
                                const SizedBox(height: 4),
                                Container(
                                  width: double.infinity,
                                  height: 1,
                                  color: const Color(0xFF94A3B8),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 20),

                          // Document Reference & Category Meta
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Reference No: $refNo',
                                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Color(0xFF0F172A)),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Category: $category',
                                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                  ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: status == 'APPROVED'
                                          ? const Color(0xFF10B981).withValues(alpha: 0.15)
                                          : const Color(0xFFF59E0B).withValues(alpha: 0.15),
                                      borderRadius: BorderRadius.circular(6),
                                      border: Border.all(
                                        color: status == 'APPROVED' ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                                      ),
                                    ),
                                    child: Text(
                                      'STAGE: $stage ($status)',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w800,
                                        color: status == 'APPROVED' ? const Color(0xFF047857) : const Color(0xFFB45309),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 20),

                          // Subject Header
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8FAFC),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: const Color(0xFFE2E8F0)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'SUBJECT: ',
                                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Color(0xFF0F172A)),
                                ),
                                Expanded(
                                  child: Text(
                                    title,
                                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Color(0xFF1E293B)),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 20),

                          // Paragraphs / Fields
                          ...content.keys.map((k) {
                            final label = k.replaceAll('_', ' ').toUpperCase();
                            final isLong = k.contains('reason') || k.contains('notes') || k.contains('proposal') || k.contains('finding') || k.contains('action') || k.contains('recommendation');

                            return Padding(
                              padding: const EdgeInsets.only(bottom: 16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Text(
                                        label,
                                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: Color(0xFF475569), letterSpacing: 0.5),
                                      ),
                                      if (isEditable) ...[
                                        const SizedBox(width: 6),
                                        const Text('(Click to edit in-place)', style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontStyle: FontStyle.italic)),
                                      ],
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  TextField(
                                    controller: controllers[k],
                                    enabled: isEditable,
                                    maxLines: isLong ? 4 : 1,
                                    style: const TextStyle(fontSize: 13, height: 1.4, color: Color(0xFF0F172A)),
                                    decoration: InputDecoration(
                                      filled: true,
                                      fillColor: isEditable ? Colors.white : const Color(0xFFF8FAFC),
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
                                      ),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(6),
                                        borderSide: const BorderSide(color: Color(0xFFCBD5E1)),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }),

                          if (isEditable) ...[
                            const SizedBox(height: 10),
                            const Divider(),
                            const SizedBox(height: 10),
                            const Text(
                              'Mandatory In-Flight Audit Justification',
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: Color(0xFFB45309)),
                            ),
                            const SizedBox(height: 6),
                            TextField(
                              controller: reasonController,
                              decoration: const InputDecoration(
                                hintText: 'e.g. Corrected course code and updated proctorial inquiry recommendation.',
                                filled: true,
                                fillColor: Color(0xFFFFFBEB),
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Bottom Control Bar
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(bottom: Radius.circular(16)),
                  border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
                ),
                child: Row(
                  children: [
                    OutlinedButton.icon(
                      icon: const Icon(Icons.picture_as_pdf, color: Colors.red, size: 16),
                      label: const Text('Download PDF', style: TextStyle(color: Colors.red)),
                      onPressed: () {
                        final url = ApiConfig.fullUrl('/api/notesheets/$refNo/pdf');
                        launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                      },
                    ),
                    const SizedBox(width: 10),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.description, color: Color(0xFF2563EB), size: 16),
                      label: const Text('Download Word DOCX'),
                      onPressed: () {
                        final url = ApiConfig.fullUrl('/api/notesheets/$refNo/docx');
                        launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                      },
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('Close'),
                    ),
                    if (isEditable) ...[
                      const SizedBox(width: 12),
                      FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.amityBlue,
                          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                        ),
                        icon: const Icon(Icons.save_rounded, size: 18),
                        label: const Text('Save In-Flight Document Edits'),
                        onPressed: () async {
                          final reason = reasonController.text.trim();
                          if (reason.isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Audit reason is mandatory for document modifications')),
                            );
                            return;
                          }
                          Navigator.pop(ctx);
                          try {
                            final dio = ref.read(apiClientProvider);
                            for (final entry in controllers.entries) {
                              final newVal = entry.value.text.trim();
                              if (newVal != content[entry.key]?.toString()) {
                                await dio.post(
                                  '/notesheets/$refNo/edit-field',
                                  data: {
                                    'officer_id': 'STAFF_OFFICER',
                                    'officer_role': stage,
                                    'field_name': entry.key,
                                    'new_value': newVal,
                                    'reason': reason,
                                  },
                                );
                              }
                            }
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Document updated and audit logged!'),
                                  backgroundColor: AppColors.successGreen,
                                ),
                              );
                              _fetchNotesheets();
                            }
                          } catch (err) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Error saving changes: $err'), backgroundColor: AppColors.urgentRed),
                              );
                            }
                          }
                        },
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Digital Notesheet Word Editor & Signatures'),
        backgroundColor: AppColors.amityBlue,
        actions: [
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: AppColors.amityBlue,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            ),
            icon: const Icon(Icons.note_add_rounded, size: 18),
            label: const Text('+ New Digital Notesheet', style: TextStyle(fontWeight: FontWeight.bold)),
            onPressed: _showCreateNotesheetDialog,
          ),
          const SizedBox(width: 8),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchNotesheets, tooltip: 'Refresh'),
          const SizedBox(width: 12),
        ],
      ),
      body: Column(
        children: [
          // Filter Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            color: Colors.grey.shade100,
            child: Row(
              children: [
                const Text('Stage Filter: ', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _currentStageFilter,
                  items: ['ALL', ..._stages]
                      .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setState(() => _currentStageFilter = val);
                      _fetchNotesheets();
                    }
                  },
                ),
                const Spacer(),
                Text(
                  'Hierarchy: Supervisor ➔ HOD ➔ HOI ➔ Pro-VC ➔ VC',
                  style: TextStyle(color: Colors.blueGrey.shade700, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _notesheets.isEmpty
                    ? const Center(child: Text('No digital notesheets found.'))
                    : ListView.builder(
                        padding: const EdgeInsets.all(24),
                        itemCount: _notesheets.length,
                        itemBuilder: (ctx, idx) {
                          final ns = _notesheets[idx];
                          final refNo = ns['reference_no'] ?? '';
                          final title = ns['title'] ?? '';
                          final stage = ns['current_stage'] ?? '';
                          final status = ns['status'] ?? '';
                          final content = ns['content'] is Map ? ns['content'] as Map : {};
                          final signatures = ns['signatures'] is List ? ns['signatures'] as List : [];

                          return Container(
                            margin: const EdgeInsets.only(bottom: 24),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.grey.shade300),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.05),
                                  blurRadius: 12,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                // Document Official Header
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
                                  decoration: BoxDecoration(
                                    color: Colors.grey.shade50,
                                    borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                                    border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
                                  ),
                                  child: LayoutBuilder(
                                    builder: (context, constraints) {
                                      final isNarrow = constraints.maxWidth < 650;
                                      final iconAndTitle = Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Container(
                                            width: 38,
                                            height: 38,
                                            decoration: BoxDecoration(
                                              color: AppColors.amityBlue,
                                              borderRadius: BorderRadius.circular(8),
                                            ),
                                            child: const Icon(Icons.school_rounded, color: Colors.white, size: 24),
                                          ),
                                          const SizedBox(width: 14),
                                          Flexible(
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                const Text(
                                                  'AMITY UNIVERSITY • OFFICIAL ACADEMIC & ADMINISTRATIVE NOTESHEET',
                                                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, letterSpacing: 0.5, color: AppColors.amityBlue),
                                                ),
                                                const SizedBox(height: 2),
                                                Text(
                                                  'Reference No: $refNo • Category: ${ns['category'] ?? 'General'}',
                                                  style: const TextStyle(fontSize: 12, color: Colors.black54),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      );

                                      final statusBadge = Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                        decoration: BoxDecoration(
                                          color: status == 'APPROVED'
                                              ? AppColors.successGreen
                                              : (status == 'REJECTED' ? AppColors.urgentRed : AppColors.amityYellow),
                                          borderRadius: BorderRadius.circular(12),
                                        ),
                                        child: Text(
                                          '$stage ($status)',
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                                        ),
                                      );

                                      if (isNarrow) {
                                        return Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            iconAndTitle,
                                            const SizedBox(height: 10),
                                            statusBadge,
                                          ],
                                        );
                                      }

                                      return Row(
                                        children: [
                                          Expanded(child: iconAndTitle),
                                          const SizedBox(width: 12),
                                          statusBadge,
                                        ],
                                      );
                                    },
                                  ),
                                ),

                                // Document Body (Word-file style)
                                Padding(
                                  padding: const EdgeInsets.all(28),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        title,
                                        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.black87),
                                      ),
                                      const SizedBox(height: 16),
                                      Container(
                                        padding: const EdgeInsets.all(20),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFFAFAFA),
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(color: Colors.grey.shade200),
                                        ),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: content.entries.map((entry) {
                                            return Padding(
                                              padding: const EdgeInsets.only(bottom: 12),
                                              child: Row(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  SizedBox(
                                                    width: 180,
                                                    child: Text(
                                                      '${entry.key.replaceAll('_', ' ').toUpperCase()}:',
                                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black54),
                                                    ),
                                                  ),
                                                  Expanded(
                                                    child: Text(
                                                      entry.value?.toString() ?? '',
                                                      style: const TextStyle(fontSize: 14, height: 1.4, color: Colors.black87),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            );
                                          }).toList(),
                                        ),
                                      ),

                                      const SizedBox(height: 24),
                                      const Divider(),
                                      const SizedBox(height: 14),

                                      // Digital Signatures Section
                                      Row(
                                        children: const [
                                          Icon(Icons.verified_user_rounded, color: AppColors.amityBlue, size: 20),
                                          SizedBox(width: 8),
                                          Text('OFFICIAL SIGNATURES & VERIFICATIONS', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, letterSpacing: 0.5)),
                                        ],
                                      ),
                                      const SizedBox(height: 14),

                                      // Signature Blocks
                                      Wrap(
                                        spacing: 16,
                                        runSpacing: 16,
                                        children: _stages.map((stg) {
                                          final sig = signatures.firstWhere((s) => s['stage'] == stg, orElse: () => null);
                                          final isSigned = sig != null;

                                          return Container(
                                            width: 220,
                                            padding: const EdgeInsets.all(14),
                                            decoration: BoxDecoration(
                                              color: isSigned ? Colors.blue.shade50 : Colors.grey.shade50,
                                              borderRadius: BorderRadius.circular(10),
                                              border: Border.all(
                                                color: isSigned ? AppColors.amityBlue.withValues(alpha: 0.4) : Colors.grey.shade300,
                                              ),
                                            ),
                                            child: Column(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Row(
                                                  children: [
                                                    Text(stg, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.amityBlue)),
                                                    const Spacer(),
                                                    Icon(
                                                      isSigned ? Icons.check_circle_rounded : Icons.pending_outlined,
                                                      size: 16,
                                                      color: isSigned ? AppColors.successGreen : Colors.grey,
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 8),
                                                if (isSigned) ...[
                                                  Text(sig['officer_name'] ?? 'Officer', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                                                  const SizedBox(height: 2),
                                                  Text(
                                                    '${sig['action']} • ${sig['signed_at']?.toString().substring(0, 10) ?? ''}',
                                                    style: const TextStyle(fontSize: 11, color: Colors.black54),
                                                  ),
                                                  const SizedBox(height: 4),
                                                  Text(
                                                    'Seal: ${sig['comments'] ?? 'Signed'}',
                                                    maxLines: 2,
                                                    overflow: TextOverflow.ellipsis,
                                                    style: const TextStyle(fontSize: 10, fontStyle: FontStyle.italic, color: Colors.black87),
                                                  ),
                                                ] else ...[
                                                  const SizedBox(height: 10),
                                                  const Text('Pending signature', style: TextStyle(fontSize: 11, color: Colors.grey)),
                                                ],
                                              ],
                                            ),
                                          );
                                        }).toList(),
                                      ),
                                    ],
                                  ),
                                ),

                                // Document Actions Bar
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                                  decoration: BoxDecoration(
                                    color: Colors.grey.shade50,
                                    borderRadius: const BorderRadius.vertical(bottom: Radius.circular(12)),
                                    border: Border(top: BorderSide(color: Colors.grey.shade200)),
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.stretch,
                                    children: [
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.end,
                                        children: [
                                          OutlinedButton.icon(
                                            icon: const Icon(Icons.download_rounded, size: 16, color: AppColors.amityBlue),
                                            label: const Text('Download DOCX'),
                                            onPressed: () {
                                              final url = ApiConfig.fullUrl('/api/notesheets/$refNo/docx');
                                              launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                                            },
                                          ),
                                          const SizedBox(width: 10),
                                          OutlinedButton.icon(
                                            icon: const Icon(Icons.picture_as_pdf_rounded, size: 16, color: Colors.red),
                                            label: const Text('Download PDF', style: TextStyle(color: Colors.red)),
                                            onPressed: () {
                                              final url = ApiConfig.fullUrl('/api/notesheets/$refNo/pdf');
                                              launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
                                            },
                                          ),
                                          const SizedBox(width: 10),
                                          FilledButton.tonalIcon(
                                            icon: const Icon(Icons.edit_document, size: 16),
                                            label: const Text('Full Word View & Edit'),
                                            onPressed: () => _showFullWordDocumentDialog(ns is Map ? Map<String, dynamic>.from(ns) : <String, dynamic>{}),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 14),
                                      _buildActionControls(
                                        context,
                                        ns is Map ? Map<String, dynamic>.from(ns) : <String, dynamic>{},
                                        ref,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
