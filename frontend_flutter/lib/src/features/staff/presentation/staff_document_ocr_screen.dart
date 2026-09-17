import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/kiosk_theme.dart';

/// Phase 25: Staff Document OCR Cockpit.
/// Displays uploaded documents with extracted OCR fields and identity
/// cross-check indicators (MATCH / MISMATCH / NOT_FOUND).
class StaffDocumentOcrScreen extends StatefulWidget {
  const StaffDocumentOcrScreen({super.key});

  @override
  State<StaffDocumentOcrScreen> createState() => _StaffDocumentOcrScreenState();
}

class _StaffDocumentOcrScreenState extends State<StaffDocumentOcrScreen> {
  bool _isLoading = true;
  List<dynamic> _documents = [];
  String _filterStatus = 'ALL';

  @override
  void initState() {
    super.initState();
    _fetchDocuments();
  }

  Future<void> _fetchDocuments() async {
    setState(() => _isLoading = true);
    try {
      final res = await http.get(Uri.parse('http://127.0.0.1:8000/api/documents/admin/audit-log'));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as List;
        setState(() {
          _documents = data;
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  Color _matchColor(String? match) {
    switch (match) {
      case 'MATCH':
        return AppColors.successGreen;
      case 'MISMATCH':
        return AppColors.urgentRed;
      case 'NOT_FOUND':
        return Colors.amber.shade700;
      default:
        return Colors.grey;
    }
  }

  IconData _matchIcon(String? match) {
    switch (match) {
      case 'MATCH':
        return Icons.check_circle_rounded;
      case 'MISMATCH':
        return Icons.error_rounded;
      case 'NOT_FOUND':
        return Icons.help_rounded;
      default:
        return Icons.remove_circle_outline;
    }
  }

  List<dynamic> get _filteredDocs {
    if (_filterStatus == 'ALL') return _documents;
    return _documents.where((d) {
      final match = d['ocr_identity_match'] ?? 'NOT_CHECKED';
      return match == _filterStatus;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('OCR Document Cockpit'),
        elevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [AppColors.amityBlue, Color(0xFF1565C0)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Filter bar
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.filter_list, color: AppColors.amityBlue),
                      const SizedBox(width: 12),
                      ..._buildFilterChips(),
                      const Spacer(),
                      Text('${_filteredDocs.length} documents',
                          style: TextStyle(color: Colors.grey.shade600, fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
                const Divider(height: 1),
                // Document list
                Expanded(
                  child: _filteredDocs.isEmpty
                      ? const Center(child: Text('No documents found.'))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredDocs.length,
                          itemBuilder: (ctx, idx) => _buildDocumentCard(_filteredDocs[idx]),
                        ),
                ),
              ],
            ),
    );
  }

  List<Widget> _buildFilterChips() {
    final filters = ['ALL', 'MATCH', 'MISMATCH', 'NOT_FOUND'];
    return filters.map((f) {
      final isActive = _filterStatus == f;
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: FilterChip(
          label: Text(f),
          selected: isActive,
          selectedColor: AppColors.amityBlue.withValues(alpha: 0.2),
          onSelected: (_) => setState(() => _filterStatus = f),
        ),
      );
    }).toList();
  }

  Widget _buildDocumentCard(dynamic doc) {
    final ocrData = doc['ocr_data'] is Map ? doc['ocr_data'] : {};
    final match = doc['ocr_identity_match'] ?? ocrData['ocr_identity_match'] ?? 'NOT_CHECKED';
    final matchColor = _matchColor(match);

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Document info
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.insert_drive_file_rounded, color: AppColors.amityBlue, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          doc['file_name'] ?? 'Unknown',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('Student: ${doc['student_id'] ?? '—'}  •  Type: ${doc['classification'] ?? '—'}',
                      style: TextStyle(color: Colors.grey.shade600)),
                  const SizedBox(height: 4),
                  Text('Status: ${doc['verification_status'] ?? '—'}',
                      style: TextStyle(
                        color: doc['verification_status'] == 'verified' ? AppColors.successGreen : Colors.grey.shade700,
                        fontWeight: FontWeight.w500,
                      )),
                ],
              ),
            ),
            const SizedBox(width: 20),
            // OCR extracted fields
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('OCR Extracted Fields', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey.shade800)),
                  const SizedBox(height: 8),
                  _ocrField('Name', ocrData['extracted_name']),
                  _ocrField('Student ID', ocrData['extracted_student_id']),
                  _ocrField('Date', ocrData['extracted_date']),
                  _ocrField('Confidence', '${((ocrData['confidence_score'] ?? 0) * 100).toStringAsFixed(0)}%'),
                ],
              ),
            ),
            const SizedBox(width: 20),
            // Identity match badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: matchColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: matchColor.withValues(alpha: 0.3)),
              ),
              child: Column(
                children: [
                  Icon(_matchIcon(match), color: matchColor, size: 32),
                  const SizedBox(height: 6),
                  Text(
                    match,
                    style: TextStyle(color: matchColor, fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                  const SizedBox(height: 2),
                  Text('ID Check', style: TextStyle(color: Colors.grey.shade500, fontSize: 10)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ocrField(String label, dynamic value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          SizedBox(
            width: 80,
            child: Text('$label:', style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
          ),
          Expanded(
            child: Text(
              value?.toString() ?? '—',
              style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
