// ==============================================================================
// UniAssist — Universal Institution Configurator GUI
// Lead Architect: Abhishek Shrivastava
// ==============================================================================
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../../core/api_client.dart';
import '../../../core/theme/kiosk_theme.dart';

class StaffInstitutionScreen extends ConsumerStatefulWidget {
  const StaffInstitutionScreen({super.key});

  @override
  ConsumerState<StaffInstitutionScreen> createState() => _StaffInstitutionScreenState();
}

class _StaffInstitutionScreenState extends ConsumerState<StaffInstitutionScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Form Controllers for Branding
  final _nameController = TextEditingController(text: "Manipal University Jaipur");
  final _logoController = TextEditingController(text: "/assets/logos/manipal_logo.png");
  final _primaryColorController = TextEditingController(text: "#E05A2B");
  final _emailController = TextEditingController(text: "registrar@jaipur.manipal.edu");

  // Dynamic Clearance Desks State
  List<Map<String, dynamic>> _clearanceDesks = [
    {"desk_code": "LAB_INCHARGE", "desk_name": "Central Labs & Equipment", "sequence_order": 1},
    {"desk_code": "LIBRARY", "desk_name": "Central University Library", "sequence_order": 2},
    {"desk_code": "FINANCE", "desk_name": "Finance & Accounts Office", "sequence_order": 3},
    {"desk_code": "DEAN_ACADEMICS", "desk_name": "Dean of Academic Affairs", "sequence_order": 4},
  ];

  // Custom Refund Slabs State
  List<Map<String, dynamic>> _refundSlabs = [
    {
      "slab_label": "15 Days Prior to Formally Notified Deadline",
      "min_days": 15,
      "max_days": 9999,
      "refund_percent": 100.0,
      "policy_note": "100% refund minus max processing fee INR 1,000",
    },
    {
      "slab_label": "Less than 15 Days Prior to Deadline",
      "min_days": 1,
      "max_days": 14,
      "refund_percent": 90.0,
      "policy_note": "90% tuition refund",
    },
    {
      "slab_label": "Up to 15 Days Post Deadline",
      "min_days": 0,
      "max_days": 15,
      "refund_percent": 80.0,
      "policy_note": "80% tuition refund",
    },
    {
      "slab_label": "Between 16 and 30 Days Post Deadline",
      "min_days": 16,
      "max_days": 30,
      "refund_percent": 50.0,
      "policy_note": "50% tuition refund",
    },
  ];

  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadInitialData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _nameController.dispose();
    _logoController.dispose();
    _primaryColorController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Color _parseColor(String? hexString) {
    if (hexString == null || hexString.isEmpty) return const Color(0xFFE05A2B);
    try {
      final hex = hexString.replaceAll('#', '').trim();
      if (hex.length == 6) {
        return Color(int.parse('FF$hex', radix: 16));
      }
      return const Color(0xFFE05A2B);
    } catch (_) {
      return const Color(0xFFE05A2B);
    }
  }

  Future<void> _loadInitialData() async {
    try {
      final dio = ref.read(apiClientProvider);
      final cfgRes = await dio.get('/institution/config');
      final chainRes = await dio.get('/institution/clearance-chain');
      final slabsRes = await dio.get('/institution/refund-slabs');

      if (mounted) {
        setState(() {
          if (cfgRes.data is Map<String, dynamic>) {
            final cfg = cfgRes.data as Map<String, dynamic>;
            if (cfg['institution_name'] != null) _nameController.text = cfg['institution_name'].toString();
            if (cfg['crest_logo_url'] != null) _logoController.text = cfg['crest_logo_url'].toString();
            if (cfg['primary_color'] != null) _primaryColorController.text = cfg['primary_color'].toString();
            if (cfg['contact_email'] != null) _emailController.text = cfg['contact_email'].toString();
          }
          if (chainRes.data is Map<String, dynamic>) {
            final chain = (chainRes.data as Map<String, dynamic>)['chain'] as List?;
            if (chain != null && chain.isNotEmpty) {
              _clearanceDesks = chain.map((e) => Map<String, dynamic>.from(e as Map)).toList();
            }
          }
          if (slabsRes.data is Map<String, dynamic>) {
            final slabs = (slabsRes.data as Map<String, dynamic>)['slabs'] as List?;
            if (slabs != null && slabs.isNotEmpty) {
              _refundSlabs = slabs.map((e) => Map<String, dynamic>.from(e as Map)).toList();
            }
          }
        });
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Universal Institution Configurator'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.palette_rounded), text: 'Branding & Theme'),
            Tab(icon: Icon(Icons.account_tree_rounded), text: 'Clearance Chain'),
            Tab(icon: Icon(Icons.calculate_rounded), text: 'Refund Slabs'),
            Tab(icon: Icon(Icons.auto_stories_rounded), text: 'AI Handbook Ingestion'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildBrandingTab(),
          _buildClearanceChainTab(),
          _buildRefundSlabsTab(),
          _buildHandbookIngestionTab(),
        ],
      ),
    );
  }

  // ── Tab 1: Branding & Identity ─────────────────────────────────────────────
  Widget _buildBrandingTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Institutional Identity (White-Label Setup)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(
            'Configure university crest, name, and brand colors across all student kiosks and staff portals.',
            style: TextStyle(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'University Name', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _logoController,
            decoration: const InputDecoration(labelText: 'Crest Logo URL', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _primaryColorController,
                  onChanged: (val) => setState(() {}),
                  decoration: const InputDecoration(
                    labelText: 'Primary Brand Color (Hex)',
                    border: OutlineInputBorder(),
                    hintText: '#E05A2B',
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: _parseColor(_primaryColorController.text),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade300),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _emailController,
            decoration: const InputDecoration(labelText: 'Registrar Official Email', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _isSaving ? null : _saveBranding,
            icon: const Icon(Icons.save_rounded),
            label: const Text('Apply Institutional Branding'),
          ),
        ],
      ),
    );
  }

  // ── Tab 2: Dynamic Clearance Desks ─────────────────────────────────────────
  Widget _buildClearanceChainTab() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Sequential Clearance Chain', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text('Drag to reorder approval sequence or add new department gates.', style: TextStyle(color: Colors.grey.shade600)),
                ],
              ),
              OutlinedButton.icon(
                onPressed: _addNewDeskDialog,
                icon: const Icon(Icons.add),
                label: const Text('Add Clearance Desk'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ReorderableListView(
              onReorder: (oldIdx, newIdx) {
                setState(() {
                  if (newIdx > oldIdx) newIdx -= 1;
                  final item = _clearanceDesks.removeAt(oldIdx);
                  _clearanceDesks.insert(newIdx, item);
                  for (int i = 0; i < _clearanceDesks.length; i++) {
                    _clearanceDesks[i]['sequence_order'] = i + 1;
                  }
                });
              },
              children: [
                for (final desk in _clearanceDesks)
                  Card(
                    key: ValueKey(desk['desk_code']),
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: AppColors.primary.withValues(alpha: 0.1),
                        child: Text('${desk['sequence_order']}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.primary)),
                      ),
                      title: Text(desk['desk_name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
                      subtitle: Text('Desk Code: ${desk['desk_code']}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.delete_outline, color: Colors.red, size: 20),
                            onPressed: () {
                              setState(() {
                                _clearanceDesks.removeWhere((d) => d['desk_code'] == desk['desk_code']);
                                for (int i = 0; i < _clearanceDesks.length; i++) {
                                  _clearanceDesks[i]['sequence_order'] = i + 1;
                                }
                              });
                            },
                          ),
                          const Icon(Icons.drag_handle_rounded),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          FilledButton.icon(
            onPressed: _isSaving ? null : _saveClearanceChain,
            icon: const Icon(Icons.check_circle),
            label: const Text('Save Clearance Chain Configuration'),
          ),
        ],
      ),
    );
  }

  // ── Tab 3: Custom Refund Slabs ─────────────────────────────────────────────
  Widget _buildRefundSlabsTab() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('UGC-Aligned Custom Refund Day Slabs', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text('Define institution-specific day cutoff brackets and refund percentages.', style: TextStyle(color: Colors.grey.shade600)),
                ],
              ),
              FilledButton.icon(
                onPressed: _isSaving ? null : _saveRefundSlabs,
                icon: const Icon(Icons.save_rounded),
                label: const Text('Save Refund Slabs'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.builder(
              itemCount: _refundSlabs.length,
              itemBuilder: (ctx, idx) {
                final slab = _refundSlabs[idx];
                final percent = (slab['refund_percent'] is num ? slab['refund_percent'] as num : 0).toDouble();
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Colors.blue.shade50,
                      child: Text('${percent.toInt()}%', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.blue.shade800)),
                    ),
                    title: Text(slab['slab_label'] ?? 'Refund Bracket', style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('Window: ${slab['min_days']} - ${slab['max_days']} days • ${slab['policy_note'] ?? ""}'),
                    trailing: Chip(
                      label: Text('${percent.toInt()}% Refund'),
                      backgroundColor: percent >= 80 ? Colors.green.shade50 : Colors.amber.shade50,
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

  // ── Tab 4: AI Handbook Ingestion ───────────────────────────────────────────
  Widget _buildHandbookIngestionTab() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('AI Handbook Ingestion (Zero-Retraining RAG)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(
            'Upload the official University Regulations or Academic Handbook PDF. The system extracts clauses and indexes them into SQLite FTS5 in sub-5ms.',
            style: TextStyle(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(32),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade300, style: BorderStyle.solid),
              borderRadius: BorderRadius.circular(16),
              color: Colors.grey.shade50,
            ),
            child: Center(
              child: Column(
                children: [
                  const Icon(Icons.cloud_upload_outlined, size: 56, color: AppColors.primary),
                  const SizedBox(height: 12),
                  const Text('Select University Ordinance / Handbook PDF', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text('e.g. Manipal_Regulations_2026.pdf (Max 25 MB)', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  const SizedBox(height: 20),
                  FilledButton.icon(
                    onPressed: _isSaving ? null : _uploadHandbookMock,
                    icon: const Icon(Icons.file_open_rounded),
                    label: const Text('Browse & Ingest into AI Engine'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── API Actions & Connectivity ─────────────────────────────────────────────

  Future<void> _saveBranding() async {
    setState(() => _isSaving = true);
    try {
      final dio = ref.read(apiClientProvider);
      final res = await dio.post(
        '/institution/branding',
        data: {
          'institution_name': _nameController.text.trim(),
          'crest_logo_url': _logoController.text.trim(),
          'primary_color': _primaryColorController.text.trim(),
          'secondary_color': '#1A2B4C',
          'contact_email': _emailController.text.trim(),
          'contact_phone': '+91-141-3999100',
          'kiosk_welcome_title': 'Welcome to ${_nameController.text.trim()} Student Services Hub',
        },
      );
      if (mounted) {
        final msg = res.data is Map ? res.data['message']?.toString() : null;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg ?? 'Branding updated successfully.'),
            backgroundColor: AppColors.successGreen,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update branding: $e'),
            backgroundColor: AppColors.urgentRed,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _saveClearanceChain() async {
    setState(() => _isSaving = true);
    try {
      final dio = ref.read(apiClientProvider);
      final chainData = _clearanceDesks.map((d) => {
        'desk_code': d['desk_code'],
        'desk_name': d['desk_name'],
        'description': d['description'] ?? '',
        'sequence_order': d['sequence_order'],
        'is_active': d['is_active'] ?? true,
      }).toList();

      final res = await dio.post(
        '/institution/clearance-chain',
        data: {'chain': chainData},
      );
      if (mounted) {
        final msg = res.data is Map ? res.data['message']?.toString() : null;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg ?? 'Clearance chain updated successfully.'),
            backgroundColor: AppColors.successGreen,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update clearance chain: $e'),
            backgroundColor: AppColors.urgentRed,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _saveRefundSlabs() async {
    setState(() => _isSaving = true);
    try {
      final dio = ref.read(apiClientProvider);
      final slabsData = _refundSlabs.map((s) => {
        'slab_label': s['slab_label'],
        'min_days': s['min_days'],
        'max_days': s['max_days'],
        'refund_percent': s['refund_percent'],
        'policy_note': s['policy_note'] ?? '',
      }).toList();

      final res = await dio.post(
        '/institution/refund-slabs',
        data: {'slabs': slabsData},
      );
      if (mounted) {
        final msg = res.data is Map ? res.data['message']?.toString() : null;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg ?? 'Refund slabs saved successfully.'),
            backgroundColor: AppColors.successGreen,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save refund slabs: $e'),
            backgroundColor: AppColors.urgentRed,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _addNewDeskDialog() async {
    final codeController = TextEditingController();
    final nameController = TextEditingController();

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Add Clearance Desk Gate', style: TextStyle(fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Desk Code (e.g. SPORTS_DEPT, PROCTORIAL_CELL):', style: TextStyle(fontSize: 12)),
            const SizedBox(height: 6),
            TextField(
              controller: codeController,
              decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'SPORTS_DEPT'),
            ),
            const SizedBox(height: 14),
            const Text('Desk Name:', style: TextStyle(fontSize: 12)),
            const SizedBox(height: 6),
            TextField(
              controller: nameController,
              decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'Sports & Athletics Cell'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final code = codeController.text.trim().toUpperCase();
              final name = nameController.text.trim();
              if (code.isNotEmpty && name.isNotEmpty) {
                setState(() {
                  _clearanceDesks.add({
                    'desk_code': code,
                    'desk_name': name,
                    'sequence_order': _clearanceDesks.length + 1,
                  });
                });
                Navigator.pop(ctx);
              }
            },
            child: const Text('Add Gate'),
          ),
        ],
      ),
    );
  }

  Future<void> _uploadHandbookMock() async {
    final fileNameController = TextEditingController(text: 'Manipal_Academic_Handbook_2026.pdf');
    final categoryController = TextEditingController(text: 'Academics & Regulations');
    final institutionController = TextEditingController(text: _nameController.text.trim());
    final contentController = TextEditingController(
      text: '%PDF-1.4\n'
          'Manipal University Jaipur Academic Ordinances 2026 Handbook.\n\n'
          'Ordinance 14.1 Degree Award Eligibility Criteria:\n'
          'A student must secure a minimum Cumulative Grade Point Average (CGPA) of 5.0 and earn all specified branch credits without any standing backlog to be eligible for degree conferment.\n\n'
          'Ordinance 14.2 Examination Debarment and Attendance Condonation:\n'
          'Students maintaining below 75% attendance are debarred from end-semester examinations unless approved by Dean Academic through documented medical condonation.\n\n'
          'Section 5.3 Special Fee Concession and Scholarship Offsetting:\n'
          'Merit scholarship holders may offset their semester tuition fee against their enrolled scholarship grant during pre-registration clearance.',
    );

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.auto_stories_rounded, color: AppColors.primary),
            ),
            const SizedBox(width: 10),
            const Text('Upload & Ingest Handbook', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        content: SizedBox(
          width: 550,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Select or Confirm PDF File Name:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: fileNameController,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.picture_as_pdf, color: Colors.red),
                    border: OutlineInputBorder(),
                    hintText: 'e.g. Manipal_Regulations_2026.pdf',
                  ),
                ),
                const SizedBox(height: 14),
                const Text('University / Institution Name:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: institutionController,
                  decoration: const InputDecoration(border: OutlineInputBorder()),
                ),
                const SizedBox(height: 14),
                const Text('Category:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: categoryController,
                  decoration: const InputDecoration(border: OutlineInputBorder()),
                ),
                const SizedBox(height: 14),
                const Text('Handbook Regulations Content Stream:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                const SizedBox(height: 6),
                TextField(
                  controller: contentController,
                  maxLines: 6,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    hintText: 'Enter regulation text or ordinances to be parsed into FTS5...',
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
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
            icon: const Icon(Icons.cloud_upload_rounded),
            label: const Text('Ingest into SQLite FTS5'),
            onPressed: () async {
              Navigator.pop(ctx);
              setState(() => _isSaving = true);
              try {
                final dio = ref.read(apiClientProvider);
                final bytes = utf8.encode(contentController.text);
                final formData = FormData.fromMap({
                  'file': MultipartFile.fromBytes(bytes, filename: fileNameController.text.trim()),
                  'category': categoryController.text.trim(),
                  'institution_name': institutionController.text.trim(),
                });

                final res = await dio.post('/policy/admin/upload-handbook', data: formData);
                if (mounted) {
                  final msg = res.data is Map ? res.data['message']?.toString() : null;
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(msg ?? 'Handbook successfully parsed and indexed!'),
                      backgroundColor: AppColors.successGreen,
                    ),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Failed to ingest handbook: $e'),
                      backgroundColor: AppColors.urgentRed,
                    ),
                  );
                }
              } finally {
                if (mounted) {
                  setState(() => _isSaving = false);
                }
              }
            },
          ),
        ],
      ),
    );
  }
}
