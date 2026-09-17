import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';

// Admin Stats
final adminStatsProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final response = await dio.get('/admin/stats');
    final data = response.data as Map<String, dynamic>;
    return {
      ...data,
      'active_grievances': data['active_grievances'] ?? data['open_grievances'] ?? 0,
      'pending_documents': data['pending_documents'] ?? data['documents_pending_verification'] ?? 0,
      'recent_activity': data['recent_activity'] ?? [],
    };
  } catch (e) {
    // Offline Mock Fallback
    return {
      'pending_withdrawals': 12,
      'active_grievances': 5,
      'pending_documents': 28,
      'recent_activity': [
        {'time': '10:00 AM', 'action': 'Withdrawal Approved'},
        {'time': '09:15 AM', 'action': 'Grievance Forwarded'},
      ]
    };
  }
});

// Admin Requests (Withdrawals)
final adminRequestsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final response = await dio.get('/admin/requests');
    return (response.data as List)
        .map((item) => _normaliseWithdrawal(item as Map<String, dynamic>))
        .toList();
  } catch (e) {
    // Offline Mock Fallback
    return [
      {
        'id': 101,
        'student_id': 'STU001',
        'type': 'WITHDRAWAL',
        'status': 'PENDING',
        'reason': 'Financial Hardship',
        'date': '2026-08-20',
      },
      {
        'id': 102,
        'student_id': 'STU045',
        'type': 'WITHDRAWAL',
        'status': 'APPROVED',
        'reason': 'Medical Reasons',
        'date': '2026-08-19',
      },
      {
        'id': 103,
        'student_id': 'STU088',
        'type': 'WITHDRAWAL',
        'status': 'PENDING',
        'reason': 'Personal',
        'date': '2026-08-20',
      },
    ];
  }
});

// Admin Grievances
final adminGrievancesProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final response = await dio.get('/admin/grievances');
    return (response.data as List)
        .map((item) => _normaliseGrievance(item as Map<String, dynamic>))
        .toList();
  } catch (e) {
    // Offline Mock Fallback
    return [
      {
        'id': 201,
        'student_id': 'STU012',
        'category': 'Hostel',
        'priority': 'HIGH',
        'subject': 'No hot water in Block B',
        'status': 'OPEN',
        'date': '2026-08-19',
      },
      {
        'id': 202,
        'student_id': 'STU099',
        'category': 'Academics',
        'priority': 'MEDIUM',
        'subject': 'Missing grade for CSE101',
        'status': 'IN_PROGRESS',
        'date': '2026-08-18',
      },
    ];
  }
});

// Admin Documents
final adminDocumentsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final dio = ref.watch(apiClientProvider);
  try {
    final response = await dio.get('/admin/documents');
    return (response.data as List)
        .map((item) => _normaliseDocument(item as Map<String, dynamic>))
        .toList();
  } catch (e) {
    // Offline Mock Fallback
    return [
      {
        'id': 301,
        'student_id': 'STU001',
        'document_type': 'Fee Receipt',
        'status': 'PENDING',
        'ocr_confidence': 0.98,
        'fraud_flags': [],
        'upload_date': '2026-08-20',
      },
      {
        'id': 302,
        'student_id': 'STU045',
        'document_type': 'Medical Certificate',
        'status': 'PENDING',
        'ocr_confidence': 0.65,
        'fraud_flags': ['Mismatched Dates', 'Blurry Signature'],
        'upload_date': '2026-08-20',
      },
    ];
  }
});

// Actions
final staffActionsProvider = Provider<StaffActions>((ref) {
  return StaffActions(ref.watch(apiClientProvider), ref);
});

class StaffActions {
  final Dio _dio;
  final Ref _ref;

  StaffActions(this._dio, this._ref);

  Future<void> updateRequestStatus(int id, String status) async {
    try {
      await _dio.post('/admin/requests/$id/status', data: {
        'status': status.toLowerCase(),
      });
    } catch (_) {
      // Mock success for offline
      await Future.delayed(const Duration(milliseconds: 500));
    }
    _ref.invalidate(adminRequestsProvider);
    _ref.invalidate(adminStatsProvider);
  }

  Future<void> batchApproveRequests(List<int> ids) async {
    for (final id in ids) {
      await updateRequestStatus(id, 'approved');
    }
  }

  Future<void> resolveGrievance(int id, String resolution) async {
    try {
      await _dio.post('/admin/grievances/$id/resolve', data: {'resolution': resolution});
    } catch (_) {
      // Mock success for offline
      await Future.delayed(const Duration(milliseconds: 500));
    }
    _ref.invalidate(adminGrievancesProvider);
    _ref.invalidate(adminStatsProvider);
  }

  Future<void> verifyDocument(int id, String status, String notes) async {
    try {
      await _dio.post('/admin/documents/$id/verify', data: {
        'status': status.toLowerCase(),
        'notes': notes
      });
    } catch (_) {
      // Mock success for offline
      await Future.delayed(const Duration(milliseconds: 500));
    }
    _ref.invalidate(adminDocumentsProvider);
  }

  Future<void> batchVerifyDocuments(List<int> ids) async {
    for (final id in ids) {
      await verifyDocument(id, 'verified', 'Batch verified');
    }
  }

  Future<void> clearDepartmentGate({
    required String referenceNo,
    required String department,
    required String action,
    double duesAmount = 0.0,
    String? officerName,
    String? notes,
  }) async {
    try {
      await _dio.post('/withdrawal/$referenceNo/clear/$department', data: {
        'action': action,
        'dues_amount': duesAmount,
        'officer_name': officerName ?? 'Department Officer',
        'notes': notes,
      });
    } catch (_) {
      await Future.delayed(const Duration(milliseconds: 500));
    }
    _ref.invalidate(adminRequestsProvider);
    _ref.invalidate(adminStatsProvider);
  }

  Future<void> offsetDepartmentDues({
    required String referenceNo,
    required String department,
    required double amount,
    required String reason,
    String? authorizedBy,
  }) async {
    try {
      await _dio.post('/withdrawal/$referenceNo/offset-dues', data: {
        'department': department,
        'amount': amount,
        'reason': reason,
        'student_consent': true,
        'authorized_by': authorizedBy ?? 'Finance Officer',
      });
    } catch (_) {
      await Future.delayed(const Duration(milliseconds: 500));
    }
    _ref.invalidate(adminRequestsProvider);
    _ref.invalidate(adminStatsProvider);
  }
}

Map<String, dynamic> _normaliseWithdrawal(Map<String, dynamic> item) {
  final status = (item['status'] ?? 'pending').toString().toUpperCase();
  return {
    ...item,
    'status': status,
    'name': item['name'] ?? item['student_name'] ?? '',
    'date': _datePart(item['timestamp'] ?? item['date']),
    'reason': item['reason'] ?? 'Not recorded',
  };
}

Map<String, dynamic> _normaliseGrievance(Map<String, dynamic> item) {
  final category = _titleCase(item['category'] ?? 'general');
  final status = (item['status'] ?? 'open').toString().toUpperCase();
  return {
    ...item,
    'category': category,
    'status': status,
    'priority': item['priority'] ?? _priorityForCategory(category),
    'subject': item['subject'] ?? item['description'] ?? 'Student grievance',
    'date': _datePart(item['timestamp'] ?? item['date']),
  };
}

Map<String, dynamic> _normaliseDocument(Map<String, dynamic> item) {
  final ocr = item['ocr_data'] is Map<String, dynamic>
      ? item['ocr_data'] as Map<String, dynamic>
      : <String, dynamic>{};
  final notes = (item['verification_notes'] ?? '').toString();
  final verificationStatus = (item['verification_status'] ?? item['status'] ?? 'pending')
      .toString()
      .toUpperCase();
  final flags = verificationStatus == 'FRAUD_DETECTED' && notes.isNotEmpty
      ? notes.split(';').map((flag) => flag.trim()).where((flag) => flag.isNotEmpty).toList()
      : <String>[];

  return {
    ...item,
    'document_type': item['document_type'] ?? item['classification'] ?? ocr['document_type'] ?? 'Document',
    'status': verificationStatus,
    'ocr_confidence': (ocr['confidence_score'] is num)
        ? (ocr['confidence_score'] as num).toDouble()
        : 0.0,
    'fraud_flags': item['fraud_flags'] ?? flags,
    'upload_date': _datePart(item['timestamp'] ?? item['upload_date']),
  };
}

String _datePart(dynamic value) {
  if (value == null) return '--';
  return value.toString().split(' ').first;
}

String _titleCase(dynamic value) {
  final text = value.toString();
  if (text.isEmpty) return text;
  return text[0].toUpperCase() + text.substring(1).toLowerCase();
}

String _priorityForCategory(String category) {
  switch (category.toLowerCase()) {
    case 'fee':
    case 'hostel':
      return 'HIGH';
    case 'exam':
    case 'academic':
      return 'MEDIUM';
    default:
      return 'LOW';
  }
}
