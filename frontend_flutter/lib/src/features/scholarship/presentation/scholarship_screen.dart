import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../core/api_client.dart';
import '../../../core/services/offline_cache_service.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../auth/application/auth_provider.dart';

/// Fetch scholarships from the API.
final scholarshipsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  final studentId = ref.watch(authProvider).studentId;
  final cache = ref.watch(offlineCacheProvider);

  if (studentId == null) return [];

  try {
    final response = await dio.get('/student/scholarships', queryParameters: {
      'student_id': studentId,
    });

    final data = (response.data as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();

    await cache.put('scholarships_$studentId', response.data);
    return data;
  } catch (e) {
    final cached = cache.get('scholarships_$studentId');
    if (cached != null) {
      return (cached as List).map((e) => Map<String, dynamic>.from(e)).toList();
    }
    return [];
  }
});

class ScholarshipScreen extends ConsumerWidget {
  const ScholarshipScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scholarshipsAsync = ref.watch(scholarshipsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Scholarship Hub')),
      body: scholarshipsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error: $err')),
        data: (scholarships) {
          if (scholarships.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.workspace_premium_outlined, size: 64, color: Colors.grey.shade400),
                  const SizedBox(height: 16),
                  Text('No scholarships available', style: Theme.of(context).textTheme.titleMedium),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(scholarshipsProvider),
            child: ListView.builder(
              itemCount: scholarships.length,
              padding: const EdgeInsets.all(16),
              itemBuilder: (context, index) {
                final s = scholarships[index];
                return _ScholarshipCard(scholarship: s)
                    .animate()
                    .fadeIn(
                      delay: Duration(milliseconds: 80 * index),
                      duration: 350.ms,
                    )
                    .slideY(begin: 0.08);
              },
            ),
          );
        },
      ),
    );
  }
}

class _ScholarshipCard extends ConsumerStatefulWidget {
  const _ScholarshipCard({required this.scholarship});
  final Map<String, dynamic> scholarship;

  @override
  ConsumerState<_ScholarshipCard> createState() => _ScholarshipCardState();
}

class _ScholarshipCardState extends ConsumerState<_ScholarshipCard> {
  bool _isApplying = false;
  String? _applyResult;

  Future<void> _apply() async {
    setState(() {
      _isApplying = true;
      _applyResult = null;
    });

    try {
      final dio = ref.read(apiClientProvider);
      final studentId = ref.read(authProvider).studentId;
      final scholarshipId = widget.scholarship['id'] is int
          ? widget.scholarship['id'] as int
          : int.tryParse(widget.scholarship['id']?.toString() ?? '1') ?? 1;
      await dio.post('/student/scholarships/apply', data: {
        'student_id': studentId,
        'scholarship_id': scholarshipId,
      });

      setState(() {
        _applyResult = 'Applied successfully!';
      });
      ref.invalidate(scholarshipsProvider);
    } on DioException catch (e) {
      setState(() {
        _applyResult = e.response?.data?['detail']?.toString() ?? 'Application failed.';
      });
    } catch (e) {
      setState(() {
        _applyResult = 'An error occurred.';
      });
    } finally {
      setState(() => _isApplying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.scholarship;
    final title = s['scheme_name'] ?? s['name'] ?? 'Scholarship';
    final description = s['description'] ?? '';
    final amount = s['amount']?.toString() ?? '';
    final cgpaReq = s['min_cgpa']?.toString() ?? '';
    final isEligible = s['eligible'] ?? true;
    final alreadyApplied = s['applied'] ?? false;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.amityYellow.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.workspace_premium_rounded, color: Color(0xFFF9A825), size: 28),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(title, style: Theme.of(context).textTheme.titleLarge),
                ),
              ],
            ),
            if (description.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(description, style: Theme.of(context).textTheme.bodyMedium),
            ],
            const Divider(height: 24),
            Row(
              children: [
                if (cgpaReq.isNotEmpty)
                  Chip(
                    avatar: const Icon(Icons.trending_up, size: 16),
                    label: Text('CGPA ≥ $cgpaReq'),
                  ),
                const SizedBox(width: 8),
                if (amount.isNotEmpty)
                  Chip(
                    avatar: const Icon(Icons.currency_rupee, size: 16),
                    label: Text(amount),
                    backgroundColor: AppColors.successGreen.withValues(alpha: 0.12),
                  ),
                const Spacer(),
                if (isEligible && !alreadyApplied)
                  const Chip(
                    label: Text('Eligible', style: TextStyle(color: Colors.white, fontSize: 12)),
                    backgroundColor: AppColors.successGreen,
                  ),
                if (alreadyApplied)
                  const Chip(
                    label: Text('Applied', style: TextStyle(color: Colors.white, fontSize: 12)),
                    backgroundColor: AppColors.amityBlue,
                  ),
              ],
            ),
            if (_applyResult != null) ...[
              const SizedBox(height: 12),
              Text(
                _applyResult!,
                style: TextStyle(
                  color: _applyResult!.contains('success') ? AppColors.successGreen : AppColors.urgentRed,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            if (!alreadyApplied && isEligible) ...[
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _isApplying ? null : _apply,
                  icon: _isApplying
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.send_rounded),
                  label: Text(_isApplying ? 'Applying...' : 'Apply Now'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
