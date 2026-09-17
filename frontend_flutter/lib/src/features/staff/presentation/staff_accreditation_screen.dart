import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/kiosk_theme.dart';

/// Phase 27: Staff Accreditation Hub.
/// Displays CO/PO attainment reports with color-coded cells,
/// branch/semester filters, and 1-click CSV/PDF export.
class StaffAccreditationScreen extends StatefulWidget {
  const StaffAccreditationScreen({super.key});

  @override
  State<StaffAccreditationScreen> createState() => _StaffAccreditationScreenState();
}

class _StaffAccreditationScreenState extends State<StaffAccreditationScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  String _selectedBranch = 'CSE';
  int? _selectedSemester;
  Map<String, dynamic> _coReport = {};
  Map<String, dynamic> _poReport = {};

  final List<String> _branches = ['CSE', 'ECE', 'MBA', 'Biotech'];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _fetchReports();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchReports() async {
    setState(() => _isLoading = true);
    try {
      String coUrl = 'http://127.0.0.1:8000/api/accreditation/co-attainment?branch=$_selectedBranch';
      if (_selectedSemester != null) coUrl += '&semester=$_selectedSemester';
      final coRes = await http.get(Uri.parse(coUrl));

      final poRes = await http.get(
          Uri.parse('http://127.0.0.1:8000/api/accreditation/po-attainment?branch=$_selectedBranch'));

      if (coRes.statusCode == 200) _coReport = jsonDecode(coRes.body);
      if (poRes.statusCode == 200) _poReport = jsonDecode(poRes.body);

      setState(() => _isLoading = false);
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  Color _attainmentColor(String status) {
    return status == 'ATTAINED' ? AppColors.successGreen : AppColors.urgentRed;
  }

  Color _poLevelColor(String level) {
    switch (level) {
      case 'HIGH':
        return AppColors.successGreen;
      case 'MEDIUM':
        return Colors.amber.shade700;
      case 'LOW':
        return AppColors.urgentRed;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('Accreditation Hub — CO/PO Reports'),
        elevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF6A1B9A), Color(0xFFAB47BC)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          tabs: const [
            Tab(text: 'CO Attainment'),
            Tab(text: 'PO Matrix'),
          ],
        ),
      ),
      body: Column(
        children: [
          // Filter bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                // Branch selector
                DropdownButton<String>(
                  value: _selectedBranch,
                  items: _branches.map((b) => DropdownMenuItem(value: b, child: Text(b))).toList(),
                  onChanged: (v) {
                    if (v != null) {
                      _selectedBranch = v;
                      _fetchReports();
                    }
                  },
                ),
                const SizedBox(width: 16),
                // Semester selector
                DropdownButton<int?>(
                  value: _selectedSemester,
                  hint: const Text('All Semesters'),
                  items: [
                    const DropdownMenuItem(value: null, child: Text('All Semesters')),
                    ...List.generate(8, (i) => DropdownMenuItem(value: i + 1, child: Text('Sem ${i + 1}'))),
                  ],
                  onChanged: (v) {
                    _selectedSemester = v;
                    _fetchReports();
                  },
                ),
                const Spacer(),
                // Export buttons
                OutlinedButton.icon(
                  onPressed: () => _downloadExport('csv'),
                  icon: const Icon(Icons.download_rounded, size: 18),
                  label: const Text('CSV'),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: () => _downloadExport('pdf'),
                  icon: const Icon(Icons.picture_as_pdf_rounded, size: 18),
                  label: const Text('PDF'),
                  style: ElevatedButton.styleFrom(backgroundColor: AppColors.amityBlue),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          // Tab content
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(
                    controller: _tabController,
                    children: [
                      _buildCoTab(),
                      _buildPoTab(),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  void _downloadExport(String format) {
    // In real app, this would trigger file download
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Downloading NAAC report as ${format.toUpperCase()}...'),
        backgroundColor: AppColors.amityBlue,
      ),
    );
  }

  Widget _buildCoTab() {
    final courses = (_coReport['courses'] as List?) ?? [];
    if (courses.isEmpty) {
      return const Center(child: Text('No CO attainment data available for this branch.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: courses.length,
      itemBuilder: (ctx, idx) {
        final course = courses[idx];
        final cos = (course['cos'] as List?) ?? [];
        return Card(
          margin: const EdgeInsets.only(bottom: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${course['course_code']} — ${course['course_name']}',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                Text('Semester ${course['semester']}', style: TextStyle(color: Colors.grey.shade600)),
                const SizedBox(height: 12),
                // CO table
                Table(
                  border: TableBorder.all(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(8)),
                  columnWidths: const {
                    0: FixedColumnWidth(60),
                    1: FlexColumnWidth(3),
                    2: FixedColumnWidth(80),
                    3: FixedColumnWidth(80),
                    4: FixedColumnWidth(90),
                  },
                  children: [
                    TableRow(
                      decoration: BoxDecoration(color: AppColors.amityBlue.withValues(alpha: 0.1)),
                      children: const [
                        Padding(padding: EdgeInsets.all(8), child: Text('CO', style: TextStyle(fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Description', style: TextStyle(fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Attain %', style: TextStyle(fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Target %', style: TextStyle(fontWeight: FontWeight.bold))),
                        Padding(padding: EdgeInsets.all(8), child: Text('Status', style: TextStyle(fontWeight: FontWeight.bold))),
                      ],
                    ),
                    ...cos.map((co) {
                      final status = co['status'] ?? 'NOT_ATTAINED';
                      final color = _attainmentColor(status);
                      return TableRow(
                        children: [
                          Padding(padding: const EdgeInsets.all(8), child: Text(co['co_code'] ?? '')),
                          Padding(padding: const EdgeInsets.all(8), child: Text(co['co_description'] ?? '', overflow: TextOverflow.ellipsis)),
                          Padding(padding: const EdgeInsets.all(8), child: Text('${co['attainment_percentage']}%')),
                          Padding(padding: const EdgeInsets.all(8), child: Text('${co['target_attainment']}%')),
                          Padding(
                            padding: const EdgeInsets.all(6),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(status, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 11), textAlign: TextAlign.center),
                            ),
                          ),
                        ],
                      );
                    }),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildPoTab() {
    final poMatrix = (_poReport['po_matrix'] as List?) ?? [];
    if (poMatrix.isEmpty) {
      return const Center(child: Text('No PO attainment data available.'));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Program Outcome Attainment Matrix — $_selectedBranch',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: poMatrix.map<Widget>((po) {
                  final level = po['attainment_level'] ?? 'NONE';
                  final color = _poLevelColor(level);
                  return Container(
                    width: 140,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: color.withValues(alpha: 0.3)),
                    ),
                    child: Column(
                      children: [
                        Text(po['po_code'] ?? '', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: color)),
                        const SizedBox(height: 4),
                        Text('Avg: ${po['average_correlation_weight']}', style: TextStyle(color: Colors.grey.shade700, fontSize: 12)),
                        Text('COs: ${po['contributing_cos']}', style: TextStyle(color: Colors.grey.shade600, fontSize: 11)),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(color: color.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(8)),
                          child: Text(level, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 10)),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
