import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../../core/utils/download_service.dart';
import '../../../core/widgets/uniassist_logo.dart';
import '../../kiosk/presentation/assistant_fab.dart';

class GuestServicesScreen extends StatelessWidget {
  const GuestServicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 800;

    return Scaffold(
      floatingActionButton: const AssistantFab(),
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: const BoxDecoration(
                color: AppColors.panel,
                border: Border(bottom: BorderSide(color: AppColors.line)),
              ),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_rounded, size: 28),
                    onPressed: () => context.go('/'),
                  ),
                  const SizedBox(width: 16),
                  const UniAssistLogo(size: 34, showWordmark: true),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.tealSoft,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'PUBLIC SERVICES',
                      style: TextStyle(
                        color: AppColors.teal,
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Grid Content
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1000),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Public Services',
                          style: TextStyle(
                            fontSize: isCompact ? 28 : 36,
                            fontWeight: FontWeight.w900,
                            color: AppColors.ink,
                          ),
                        ).animate().fadeIn().slideX(begin: -0.1),
                        const SizedBox(height: 8),
                        const Text(
                          'Select a category to find information, download forms, or track your live clearance token.',
                          style: TextStyle(fontSize: 16, color: AppColors.muted, fontWeight: FontWeight.w500),
                        ).animate(delay: 100.ms).fadeIn(),
                        const SizedBox(height: 24),

                        // Remote Token Tracking Handshake Banner (Phase 26)
                        _PublicTokenTrackingBanner(),
                        const SizedBox(height: 32),

                        GridView.count(
                          crossAxisCount: isCompact ? 2 : 4,
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          mainAxisSpacing: 24,
                          crossAxisSpacing: 24,
                          childAspectRatio: 1.1,
                          children: [
                            _CategoryCard(
                              title: 'Procedures',
                              icon: Icons.account_tree_outlined,
                              color: AppColors.primary,
                              delay: 200,
                              route: '/withdrawal',
                            ),
                            _CategoryCard(
                              title: 'Forms',
                              icon: Icons.description_outlined,
                              color: AppColors.teal,
                              delay: 250,
                              route: '/forms',
                            ),
                            _CategoryCard(
                              title: 'Documents',
                              icon: Icons.folder_open_rounded,
                              color: AppColors.gold,
                              delay: 300,
                              route: '/login', // Requires login
                            ),
                            _CategoryCard(
                              title: 'Notices',
                              icon: Icons.campaign_outlined,
                              color: AppColors.danger,
                              delay: 350,
                              route: '/notices',
                            ),
                            _CategoryCard(
                              title: 'FAQs',
                              icon: Icons.help_outline_rounded,
                              color: AppColors.primary,
                              delay: 400,
                              route: '/chat',
                            ),
                            _CategoryCard(
                              title: 'Scholarships',
                              icon: Icons.school_outlined,
                              color: AppColors.teal,
                              delay: 450,
                              route: '/scholarship',
                            ),
                            _CategoryCard(
                              title: 'Certificates',
                              icon: Icons.verified_outlined,
                              color: AppColors.gold,
                              delay: 500,
                              route: '/forms',
                            ),
                            _CategoryCard(
                              title: 'Hostel Services',
                              icon: Icons.apartment_rounded,
                              color: AppColors.danger,
                              delay: 550,
                              route: '/login',
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CategoryCard extends StatelessWidget {
  const _CategoryCard({
    required this.title,
    required this.icon,
    required this.color,
    required this.delay,
    required this.route,
  });

  final String title;
  final IconData icon;
  final Color color;
  final int delay;
  final String route;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        if (route == '/login') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Please login to access $title.')),
          );
        }
        context.push(route);
      },
      borderRadius: BorderRadius.circular(16),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.line),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 36, color: color),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.ink,
              ),
            ),
          ],
        ),
      ).animate(delay: delay.ms).fadeIn().scale(begin: const Offset(0.9, 0.9)),
    );
  }
}

class _PublicTokenTrackingBanner extends StatefulWidget {
  const _PublicTokenTrackingBanner();

  @override
  State<_PublicTokenTrackingBanner> createState() => _PublicTokenTrackingBannerState();
}

class _PublicTokenTrackingBannerState extends State<_PublicTokenTrackingBanner> {
  final _refController = TextEditingController();

  @override
  void dispose() {
    _refController.dispose();
    super.dispose();
  }

  void _onTrack() {
    final ref = _refController.text.trim();
    if (ref.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your Reference Number (e.g. AMITY-WTH-2026-0001)')),
      );
      return;
    }
    showDialog(
      context: context,
      builder: (ctx) => _TokenTrackingResultDialog(referenceNo: ref),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.amityBlue,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: AppColors.amityBlue.withValues(alpha: 0.25),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.travel_explore_rounded, color: Colors.white, size: 24),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Live Token Tracking (Overseas & Remote Handshake)',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Track 4-gate clearance progress or reprint your official token slip anywhere without logging in.',
                      style: TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _refController,
                  style: const TextStyle(color: Colors.black87, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Enter Reference (e.g. AMITY-WTH-2026-0001)',
                    hintStyle: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    filled: true,
                    fillColor: Colors.white,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  onSubmitted: (_) => _onTrack(),
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: _onTrack,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.amityYellow,
                  foregroundColor: Colors.black87,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(Icons.search_rounded, size: 18),
                label: const Text('Track Token', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    ).animate().fadeIn().slideY(begin: 0.05);
  }
}

class _TokenTrackingResultDialog extends StatefulWidget {
  const _TokenTrackingResultDialog({required this.referenceNo});
  final String referenceNo;

  @override
  State<_TokenTrackingResultDialog> createState() => _TokenTrackingResultDialogState();
}

class _TokenTrackingResultDialogState extends State<_TokenTrackingResultDialog> {
  bool _isLoading = true;
  String? _error;
  Map<String, dynamic>? _data;

  @override
  void initState() {
    super.initState();
    _fetchStatus();
  }

  Future<void> _fetchStatus() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final dio = Dio(BaseOptions(
        baseUrl: 'http://127.0.0.1:8000/api',
        connectTimeout: const Duration(seconds: 8),
      ));
      final resp = await dio.get('/withdrawal/track/${widget.referenceNo.trim()}');
      if (mounted) {
        setState(() {
          _data = Map<String, dynamic>.from(resp.data as Map);
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Unable to find tracking record for "${widget.referenceNo}". Please verify your reference number.';
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 540),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: _isLoading
              ? const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Fetching live token clearance status...'),
                  ],
                )
              : _error != null
                  ? Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline_rounded, color: Colors.redAccent, size: 48),
                        const SizedBox(height: 12),
                        const Text('Token Not Found', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
                        const SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('Close'),
                        ),
                      ],
                    )
                  : _buildDetails(context),
        ),
      ),
    );
  }

  Widget _buildDetails(BuildContext context) {
    final d = _data!;
    final ref = d['reference_no'] ?? widget.referenceNo;
    final maskedName = d['student_name_masked'] ?? 'Student';
    final program = d['program'] ?? 'Academic Program';
    final status = d['current_status'] ?? 'PENDING';
    final progress = d['clearance_progress'] ?? '';
    final gates = (d['gates'] as List? ?? []);
    final voucher = d['voucher'] is Map ? Map<String, dynamic>.from(d['voucher'] as Map) : null;

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.qr_code_2_rounded, color: AppColors.amityBlue, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(ref.toString(), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    Text('$maskedName • $program', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.amityBlue.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  status.toString(),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.amityBlue),
                ),
              ),
            ],
          ),
          const Divider(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('4-Gate Clearance Pipeline', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              Text(progress.toString(), style: const TextStyle(color: AppColors.successGreen, fontWeight: FontWeight.bold, fontSize: 12)),
            ],
          ),
          const SizedBox(height: 12),
          ...gates.map((g) {
            final gate = g is Map ? Map<String, dynamic>.from(g) : <String, dynamic>{};
            final dept = gate['department']?.toString().toUpperCase() ?? '';
            final gStatus = gate['status']?.toString().toUpperCase() ?? 'PENDING';
            final dues = (gate['dues_amount'] as num?)?.toDouble() ?? 0.0;
            final isCleared = gStatus == 'CLEARED';
            final isFlagged = gStatus == 'FLAG_DUES';

            return Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: isCleared
                    ? AppColors.successGreen.withValues(alpha: 0.06)
                    : (isFlagged ? Colors.orange.withValues(alpha: 0.08) : Colors.grey.withValues(alpha: 0.06)),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isCleared
                      ? AppColors.successGreen.withValues(alpha: 0.3)
                      : (isFlagged ? Colors.orange.withValues(alpha: 0.3) : Colors.grey.shade300),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    isCleared
                        ? Icons.check_circle_rounded
                        : (isFlagged ? Icons.warning_amber_rounded : Icons.pending_outlined),
                    size: 16,
                    color: isCleared ? AppColors.successGreen : (isFlagged ? Colors.orange : Colors.grey),
                  ),
                  const SizedBox(width: 8),
                  Text(dept, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                  const Spacer(),
                  if (dues > 0)
                    Text('Dues: ₹${dues.toStringAsFixed(0)}  ', style: const TextStyle(fontSize: 11, color: Colors.redAccent, fontWeight: FontWeight.bold)),
                  Text(
                    gStatus,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: isCleared ? AppColors.successGreen : (isFlagged ? Colors.orange : Colors.grey),
                    ),
                  ),
                ],
              ),
            );
          }),
          if (voucher != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Refund Estimate:', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  Text(
                    '₹${((voucher['net_refundable_amount'] as num?)?.toDouble() ?? 0.0).toStringAsFixed(2)}',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.successGreen),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    DownloadService.downloadFile(
                      'http://127.0.0.1:8000/api/withdrawal/$ref/slip',
                      fileName: 'TOKEN-$ref.pdf',
                    );
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Downloading Token Slip PDF for $ref...')),
                    );
                  },
                  icon: const Icon(Icons.download_rounded, size: 16),
                  label: const Text('Download Slip PDF', style: TextStyle(fontSize: 12)),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Done'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
