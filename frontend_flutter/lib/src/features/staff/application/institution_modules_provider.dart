import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';

/// Provider for dynamic module enablement across the institution.
/// If an administrator disables a module (e.g. scholarships, hostel, grievance),
/// the UI reactively hides or disables that section.
final institutionModulesProvider = FutureProvider<Map<String, bool>>((ref) async {
  final client = ref.watch(apiClientProvider);
  try {
    final res = await client.get('/institution/modules');
    if (res.data is Map<String, dynamic>) {
      final rawModules = (res.data as Map<String, dynamic>)['modules'];
      if (rawModules is Map) {
        return rawModules.map((k, v) => MapEntry(k.toString(), v == true));
      }
    }
  } catch (_) {
    // Graceful offline fallback: keep all existing features active
  }

  return const {
    'dashboard': true,
    'academics': true,
    'withdrawal': true,
    'forms': true,
    'grievance': true,
    'scholarships': true,
    'hostel': true,
    'examinations': true,
    'voice_ai': true,
    'documents': true,
    'notices': true,
  };
});
