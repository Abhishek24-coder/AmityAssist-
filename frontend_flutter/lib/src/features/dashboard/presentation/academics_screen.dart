import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../core/api_client.dart';
import '../../../core/services/offline_cache_service.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../auth/application/auth_provider.dart';

final academicsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final studentId = ref.watch(authProvider).studentId;
  if (studentId == null) throw Exception('Not logged in');

  final dio = ref.watch(apiClientProvider);
  final cache = ref.watch(offlineCacheProvider);

  try {
    final response = await dio.get('/student/exams', queryParameters: {
      'student_id': studentId,
    });

    final data = (response.data as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();

    await cache.put('exams_$studentId', response.data);
    return data;
  } catch (e) {
    final cached = cache.get('exams_$studentId');
    if (cached != null) {
      return (cached as List).map((e) => Map<String, dynamic>.from(e)).toList();
    }
    rethrow;
  }
});

class AcademicsScreen extends ConsumerWidget {
  const AcademicsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final academicsAsync = ref.watch(academicsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Academics & Exams')),
      body: academicsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, st) => Center(child: Text('Error: $err')),
        data: (exams) {
          if (exams.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.school_outlined, size: 64, color: Colors.grey.shade400),
                  const SizedBox(height: 16),
                  Text('No academic records found.', style: Theme.of(context).textTheme.titleMedium),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(academicsProvider),
            child: ListView.builder(
              itemCount: exams.length,
              padding: const EdgeInsets.all(16),
              itemBuilder: (context, index) {
                final exam = exams[index];
                return _ExamCard(exam: exam)
                    .animate()
                    .fadeIn(
                      delay: Duration(milliseconds: 50 * index),
                      duration: 300.ms,
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

class _ExamCard extends ConsumerStatefulWidget {
  const _ExamCard({required this.exam});
  final Map<String, dynamic> exam;

  @override
  ConsumerState<_ExamCard> createState() => _ExamCardState();
}

class _ExamCardState extends ConsumerState<_ExamCard> {
  bool _isRegistering = false;

  Color _gradeColor(String? grade) {
    switch (grade) {
      case 'A+' || 'A':
        return AppColors.successGreen;
      case 'B+' || 'B':
        return AppColors.amityBlue;
      case 'C+' || 'C':
        return const Color(0xFFF9A825);
      case 'D' || 'F':
        return AppColors.urgentRed;
      default:
        return Colors.grey;
    }
  }

  IconData _gradeIcon(String? grade) {
    switch (grade) {
      case 'A+' || 'A':
        return Icons.workspace_premium_rounded;
      case 'B+' || 'B':
        return Icons.thumb_up_rounded;
      case 'C+' || 'C':
        return Icons.info_outline_rounded;
      case 'D' || 'F':
        return Icons.warning_amber_rounded;
      default:
        return Icons.pending_outlined;
    }
  }

  Future<void> _registerBackpaper() async {
    setState(() => _isRegistering = true);

    try {
      final dio = ref.read(apiClientProvider);
      final studentId = ref.read(authProvider).studentId;
      final examId = widget.exam['id'] is int
          ? widget.exam['id'] as int
          : int.tryParse(widget.exam['id']?.toString() ?? '1') ?? 1;
      await dio.post('/student/backpaper', data: {
        'student_id': studentId,
        'exam_id': examId,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Backpaper registered for ${widget.exam['course_name'] ?? 'course'}'),
            backgroundColor: AppColors.successGreen,
          ),
        );
        ref.invalidate(academicsProvider);
      }
    } on DioException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.response?.data?['detail'] ?? e.message}')),
        );
      }
    } finally {
      if (mounted) setState(() => _isRegistering = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final exam = widget.exam;
    final grade = exam['grade'] as String?;
    final courseName = exam['course_name'] ?? 'Unknown Course';
    final examDate = exam['exam_date'] ?? 'TBA';
    final hasFailed = grade == 'F' || grade == 'D';
    final color = _gradeColor(grade);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: hasFailed
            ? BorderSide(color: AppColors.urgentRed.withValues(alpha: 0.3), width: 1.5)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(_gradeIcon(grade), color: color, size: 26),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        courseName,
                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Exam: $examDate',
                        style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                ),
                // Grade badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    grade ?? '—',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: color,
                    ),
                  ),
                ),
              ],
            ),
            // Backpaper registration for failed subjects
            if (hasFailed) ...[
              const SizedBox(height: 14),
              OutlinedButton.icon(
                onPressed: _isRegistering ? null : _registerBackpaper,
                icon: _isRegistering
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.app_registration_rounded, size: 20),
                label: Text(_isRegistering ? 'Registering...' : 'Register Backpaper'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.urgentRed,
                  side: BorderSide(color: AppColors.urgentRed.withValues(alpha: 0.5)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
