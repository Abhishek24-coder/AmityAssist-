import 'package:dio/dio.dart';
import '../domain/withdrawal_models.dart';

class WithdrawalRepository {
  WithdrawalRepository(this._dio);

  final Dio _dio;

  Future<WithdrawalGuide> fetchGuide() async {
    final response = await _dio.get<Map<String, dynamic>>('/withdrawal/guide');
    return WithdrawalGuide.fromJson(response.data ?? {});
  }

  Future<ClearanceVoucher> fetchClearanceVoucher(String referenceNo) async {
    final response = await _dio.get<Map<String, dynamic>>('/withdrawal/voucher/$referenceNo');
    return ClearanceVoucher.fromJson(response.data ?? {});
  }

  Future<Map<String, dynamic>> submitDepartmentClearance({
    required String referenceNo,
    required String department,
    required String action,
    double duesAmount = 0.0,
    String? officerName,
    String? notes,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/withdrawal/$referenceNo/clear/$department',
      data: {
        'action': action,
        'dues_amount': duesAmount,
        'officer_name': officerName ?? 'Department Officer',
        'notes': notes,
      },
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> offsetDepartmentDues({
    required String referenceNo,
    required String department,
    required double amount,
    required String reason,
    String? authorizedBy,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/withdrawal/$referenceNo/offset-dues',
      data: {
        'department': department,
        'amount': amount,
        'reason': reason,
        'student_consent': true,
        'authorized_by': authorizedBy ?? 'Finance Officer',
      },
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> fetchDepositLedger(String referenceNo) async {
    final response = await _dio.get<Map<String, dynamic>>('/withdrawal/$referenceNo/deposit-ledger');
    return response.data ?? {};
  }
}
