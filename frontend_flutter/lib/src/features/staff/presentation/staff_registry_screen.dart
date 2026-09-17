import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/kiosk_theme.dart';

class StaffRegistryScreen extends StatefulWidget {
  const StaffRegistryScreen({super.key});

  @override
  State<StaffRegistryScreen> createState() => _StaffRegistryScreenState();
}

class _StaffRegistryScreenState extends State<StaffRegistryScreen> {
  bool _isLoading = true;
  List<dynamic> _roster = [];
  String _selectedBranch = 'CSE';
  int _suspendedCount = 0;
  int _debarredCount = 0;

  final List<String> _branches = ['CSE', 'ECE', 'MBA', 'Biotech'];
  final List<String> _statuses = ['ACTIVE', 'UNDER_CLEARANCE', 'WITHDRAWN', 'SUSPENDED', 'DEBARRED'];

  @override
  void initState() {
    super.initState();
    _fetchRoster();
  }

  Future<void> _fetchRoster() async {
    setState(() => _isLoading = true);
    try {
      final res = await http.get(Uri.parse('http://127.0.0.1:8000/api/registry/roster/$_selectedBranch'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        setState(() {
          _roster = data['roster'] ?? [];
          _suspendedCount = data['suspended_count'] ?? 0;
          _debarredCount = data['debarred_count'] ?? 0;
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _showUpdateStatusDialog(Map<String, dynamic> student) {
    final studentId = student['id'] ?? '';
    String selectedStatus = student['status'] ?? 'ACTIVE';
    final reasonController = TextEditingController();
    final officerController = TextEditingController(text: 'PROCTOR_BOARD_DESK');

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              const Icon(Icons.shield_rounded, color: AppColors.amityBlue),
              const SizedBox(width: 8),
              Text('Update Status: $studentId (${student['name']})'),
            ],
          ),
          content: SizedBox(
            width: 460,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Changing status to SUSPENDED or DEBARRED instantly broadcasts real-time entry locks across faculty attendance screens, exam hall scanners, and kiosks.',
                  style: TextStyle(fontSize: 13, color: Colors.black54),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: selectedStatus,
                  decoration: const InputDecoration(labelText: 'Operational Status', border: OutlineInputBorder()),
                  items: _statuses
                      .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setDialogState(() => selectedStatus = val);
                    }
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: reasonController,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Mandatory Reason / Reference',
                    hintText: 'e.g., Proctorial Inquiry PB-2026-092 or Attendance <60%',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: officerController,
                  decoration: const InputDecoration(labelText: 'Officer / Authority ID', border: OutlineInputBorder()),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: (selectedStatus == 'SUSPENDED' || selectedStatus == 'DEBARRED')
                    ? AppColors.urgentRed
                    : AppColors.amityBlue,
              ),
              onPressed: () async {
                final reason = reasonController.text.trim();
                if (reason.isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Mandatory reason required')),
                  );
                  return;
                }

                Navigator.pop(ctx);
                try {
                  final updateRes = await http.post(
                    Uri.parse('http://127.0.0.1:8000/api/registry/status/update'),
                    headers: {'Content-Type': 'application/json'},
                    body: jsonEncode({
                      'student_id': studentId,
                      'new_status': selectedStatus,
                      'reason': reason,
                      'updated_by': officerController.text.trim(),
                    }),
                  );
                  if (updateRes.statusCode == 200) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Student $studentId status updated to $selectedStatus!'),
                        backgroundColor: AppColors.successGreen,
                      ),
                    );
                    _fetchRoster();
                  }
                } catch (_) {}
              },
              child: const Text('Confirm Status Update', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }

  void _showHistoryDialog(String studentId) async {
    try {
      final res = await http.get(Uri.parse('http://127.0.0.1:8000/api/registry/history/$studentId'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final history = (data['history'] as List?) ?? [];

        if (!mounted) return;
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            title: Text('Status Audit History: $studentId'),
            content: SizedBox(
              width: 500,
              height: 350,
              child: history.isEmpty
                  ? const Center(child: Text('No previous status changes recorded.'))
                  : ListView.separated(
                      itemCount: history.length,
                      separatorBuilder: (c, i) => const Divider(),
                      itemBuilder: (c, i) {
                        final h = history[i];
                        return ListTile(
                          title: Text('${h['previous_status']} ➔ ${h['new_status']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text('Reason: ${h['reason']}\nBy: ${h['updated_by']} at ${h['updated_at']}'),
                        );
                      },
                    ),
            ),
            actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close'))],
          ),
        );
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Centralized Student Status Registry & Entry Locks'),
        backgroundColor: AppColors.amityBlue,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _fetchRoster, tooltip: 'Refresh Roster'),
        ],
      ),
      body: Column(
        children: [
          // Banner for warning metrics
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            color: Colors.grey.shade100,
            child: Row(
              children: [
                const Text('Branch / Roster: ', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _selectedBranch,
                  items: _branches
                      .map((b) => DropdownMenuItem(value: b, child: Text(b)))
                      .toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setState(() => _selectedBranch = val);
                      _fetchRoster();
                    }
                  },
                ),
                const Spacer(),
                if (_suspendedCount > 0) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(color: AppColors.urgentRed, borderRadius: BorderRadius.circular(12)),
                    child: Text('$_suspendedCount SUSPENDED', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                  ),
                  const SizedBox(width: 8),
                ],
                if (_debarredCount > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(color: Colors.orange.shade800, borderRadius: BorderRadius.circular(12)),
                    child: Text('$_debarredCount DEBARRED', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                  ),
              ],
            ),
          ),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _roster.isEmpty
                    ? const Center(child: Text('No enrolled students found.'))
                    : ListView.builder(
                        padding: const EdgeInsets.all(24),
                        itemCount: _roster.length,
                        itemBuilder: (ctx, idx) {
                          final stu = _roster[idx];
                          final id = stu['id'] ?? '';
                          final name = stu['name'] ?? '';
                          final status = stu['status'] ?? 'ACTIVE';
                          final isLocked = stu['attendance_locked'] == true;
                          final reason = stu['status_reason'] ?? '';

                          return Card(
                            margin: const EdgeInsets.only(bottom: 16),
                            elevation: isLocked ? 4 : 1,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: isLocked ? const BorderSide(color: AppColors.urgentRed, width: 2) : BorderSide.none,
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(20),
                              child: Row(
                                children: [
                                  CircleAvatar(
                                    backgroundColor: isLocked ? AppColors.urgentRed.withValues(alpha: 0.1) : AppColors.amityBlue.withValues(alpha: 0.1),
                                    child: Icon(
                                      isLocked ? Icons.lock_rounded : Icons.person_rounded,
                                      color: isLocked ? AppColors.urgentRed : AppColors.amityBlue,
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Text('$id - $name', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                                            const SizedBox(width: 12),
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                              decoration: BoxDecoration(
                                                color: isLocked ? AppColors.urgentRed : (status == 'UNDER_CLEARANCE' ? AppColors.amityYellow : AppColors.successGreen),
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: Text(
                                                status,
                                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 6),
                                        Text('Course: ${stu['course']} | Attendance: ${stu['attendance']}% | CGPA: ${stu['cgpa']}'),
                                        if (isLocked && reason.isNotEmpty) ...[
                                          const SizedBox(height: 6),
                                          Text(
                                            'Lock Justification: $reason',
                                            style: const TextStyle(color: AppColors.urgentRed, fontWeight: FontWeight.w600, fontSize: 13),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                  Column(
                                    children: [
                                      ElevatedButton.icon(
                                        icon: const Icon(Icons.edit, size: 16),
                                        label: const Text('Update Status'),
                                        onPressed: () => _showUpdateStatusDialog(stu),
                                      ),
                                      const SizedBox(height: 6),
                                      TextButton.icon(
                                        icon: const Icon(Icons.history, size: 16),
                                        label: const Text('Audit History'),
                                        onPressed: () => _showHistoryDialog(id),
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
