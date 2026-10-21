import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:local_auth/local_auth.dart';

import '../../../core/api_client.dart';
import '../../../core/services/offline_cache_service.dart';

/// Models the authentication state for both student and staff.
class AuthState {
  final bool isLoading;
  final String? studentId;
  final String? token;
  final String? error;
  final bool isStaff;
  final String? staffRole;
  final String? staffUsername;

  const AuthState({
    this.isLoading = false,
    this.studentId,
    this.token,
    this.error,
    this.isStaff = false,
    this.staffRole,
    this.staffUsername,
  });

  bool get isAuthenticated => token != null;

  AuthState copyWith({
    bool? isLoading,
    String? studentId,
    String? token,
    String? error,
    bool? isStaff,
    String? staffRole,
    String? staffUsername,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      studentId: studentId ?? this.studentId,
      token: token ?? this.token,
      error: error,
      isStaff: isStaff ?? this.isStaff,
      staffRole: staffRole ?? this.staffRole,
      staffUsername: staffUsername ?? this.staffUsername,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final Dio _dio;
  final SharedPreferences _prefs;

  AuthNotifier(this._dio, this._prefs) : super(const AuthState()) {
    _restoreSession();
  }

  // ── Restore persisted JWT session on app start ────────────
  void _restoreSession() {
    final token = _prefs.getString(kJwtTokenKey);
    
    // Clear out old dummy tokens if they somehow got cached
    if (token == 'local_demo_token') {
      logout();
      return;
    }

    final studentId = _prefs.getString('student_id');
    final isStaff = _prefs.getBool('is_staff') ?? false;
    final staffRole = _prefs.getString('staff_role');
    final staffUsername = _prefs.getString('staff_username');

    if (token != null && token.isNotEmpty) {
      state = AuthState(
        token: token,
        studentId: studentId,
        isStaff: isStaff,
        staffRole: staffRole,
        staffUsername: staffUsername,
      );
    } else {
      // Clear out any stale/orphaned student_id or staff credentials when not authenticated
      _prefs.remove('student_id');
      _prefs.remove('is_staff');
      _prefs.remove('staff_role');
      _prefs.remove('staff_username');
      state = const AuthState();
    }
  }

  // ── Student JWT login ─────────────────────────────────────
  Future<bool> login(String studentId) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.post('/auth/login', data: {
        'student_id': studentId,
      });

      if (response.statusCode == 200) {
        final data = response.data;
        final token = data['token'] as String?;
        final sid = data['student_id'] as String? ?? studentId.toUpperCase();

        if (token != null) {
          await _prefs.setString(kJwtTokenKey, token);
          await _prefs.setString('student_id', sid);
          await _prefs.setBool('is_staff', false);

          state = AuthState(
            token: token,
            studentId: sid,
            isStaff: false,
          );
          return true;
        }
      }
      state = state.copyWith(
        isLoading: false,
        error: 'Login failed. Please check your Student ID.',
      );
      return false;
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Network error occurred. Ensure backend is running.';
      state = state.copyWith(isLoading: false, error: msg.toString());
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'An unexpected error occurred.');
      return false;
    }
  }

  // ── Staff JWT login ───────────────────────────────────────
  Future<bool> biometricLogin() async {
    final LocalAuthentication auth = LocalAuthentication();
    try {
      final bool canAuthenticateWithBiometrics = await auth.canCheckBiometrics;
      final bool canAuthenticate = canAuthenticateWithBiometrics || await auth.isDeviceSupported();

      if (!canAuthenticate) {
        state = state.copyWith(error: 'Biometrics not supported on this device.');
        return false;
      }

      final bool didAuthenticate = await auth.authenticate(
        localizedReason: 'Please authenticate to access UniAssist',
      );

      if (didAuthenticate) {
        // Assume session is already restored (token exists from previous login)
        return true;
      } else {
        state = state.copyWith(error: 'Biometric authentication failed.');
        return false;
      }
    } catch (e) {
      state = state.copyWith(error: 'Error during biometric authentication.');
      return false;
    }
  }

  // ── Staff JWT login ───────────────────────────────────────
  Future<bool> staffLogin(String username, String role) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _dio.post('/auth/staff/login', data: {
        'username': username,
      });

      if (response.statusCode == 200) {
        final data = response.data;
        final token = data['token'] as String?;

        if (token != null) {
          await _prefs.setString(kJwtTokenKey, token);
          await _prefs.setString('staff_username', username);
          await _prefs.setString('staff_role', data['role'] as String? ?? role);
          await _prefs.setBool('is_staff', true);

          state = AuthState(
            token: token,
            isStaff: true,
            staffUsername: username,
            staffRole: data['role'] as String? ?? role,
          );
          return true;
        }
      }
      state = state.copyWith(
        isLoading: false,
        error: 'Staff login failed. Check your credentials.',
      );
      return false;
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Network error occurred.';
      state = state.copyWith(isLoading: false, error: msg.toString());
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'An unexpected error occurred.');
      return false;
    }
  }

  // ── Logout ────────────────────────────────────────────────
  Future<void> logout() async {
    await _prefs.remove(kJwtTokenKey);
    await _prefs.remove('student_id');
    await _prefs.remove('is_staff');
    await _prefs.remove('staff_role');
    await _prefs.remove('staff_username');
    state = const AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final dio = ref.watch(apiClientProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return AuthNotifier(dio, prefs);
});
