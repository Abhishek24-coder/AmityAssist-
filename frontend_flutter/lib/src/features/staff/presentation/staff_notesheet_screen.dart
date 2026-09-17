import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/kiosk_theme.dart';

class StaffNotesheetScreen extends StatefulWidget {
  const StaffNotesheetScreen({super.key});

  @override
  State<StaffNotesheetScreen> createState() => _StaffNotesheetScreenState();
}

class _StaffNotesheetScreenState extends State<StaffNotesheetScreen> {
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
      String url = 'http://127.0.0.1:8000/api/notesheets';
      final params = <String, String>{};
      if (_currentStageFilter != 'ALL') {
        params['stage'] = _currentStageFilter;
      }
      if (_selectedCategory != null && _selectedCategory != 'All') {
        params['category'] = _selectedCategory!;
      }
      if (params.isNotEmpty) {
        url += '?${Uri(queryParameters: params).query}';
      }

      final res = await http.get(Uri.parse(url));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        setState(() {
          _notesheets = data['notesheets'] ?? [];
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _performAction(String refNo, String action, String stage) async {
    try {
      final res = await http.post(
        Uri.parse('http://127.0.0.1:8000/api/notesheets/$refNo/action'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'officer_id': 'STAFF_CURRENT',
          'officer_name': 'Senior Administrative Officer',
          'role': stage,
          'action': action,
          'comments': 'Signed and processed via Staff Digital Notesheet Cockpit',
        }),
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
              content: Text('Action failed: ${res.body}'),
              backgroundColor: AppColors.urgentRed,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: AppColors.urgentRed),
        );
      }
    }
  }

  void _showInFlightEditDialog(Map<String, dynamic> ns) {
    final content = ns['content'] is Map ? ns['content'] as Map<String, dynamic> : <String, dynamic>{};
    final refNo = ns['reference_no'];
    String selectedField = content.keys.isNotEmpty ? content.keys.first : 'course_code';
    final valController = TextEditingController(text: content[selectedField]?.toString() ?? '');
    final reasonController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              const Icon(Icons.edit_note_rounded, color: AppColors.amityBlue),
              const SizedBox(width: 8),
              Text('In-Flight Edit: $refNo'),
            ],
          ),
          content: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Correct typographical errors or course codes in-flight without resetting the approval hierarchy.',
                  style: TextStyle(fontSize: 13, color: Colors.black54),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: selectedField,
                  decoration: const InputDecoration(labelText: 'Field to Modify', border: OutlineInputBorder()),
                  items: content.keys
                      .map((k) => DropdownMenuItem(value: k, child: Text(k)))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setDialogState(() {
                        selectedField = val;
                        valController.text = content[val]?.toString() ?? '';
                      });
                    }
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: valController,
                  decoration: const InputDecoration(labelText: 'New Corrected Value', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: reasonController,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Mandatory Audit Justification',
                    hintText: 'e.g., Corrected course code typo from CS101 to CSE101',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.amityBlue),
              onPressed: () async {
                final reason = reasonController.text.trim();
                if (reason.isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Audit reason is mandatory')),
                  );
                  return;
                }

                Navigator.pop(ctx);
                try {
                  final editRes = await http.post(
                    Uri.parse('http://127.0.0.1:8000/api/notesheets/$refNo/edit-field'),
                    headers: {'Content-Type': 'application/json'},
                    body: jsonEncode({
                      'officer_id': 'STAFF_OFFICER',
                      'officer_role': ns['current_stage'] ?? 'HOD',
                      'field_name': selectedField,
                      'new_value': valController.text.trim(),
                      'reason': reason,
                    }),
                  );
                  if (editRes.statusCode == 200) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('In-flight correction saved with audit log!'), backgroundColor: AppColors.successGreen),
                    );
                    _fetchNotesheets();
                  }
                } catch (_) {}
              },
              child: const Text('Apply Correction', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Digital Notesheet Hierarchy & In-Flight Edits'),
        backgroundColor: AppColors.amityBlue,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchNotesheets, tooltip: 'Refresh'),
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

                          return Card(
                            margin: const EdgeInsets.only(bottom: 16),
                            elevation: 2,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            child: Padding(
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: AppColors.amityBlue.withValues(alpha: 0.1),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Text(refNo, style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.amityBlue)),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                                      ),
                                      Container(
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
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Text('Student ID: ${ns['student_id'] ?? 'N/A'} | Category: ${ns['category'] ?? 'General'}'),
                                  const SizedBox(height: 8),

                                  // Content Preview Chip
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade50,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(color: Colors.grey.shade300),
                                    ),
                                    child: Text(
                                      'Content Fields: ${content.entries.map((e) => '${e.key}: ${e.value}').join(' | ')}',
                                      style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
                                    ),
                                  ),

                                  const SizedBox(height: 16),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.end,
                                    children: [
                                      OutlinedButton.icon(
                                        icon: const Icon(Icons.edit, size: 16),
                                        label: const Text('In-Flight Edit'),
                                        onPressed: status == 'IN_REVIEW' ? () => _showInFlightEditDialog(ns) : null,
                                      ),
                                      const SizedBox(width: 12),
                                      OutlinedButton.icon(
                                        icon: const Icon(Icons.close, color: Colors.red, size: 16),
                                        label: const Text('Reject', style: TextStyle(color: Colors.red)),
                                        onPressed: status == 'IN_REVIEW' ? () => _performAction(refNo, 'REJECT', stage) : null,
                                      ),
                                      const SizedBox(width: 12),
                                      ElevatedButton.icon(
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: stage == 'VC' ? AppColors.successGreen : AppColors.amityBlue,
                                        ),
                                        icon: Icon(stage == 'VC' ? Icons.check_circle : Icons.send, size: 16, color: Colors.white),
                                        label: Text(
                                          stage == 'VC' ? 'Final Approve' : 'Forward ➔ Next Stage',
                                          style: const TextStyle(color: Colors.white),
                                        ),
                                        onPressed: status == 'IN_REVIEW' ? () => _performAction(refNo, stage == 'VC' ? 'APPROVE' : 'FORWARD', stage) : null,
                                      ),
                                    ],
                                  ),
                                ],
                              ),
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
