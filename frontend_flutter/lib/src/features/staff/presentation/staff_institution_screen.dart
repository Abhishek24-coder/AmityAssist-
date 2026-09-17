import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/kiosk_theme.dart';

/// Phase 28: Staff Institution Configurator.
/// Admin Settings screen for university branding, dynamic clearance chain
/// management, and custom refund slab editing.
class StaffInstitutionScreen extends StatefulWidget {
  const StaffInstitutionScreen({super.key});

  @override
  State<StaffInstitutionScreen> createState() => _StaffInstitutionScreenState();
}

class _StaffInstitutionScreenState extends State<StaffInstitutionScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;
  Map<String, dynamic> _config = {};
  List<dynamic> _clearanceChain = [];
  List<dynamic> _refundSlabs = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
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
      final configRes = await http.get(Uri.parse('http://127.0.0.1:8000/api/institution/config'));
      final chainRes = await http.get(Uri.parse('http://127.0.0.1:8000/api/institution/clearance-chain'));
      final slabRes = await http.get(Uri.parse('http://127.0.0.1:8000/api/institution/refund-slabs'));

      if (configRes.statusCode == 200) _config = jsonDecode(configRes.body);
      if (chainRes.statusCode == 200) _clearanceChain = jsonDecode(chainRes.body)['chain'] ?? [];
      if (slabRes.statusCode == 200) _refundSlabs = jsonDecode(slabRes.body)['slabs'] ?? [];

      setState(() => _isLoading = false);
    } catch (_) {
      setState(() => _isLoading = false);
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
          tabs: const [
            Tab(icon: Icon(Icons.branding_watermark), text: 'Branding'),
            Tab(icon: Icon(Icons.linear_scale), text: 'Clearance Chain'),
            Tab(icon: Icon(Icons.account_balance_wallet), text: 'Refund Slabs'),
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
                      decoration: BoxDecoration(
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
}
