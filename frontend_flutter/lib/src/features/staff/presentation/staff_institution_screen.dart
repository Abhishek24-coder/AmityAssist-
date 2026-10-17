import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../application/institution_modules_provider.dart';

/// Phase 28 + Phase 30: Staff Institution Configurator.
/// Admin Settings screen for university branding, dynamic clearance chain
/// management, custom refund slab editing, module switchboard, and procedure step customizer.
class StaffInstitutionScreen extends ConsumerStatefulWidget {
  const StaffInstitutionScreen({super.key});

  @override
  ConsumerState<StaffInstitutionScreen> createState() => _StaffInstitutionScreenState();
}

class _StaffInstitutionScreenState extends ConsumerState<StaffInstitutionScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  Map<String, dynamic> _config = {};
  List<dynamic> _clearanceChain = [];
  List<dynamic> _refundSlabs = [];
  Map<String, dynamic> _modules = {};
  List<dynamic> _procedureSteps = [];
  final String _selectedProcedureCode = 'withdrawal';
  List<dynamic> _policies = [];
  String _policySearchQuery = '';
  String _selectedPolicyCategory = 'All';

  static const List<Map<String, String>> _availableModules = [
    {
      'id': 'dashboard',
      'title': 'Student & Admin Dashboard',
      'description': 'Central statistics, status cards, and metric overviews.',
      'icon': 'dashboard',
    },
    {
      'id': 'academics',
      'title': 'Academic Cell & Course Records',
      'description': 'Credits, semester tracking, and curriculum mapping.',
      'icon': 'school',
    },
    {
      'id': 'withdrawal',
      'title': 'Withdrawal & Clearance Cockpit',
      'description': 'Multi-gate student exit workflow, caution refund offsets.',
      'icon': 'exit_to_app',
    },
    {
      'id': 'forms',
      'title': 'Forms & Applications Catalog',
      'description': '31+ downloadable academic, financial, and logistics forms.',
      'icon': 'folder_shared',
    },
    {
      'id': 'grievance',
      'title': 'Student Grievance Redressal Desk',
      'description': 'Mandatory SLA ticket logging, tracking, and staff escalation.',
      'icon': 'support_agent',
    },
    {
      'id': 'scholarships',
      'title': 'Scholarships & Financial Aid',
      'description': 'Merit renewal criteria and tuition concessions.',
      'icon': 'monetization_on',
    },
    {
      'id': 'hostel',
      'title': 'Hostel & Accommodation Desk',
      'description': 'Room allocation, warden clearance, mess records.',
      'icon': 'apartment',
    },
    {
      'id': 'examinations',
      'title': 'Examination & Rechecking Portal',
      'description': 'Exam eligibility, re-evaluation, and Form EX-02.',
      'icon': 'assignment',
    },
    {
      'id': 'voice_ai',
      'title': 'AI Counselor & Voice Assistance',
      'description': 'Hands-free speech navigation, bilingual counsel.',
      'icon': 'record_voice_over',
    },
    {
      'id': 'documents',
      'title': 'Verified Documents & Vault',
      'description': 'Digital document verification, bonafide certificates.',
      'icon': 'verified_user',
    },
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 6, vsync: this);
    _fetchAll();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchAll() async {
    setState(() => _isLoading = true);
    try {
      final client = ref.read(apiClientProvider);
      final configRes = await client.get('/institution/config');
      final chainRes = await client.get('/institution/clearance-chain');
      final slabRes = await client.get('/institution/refund-slabs');
      final modulesRes = await client.get('/institution/modules');
      final stepsRes = await client.get('/procedures/$_selectedProcedureCode/steps');
      final policyRes = await client.get('/policy/admin/list');

      if (mounted) {
        setState(() {
          if (configRes.data is Map<String, dynamic>) {
            _config = configRes.data as Map<String, dynamic>;
          }
          if (chainRes.data is Map<String, dynamic>) {
            _clearanceChain = (chainRes.data as Map<String, dynamic>)['chain'] as List? ?? [];
          }
          if (slabRes.data is Map<String, dynamic>) {
            _refundSlabs = (slabRes.data as Map<String, dynamic>)['slabs'] as List? ?? [];
          }
          if (modulesRes.data is Map<String, dynamic>) {
            _modules = (modulesRes.data as Map<String, dynamic>)['modules'] as Map<String, dynamic>? ?? {};
          }
          if (stepsRes.data is Map<String, dynamic>) {
            _procedureSteps = (stepsRes.data as Map<String, dynamic>)['steps'] as List? ?? [];
          }
          if (policyRes.data is Map<String, dynamic>) {
            _policies = (policyRes.data as Map<String, dynamic>)['policies'] as List? ?? [];
          }
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _fetchPolicies() async {
    try {
      final client = ref.read(apiClientProvider);
      final policyRes = await client.get('/policy/admin/list');
      if (mounted && policyRes.data is Map<String, dynamic>) {
        setState(() {
          _policies = (policyRes.data as Map<String, dynamic>)['policies'] as List? ?? [];
        });
      }
    } catch (_) {}
  }

  Future<void> _fetchSteps() async {
    try {
      final client = ref.read(apiClientProvider);
      final stepsRes = await client.get('/procedures/$_selectedProcedureCode/steps');
      if (mounted && stepsRes.data is Map<String, dynamic>) {
        setState(() {
          _procedureSteps = (stepsRes.data as Map<String, dynamic>)['steps'] as List? ?? [];
        });
      }
    } catch (_) {}
  }

  Future<void> _toggleModule(String moduleId, bool enabled) async {
    setState(() {
      _modules[moduleId] = enabled;
    });

    try {
      final client = ref.read(apiClientProvider);
      await client.put(
        '/institution/modules',
        data: {'modules': _modules},
      );
      ref.invalidate(institutionModulesProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${enabled ? "Enabled" : "Disabled"} module: $moduleId'),
            duration: const Duration(seconds: 1),
            backgroundColor: enabled ? AppColors.successGreen : Colors.grey.shade700,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update module switchboard'), backgroundColor: AppColors.urgentRed),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.surface,
      appBar: AppBar(
        title: const Text('Institution Configurator'),
        elevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF00695C), Color(0xFF4DB6AC)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          isScrollable: true,
          tabs: const [
            Tab(icon: Icon(Icons.branding_watermark), text: 'Branding'),
            Tab(icon: Icon(Icons.linear_scale), text: 'Clearance Chain'),
            Tab(icon: Icon(Icons.account_balance_wallet), text: 'Refund Slabs'),
            Tab(icon: Icon(Icons.toggle_on_rounded), text: 'Switchboard'),
            Tab(icon: Icon(Icons.format_list_numbered_rounded), text: 'Procedure Steps'),
            Tab(icon: Icon(Icons.gavel_rounded), text: 'Policy Editor'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildBrandingTab(),
                _buildClearanceChainTab(),
                _buildRefundSlabsTab(),
                _buildModulesTab(),
                _buildProcedureStepsTab(),
                _buildPolicyEditorTab(),
              ],
            ),
    );
  }

  // ── Branding Tab ───────────────────────────────────────────────────────────
  Widget _buildBrandingTab() {
    final displayKeys = [
      'institution_name', 'institution_motto', 'crest_logo_url',
      'primary_color', 'secondary_color', 'contact_email',
      'contact_phone', 'website_url', 'address',
    ];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.school_rounded, color: AppColors.amityBlue, size: 28),
                  const SizedBox(width: 12),
                  Text(
                    _config['institution_name'] ?? 'University',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 22),
                  ),
                ],
              ),
              if (_config['institution_motto'] != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4, left: 40),
                  child: Text(
                    '"${_config['institution_motto']}"',
                    style: TextStyle(fontStyle: FontStyle.italic, color: Colors.grey.shade600),
                  ),
                ),
              const SizedBox(height: 24),
              ...displayKeys.map((key) => _buildConfigRow(key, _config[key]?.toString() ?? '—')),
              const SizedBox(height: 16),
              // Color preview
              Row(
                children: [
                  const Text('Theme Preview: ', style: TextStyle(fontWeight: FontWeight.w500)),
                  const SizedBox(width: 8),
                  Container(
                    width: 32, height: 32,
                    decoration: BoxDecoration(
                      color: _parseColor(_config['primary_color']),
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    width: 32, height: 32,
                    decoration: BoxDecoration(
                      color: _parseColor(_config['secondary_color']),
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return Colors.grey;
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (_) {
      return Colors.grey;
    }
  }

  Widget _buildConfigRow(String key, String value) {
    final label = key.replaceAll('_', ' ').split(' ').map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : w).join(' ');
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 160,
            child: Text('$label:', style: TextStyle(color: Colors.grey.shade600, fontWeight: FontWeight.w500)),
          ),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
        ],
      ),
    );
  }

  // ── Clearance Chain Tab ────────────────────────────────────────────────────
  Widget _buildClearanceChainTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.linear_scale, color: AppColors.amityBlue),
              const SizedBox(width: 8),
              const Text('Dynamic Clearance Desks', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const Spacer(),
              Text('${_clearanceChain.length} desks', style: TextStyle(color: Colors.grey.shade600)),
            ],
          ),
          const SizedBox(height: 16),
          ..._clearanceChain.asMap().entries.map((entry) {
            final idx = entry.key;
            final desk = entry.value;
            final isLast = idx == _clearanceChain.length - 1;
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Stepper indicator
                Column(
                  children: [
                    Container(
                      width: 36, height: 36,
                      decoration: const BoxDecoration(
                        color: AppColors.amityBlue,
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text('${idx + 1}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                      ),
                    ),
                    if (!isLast) Container(width: 2, height: 40, color: AppColors.amityBlue.withValues(alpha: 0.3)),
                  ],
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(desk['desk_code'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: (desk['is_active'] == 1 ? AppColors.successGreen : Colors.grey).withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  desk['is_active'] == 1 ? 'Active' : 'Inactive',
                                  style: TextStyle(color: desk['is_active'] == 1 ? AppColors.successGreen : Colors.grey, fontSize: 11),
                                ),
                              ),
                            ],
                          ),
                          Text(desk['desk_name'] ?? '', style: TextStyle(color: Colors.grey.shade700)),
                          if (desk['description'] != null && desk['description'].toString().isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(desk['description'], style: TextStyle(color: Colors.grey.shade500, fontSize: 12)),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            );
          }),
        ],
      ),
    );
  }

  // ── Refund Slabs Tab ───────────────────────────────────────────────────────
  Widget _buildRefundSlabsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Refund Day Slabs', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 16),
              Table(
                border: TableBorder.all(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(8)),
                columnWidths: const {
                  0: FlexColumnWidth(3),
                  1: FixedColumnWidth(80),
                  2: FixedColumnWidth(80),
                  3: FixedColumnWidth(90),
                  4: FlexColumnWidth(3),
                },
                children: [
                  TableRow(
                    decoration: BoxDecoration(color: AppColors.amityBlue.withValues(alpha: 0.1)),
                    children: const [
                      Padding(padding: EdgeInsets.all(10), child: Text('Slab', style: TextStyle(fontWeight: FontWeight.bold))),
                      Padding(padding: EdgeInsets.all(10), child: Text('From', style: TextStyle(fontWeight: FontWeight.bold))),
                      Padding(padding: EdgeInsets.all(10), child: Text('To', style: TextStyle(fontWeight: FontWeight.bold))),
                      Padding(padding: EdgeInsets.all(10), child: Text('Refund %', style: TextStyle(fontWeight: FontWeight.bold))),
                      Padding(padding: EdgeInsets.all(10), child: Text('Policy Note', style: TextStyle(fontWeight: FontWeight.bold))),
                    ],
                  ),
                  ..._refundSlabs.map((slab) {
                    final pct = (slab['refund_percent'] ?? 0).toDouble();
                    final color = pct >= 80 ? AppColors.successGreen : pct >= 25 ? Colors.amber.shade700 : AppColors.urgentRed;
                    return TableRow(
                      children: [
                        Padding(padding: const EdgeInsets.all(10), child: Text(slab['slab_label'] ?? '')),
                        Padding(padding: const EdgeInsets.all(10), child: Text('Day ${slab['min_days']}')),
                        Padding(padding: const EdgeInsets.all(10), child: Text('Day ${slab['max_days']}')),
                        Padding(
                          padding: const EdgeInsets.all(8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
                            child: Text('${pct.toStringAsFixed(0)}%',
                                style: TextStyle(color: color, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
                          ),
                        ),
                        Padding(padding: const EdgeInsets.all(10), child: Text(slab['policy_note'] ?? '', style: TextStyle(fontSize: 12, color: Colors.grey.shade600))),
                      ],
                    );
                  }),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Module Switchboard Tab ─────────────────────────────────────────────────
  Widget _buildModulesTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.toggle_on_rounded, color: Color(0xFF00695C), size: 28),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Dynamic Module Switchboard', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  Text(
                    'Toggle features and navigation tabs on or off for this institution',
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 18),
          ..._availableModules.map((m) {
            final modId = m['id']!;
            final isEnabled = _modules[modId] ?? true;

            IconData iconData;
            switch (m['icon']) {
              case 'dashboard':
                iconData = Icons.dashboard_rounded;
                break;
              case 'school':
                iconData = Icons.school_rounded;
                break;
              case 'exit_to_app':
                iconData = Icons.exit_to_app_rounded;
                break;
              case 'folder_shared':
                iconData = Icons.folder_shared_rounded;
                break;
              case 'support_agent':
                iconData = Icons.support_agent_rounded;
                break;
              case 'monetization_on':
                iconData = Icons.monetization_on_rounded;
                break;
              case 'apartment':
                iconData = Icons.apartment_rounded;
                break;
              case 'assignment':
                iconData = Icons.assignment_rounded;
                break;
              case 'record_voice_over':
                iconData = Icons.record_voice_over_rounded;
                break;
              default:
                iconData = Icons.verified_user_rounded;
            }

            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: SwitchListTile(
                value: isEnabled,
                activeThumbColor: const Color(0xFF00695C),
                secondary: Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: (isEnabled ? const Color(0xFF00695C) : Colors.grey).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(iconData, color: isEnabled ? const Color(0xFF00695C) : Colors.grey),
                ),
                title: Text(
                  m['title']!,
                  style: TextStyle(fontWeight: FontWeight.w600, color: isEnabled ? AppColors.ink : Colors.grey.shade600),
                ),
                subtitle: Text(
                  m['description']!,
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                ),
                onChanged: (val) => _toggleModule(modId, val),
              ),
            );
          }),
        ],
      ),
    );
  }

  // ── Procedure Steps Customizer Tab ────────────────────────────────────────
  Widget _buildProcedureStepsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.format_list_numbered_rounded, color: Color(0xFF00695C), size: 28),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Procedure Step Customizer', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  Text(
                    'Customize steps, SLA timelines, and responsible departments',
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                  ),
                ],
              ),
              const Spacer(),
              ElevatedButton.icon(
                onPressed: _showAddStepDialog,
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('Add Step'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00695C),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (_procedureSteps.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(40),
                child: Text('No steps configured for $_selectedProcedureCode.', style: TextStyle(color: Colors.grey.shade600)),
              ),
            )
          else
            ..._procedureSteps.map((s) {
              final stepNum = s['step_number'] ?? 0;
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          color: const Color(0xFF00695C).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Center(
                          child: Text(
                            '$stepNum',
                            style: const TextStyle(color: Color(0xFF00695C), fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    s['title'] ?? '',
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    s['timeline_text'] ?? '1-2 days',
                                    style: const TextStyle(color: Colors.blue, fontSize: 11, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Department: ${s['department'] ?? '—'}',
                              style: TextStyle(color: Colors.grey.shade700, fontSize: 12, fontWeight: FontWeight.w500),
                            ),
                            if (s['description'] != null && s['description'].toString().isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text(
                                s['description'].toString(),
                                style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                              ),
                            ],
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.edit_outlined, size: 20, color: Color(0xFF00695C)),
                        tooltip: 'Edit Step',
                        onPressed: () => _showEditStepDialog(s),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, size: 20, color: AppColors.urgentRed),
                        tooltip: 'Delete Step',
                        onPressed: () => _confirmDeleteStep(stepNum),
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  void _showAddStepDialog() {
    final titleCtrl = TextEditingController();
    final deptCtrl = TextEditingController(text: 'Department Desk');
    final timelineCtrl = TextEditingController(text: '1-2 days');
    final descCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Procedure Step', style: TextStyle(fontWeight: FontWeight.bold)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleCtrl,
                decoration: const InputDecoration(labelText: 'Step Title *', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: deptCtrl,
                decoration: const InputDecoration(labelText: 'Responsible Department *', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: timelineCtrl,
                decoration: const InputDecoration(labelText: 'Timeline SLA (e.g. 24 hours) *', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: descCtrl,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Description / Instructions', border: OutlineInputBorder()),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              if (titleCtrl.text.trim().isEmpty || deptCtrl.text.trim().isEmpty) return;
              Navigator.of(ctx).pop();
              try {
                final client = ref.read(apiClientProvider);
                await client.post(
                  '/procedures/$_selectedProcedureCode/steps',
                  data: {
                    'title': titleCtrl.text.trim(),
                    'department': deptCtrl.text.trim(),
                    'timeline_text': timelineCtrl.text.trim(),
                    'description': descCtrl.text.trim(),
                  },
                );
                await _fetchSteps();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Step added successfully'), backgroundColor: AppColors.successGreen),
                  );
                }
              } catch (_) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Failed to add step'), backgroundColor: AppColors.urgentRed),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00695C), foregroundColor: Colors.white),
            child: const Text('Add Step'),
          ),
        ],
      ),
    );
  }

  void _showEditStepDialog(Map<String, dynamic> step) {
    final stepNum = step['step_number'] ?? 1;
    final titleCtrl = TextEditingController(text: step['title'] ?? '');
    final deptCtrl = TextEditingController(text: step['department'] ?? '');
    final timelineCtrl = TextEditingController(text: step['timeline_text'] ?? '');
    final descCtrl = TextEditingController(text: step['description'] ?? '');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Edit Step $stepNum', style: const TextStyle(fontWeight: FontWeight.bold)),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleCtrl,
                decoration: const InputDecoration(labelText: 'Step Title', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: deptCtrl,
                decoration: const InputDecoration(labelText: 'Responsible Department', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: timelineCtrl,
                decoration: const InputDecoration(labelText: 'Timeline SLA', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: descCtrl,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(ctx).pop();
              try {
                final client = ref.read(apiClientProvider);
                await client.put(
                  '/procedures/$_selectedProcedureCode/steps/$stepNum',
                  data: {
                    'title': titleCtrl.text.trim(),
                    'department': deptCtrl.text.trim(),
                    'timeline_text': timelineCtrl.text.trim(),
                    'description': descCtrl.text.trim(),
                  },
                );
                await _fetchSteps();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Step updated successfully'), backgroundColor: AppColors.successGreen),
                  );
                }
              } catch (_) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Failed to update step'), backgroundColor: AppColors.urgentRed),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00695C), foregroundColor: Colors.white),
            child: const Text('Save Changes'),
          ),
        ],
      ),
    );
  }

  void _confirmDeleteStep(int stepNumber) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delete Step $stepNumber?'),
        content: const Text('This will delete the step and re-index all subsequent steps to maintain continuous numbering.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(ctx).pop();
              try {
                final client = ref.read(apiClientProvider);
                await client.delete('/procedures/$_selectedProcedureCode/steps/$stepNumber');
                await _fetchSteps();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Step $stepNumber deleted'), backgroundColor: AppColors.urgentRed),
                  );
                }
              } catch (_) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Failed to delete step'), backgroundColor: AppColors.urgentRed),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.urgentRed, foregroundColor: Colors.white),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  // ── Policy & Ordinance Editor Tab ─────────────────────────────────────────
  Widget _buildPolicyEditorTab() {
    final categories = ['All', 'Academic', 'Clearance & ID Card', 'Financial & Refunds', 'Hostels & Mess', 'Discipline & Conduct', 'Grievance & SLA'];

    final filtered = _policies.where((p) {
      if (_selectedPolicyCategory != 'All') {
        final cat = (p['category'] ?? '').toString().toLowerCase();
        if (!cat.contains(_selectedPolicyCategory.toLowerCase())) {
          return false;
        }
      }
      if (_policySearchQuery.trim().isNotEmpty) {
        final q = _policySearchQuery.trim().toLowerCase();
        final title = (p['title'] ?? '').toString().toLowerCase();
        final clause = (p['clause_code'] ?? '').toString().toLowerCase();
        final docId = (p['doc_id'] ?? '').toString().toLowerCase();
        final content = (p['content'] ?? '').toString().toLowerCase();
        return title.contains(q) || clause.contains(q) || docId.contains(q) || content.contains(q);
      }
      return true;
    }).toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF00695C).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.gavel_rounded, color: Color(0xFF00695C), size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'University Policy & Ordinance Editor',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Customize statutory ordinances, create university-specific clauses, and synchronize live with AI search & hybrid guidance.',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: () => _showEditPolicyDialog(),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('Add Policy'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00695C),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Search and Filters
          Row(
            children: [
              Expanded(
                child: TextField(
                  decoration: InputDecoration(
                    hintText: 'Search by title, clause code, or keyword (e.g. ORD-ACAD, refund, hostel)...',
                    prefixIcon: const Icon(Icons.search, size: 20),
                    suffixIcon: _policySearchQuery.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () => setState(() => _policySearchQuery = ''),
                          )
                        : null,
                    isDense: true,
                    filled: true,
                    fillColor: Colors.grey.shade50,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: Colors.grey.shade300)),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: Colors.grey.shade300)),
                  ),
                  onChanged: (val) => setState(() => _policySearchQuery = val),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Category Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: categories.map((cat) {
                final isSelected = _selectedPolicyCategory == cat;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(cat),
                    selected: isSelected,
                    onSelected: (_) => setState(() => _selectedPolicyCategory = cat),
                    selectedColor: const Color(0xFF00695C).withValues(alpha: 0.15),
                    checkmarkColor: const Color(0xFF00695C),
                    labelStyle: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      color: isSelected ? const Color(0xFF00695C) : Colors.grey.shade700,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                      side: BorderSide(color: isSelected ? const Color(0xFF00695C) : Colors.grey.shade300),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 18),

          // Policies Count Banner
          Row(
            children: [
              Text(
                'Showing ${filtered.length} of ${_policies.length} policies',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Colors.grey.shade700),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.bolt_rounded, size: 14, color: Colors.green.shade700),
                    const SizedBox(width: 4),
                    Text(
                      'AI Real-Time FTS5 Sync Active',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.green.shade800),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Policy Cards
          if (filtered.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(48),
                child: Column(
                  children: [
                    Icon(Icons.policy_outlined, size: 54, color: Colors.grey.shade400),
                    const SizedBox(height: 12),
                    Text('No matching policies found', style: TextStyle(color: Colors.grey.shade600, fontSize: 15)),
                  ],
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: filtered.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final p = filtered[index];
                final isCustom = p['is_custom'] == 1 || p['is_custom'] == true;
                final clauseCode = p['clause_code'] ?? 'ORD-00';
                final category = p['category'] ?? 'General';
                final title = p['title'] ?? 'Untitled Policy';
                final content = p['content'] ?? '';
                final docId = p['doc_id'] ?? '';
                final actionLabel = p['action_label'] ?? 'View Policy';

                return Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: BorderSide(
                      color: isCustom ? Colors.amber.shade300 : Colors.grey.shade200,
                      width: isCustom ? 1.5 : 1,
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Badges & Action Buttons
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: const Color(0xFF00695C).withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                clauseCode,
                                style: const TextStyle(
                                  color: Color(0xFF00695C),
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                  fontFamily: 'monospace',
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade100,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                category,
                                style: TextStyle(
                                  color: Colors.grey.shade700,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: isCustom ? Colors.amber.shade50 : Colors.blue.shade50,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: isCustom ? Colors.amber.shade400 : Colors.blue.shade200,
                                  width: 0.8,
                                ),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    isCustom ? Icons.edit_note_rounded : Icons.verified_rounded,
                                    size: 13,
                                    color: isCustom ? Colors.amber.shade900 : Colors.blue.shade700,
                                  ),
                                  const SizedBox(width: 4),
                                  Text(
                                    isCustom ? 'Customized' : 'Statutory Default',
                                    style: TextStyle(
                                      color: isCustom ? Colors.amber.shade900 : Colors.blue.shade700,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Spacer(),
                            IconButton(
                              icon: const Icon(Icons.edit_outlined, size: 20),
                              tooltip: 'Edit Ordinance',
                              color: const Color(0xFF00695C),
                              onPressed: () => _showEditPolicyDialog(p),
                            ),
                            IconButton(
                              icon: Icon(
                                isCustom ? Icons.restart_alt_rounded : Icons.delete_outline_rounded,
                                size: 20,
                              ),
                              tooltip: isCustom ? 'Reset to Default / Delete' : 'Statutory ordinance',
                              color: isCustom ? AppColors.urgentRed : Colors.grey.shade400,
                              onPressed: isCustom ? () => _confirmDeletePolicy(p) : null,
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),

                        // Title
                        Text(
                          title,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.ink),
                        ),
                        const SizedBox(height: 6),

                        // Content
                        Text(
                          content,
                          style: TextStyle(fontSize: 13, height: 1.4, color: Colors.grey.shade800),
                        ),
                        const SizedBox(height: 12),

                        // Footer Meta
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade50,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: Colors.grey.shade200),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.link_rounded, size: 14, color: Colors.grey.shade600),
                                  const SizedBox(width: 4),
                                  Text(
                                    actionLabel,
                                    style: TextStyle(fontSize: 11, color: Colors.grey.shade700, fontWeight: FontWeight.w600),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 10),
                            Text(
                              'ID: $docId',
                              style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: Colors.grey.shade400),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  void _showEditPolicyDialog([Map<String, dynamic>? policy]) {
    final isNew = policy == null;
    final docIdCtrl = TextEditingController(text: policy?['doc_id'] ?? '');
    final categoryCtrl = TextEditingController(text: policy?['category'] ?? 'Academic');
    final titleCtrl = TextEditingController(text: policy?['title'] ?? '');
    final clauseCtrl = TextEditingController(text: policy?['clause_code'] ?? 'ORD-');
    final contentCtrl = TextEditingController(text: policy?['content'] ?? '');
    final urlCtrl = TextEditingController(text: policy?['action_url'] ?? '/forms');
    final labelCtrl = TextEditingController(text: policy?['action_label'] ?? 'View Policy');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            Icon(isNew ? Icons.add_circle_outline : Icons.edit_note_rounded, color: const Color(0xFF00695C)),
            const SizedBox(width: 8),
            Text(isNew ? 'Add New Policy Ordinance' : 'Edit Policy Ordinance', style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        content: SizedBox(
          width: 580,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (isNew) ...[
                  TextField(
                    controller: docIdCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Policy Unique Identifier (doc_id) *',
                      hintText: 'e.g. ord_hostel_curfew_policy',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                ] else ...[
                  Text('Editing: ${policy['doc_id']}', style: TextStyle(color: Colors.grey.shade600, fontSize: 13, fontFamily: 'monospace')),
                  const SizedBox(height: 12),
                ],
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: TextField(
                        controller: clauseCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Clause Code *',
                          hintText: 'e.g. ORD-HST-3.2',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 4,
                      child: TextField(
                        controller: categoryCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Category *',
                          hintText: 'Academic, Hostels, etc.',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: titleCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Policy Title *',
                    hintText: 'e.g. Student Medical Leave & Attendance Regularization',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: contentCtrl,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: 'Statutory Clause Text / Content *',
                    hintText: 'Enter full policy ordinance text with attendance percentages, SLA rules, fees, etc.',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: urlCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Action URL',
                          hintText: '/forms, /grievance, etc.',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: labelCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Action Button Label',
                          hintText: 'View Policy / Download Form',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final docId = (isNew ? docIdCtrl.text : (policy['doc_id'] ?? '')).trim();
              final category = categoryCtrl.text.trim();
              final title = titleCtrl.text.trim();
              final clause = clauseCtrl.text.trim();
              final content = contentCtrl.text.trim();

              if (docId.isEmpty || title.isEmpty || clause.isEmpty || content.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Please fill all required fields (*)'), backgroundColor: AppColors.urgentRed),
                );
                return;
              }

              Navigator.of(ctx).pop();
              try {
                final client = ref.read(apiClientProvider);
                await client.post(
                  '/policy/admin/save',
                  data: {
                    'doc_id': docId,
                    'category': category.isEmpty ? 'General' : category,
                    'title': title,
                    'clause_code': clause,
                    'content': content,
                    'action_url': urlCtrl.text.trim().isEmpty ? '/forms' : urlCtrl.text.trim(),
                    'action_label': labelCtrl.text.trim().isEmpty ? 'View Policy' : labelCtrl.text.trim(),
                  },
                );
                await _fetchPolicies();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Policy "$title" saved & indexed into AI search!'),
                      backgroundColor: AppColors.successGreen,
                    ),
                  );
                }
              } catch (_) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Failed to save policy ordinance'), backgroundColor: AppColors.urgentRed),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00695C), foregroundColor: Colors.white),
            child: const Text('Save & Index in AI'),
          ),
        ],
      ),
    );
  }

  void _confirmDeletePolicy(Map<String, dynamic> policy) {
    final docId = policy['doc_id'] ?? '';
    final title = policy['title'] ?? 'Policy';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reset or Delete Policy?'),
        content: Text('Are you sure you want to revert or delete "$title" ($docId)?\n\nIf this was a customized default ordinance, it will be restored to its statutory seed. The AI search engine will immediately update its knowledge index.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(ctx).pop();
              try {
                final client = ref.read(apiClientProvider);
                await client.delete('/policy/admin/$docId');
                await _fetchPolicies();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Policy "$docId" reset/deleted successfully'), backgroundColor: AppColors.urgentRed),
                  );
                }
              } catch (_) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Failed to delete policy'), backgroundColor: AppColors.urgentRed),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.urgentRed, foregroundColor: Colors.white),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }
}

