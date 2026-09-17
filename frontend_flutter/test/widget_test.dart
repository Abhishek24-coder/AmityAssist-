import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uniassist/src/app/uniassist_app.dart';
import 'package:uniassist/src/core/services/offline_cache_service.dart';

void main() {
  testWidgets('UniAssist Kiosk Welcome Screen loads successfully', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: const UniAssistApp(),
      ),
    );

    // Wait for splash overlay timer (3 seconds) to dismiss
    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();

    // Verify Welcome Hero Branding is present
    expect(find.text('Welcome to UniAssist'), findsOneWidget);
    expect(find.text('PUBLIC SERVICES'), findsWidgets);
    expect(find.text('STUDENT / STAFF'), findsWidgets);
  });
}
