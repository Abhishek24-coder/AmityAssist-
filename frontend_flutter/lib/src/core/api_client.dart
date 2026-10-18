import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_config.dart';
import 'services/offline_cache_service.dart';

/// Key used to persist the JWT token in SharedPreferences.
const kJwtTokenKey = 'jwt_token';

/// Provides a global singleton instance of Dio for API requests.
final apiClientProvider = Provider<Dio>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);

  final dio = Dio(BaseOptions(
    baseUrl: ApiConfig.apiUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  ));

  // ── JWT auth interceptor ──────────────────────────────────
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = prefs.getString(kJwtTokenKey);
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        // On 401 Unauthorized, clear the stored token so the UI
        // can redirect to login.
        if (error.response?.statusCode == 401) {
          prefs.remove(kJwtTokenKey);
        }
        return handler.next(error);
      },
    ),
  );

  return dio;
});
