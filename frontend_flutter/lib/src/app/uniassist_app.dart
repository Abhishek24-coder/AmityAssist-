import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/kiosk_theme.dart';
import '../features/kiosk/presentation/kiosk_welcome_screen.dart';
import '../features/services/presentation/guest_services_screen.dart';
import '../features/auth/application/auth_provider.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/chat/presentation/chat_screen.dart';
import '../features/dashboard/presentation/academics_screen.dart';
import '../features/dashboard/presentation/dashboard_screen.dart';
import '../features/dashboard/presentation/document_center_screen.dart';
import '../features/dashboard/presentation/request_status_screen.dart';
import '../features/forms/presentation/forms_catalog_screen.dart';
import '../features/grievance/presentation/grievance_screen.dart';
import '../features/notices/presentation/notices_screen.dart';
import '../features/notifications/presentation/notifications_screen.dart';
import '../features/scholarship/presentation/scholarship_screen.dart';
import '../features/staff/presentation/staff_dashboard_screen.dart';
import '../features/staff/presentation/staff_document_screen.dart';
import '../features/staff/presentation/staff_grievance_screen.dart';
import '../features/staff/presentation/staff_withdrawal_screen.dart';
import '../features/staff/presentation/staff_notesheet_screen.dart';
import '../features/staff/presentation/staff_registry_screen.dart';
import '../features/staff/presentation/staff_document_ocr_screen.dart';
import '../features/staff/presentation/staff_accreditation_screen.dart';
import '../features/staff/presentation/staff_institution_screen.dart';
import '../features/withdrawal/presentation/withdrawal_flow_screen.dart';
import '../features/withdrawal/presentation/withdrawal_home_screen.dart';

class UniAssistApp extends ConsumerWidget {
  const UniAssistApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(path: '/', builder: (context, state) => const KioskWelcomeScreen()),
        GoRoute(path: '/services', builder: (context, state) => const GuestServicesScreen()),
        GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
        GoRoute(path: '/dashboard', builder: (context, state) => const _KioskSession(child: DashboardScreen())),
        GoRoute(path: '/request-status', builder: (context, state) => const _KioskSession(child: RequestStatusScreen())),
        GoRoute(path: '/documents', builder: (context, state) => const _KioskSession(child: DocumentCenterScreen())),
        GoRoute(path: '/forms', builder: (context, state) => const _KioskSession(child: FormsCatalogScreen())),
        GoRoute(path: '/academics', builder: (context, state) => const _KioskSession(child: AcademicsScreen())),
        GoRoute(path: '/scholarship', builder: (context, state) => const _KioskSession(child: ScholarshipScreen())),
        GoRoute(path: '/grievance', builder: (context, state) => const _KioskSession(child: GrievanceScreen())),
        GoRoute(path: '/withdrawal', builder: (context, state) => const _KioskSession(child: WithdrawalHomeScreen())),
        GoRoute(path: '/withdrawal/flow', builder: (context, state) => const _KioskSession(child: WithdrawalFlowScreen())),
        GoRoute(path: '/notifications', builder: (context, state) => const _KioskSession(child: NotificationsScreen())),
        GoRoute(path: '/notices', builder: (context, state) => const _KioskSession(child: NoticesScreen())),
        GoRoute(path: '/chat', builder: (context, state) => const _KioskSession(child: ChatScreen())),
        GoRoute(path: '/staff', builder: (context, state) => const StaffDashboardScreen()),
        GoRoute(path: '/staff/withdrawals', builder: (context, state) => const StaffWithdrawalScreen()),
        GoRoute(path: '/staff/grievances', builder: (context, state) => const StaffGrievanceScreen()),
        GoRoute(path: '/staff/documents', builder: (context, state) => const StaffDocumentScreen()),
        GoRoute(path: '/staff/notesheets', builder: (context, state) => const StaffNotesheetScreen()),
        GoRoute(path: '/staff/registry', builder: (context, state) => const StaffRegistryScreen()),
        GoRoute(path: '/staff/ocr', builder: (context, state) => const StaffDocumentOcrScreen()),
        GoRoute(path: '/staff/accreditation', builder: (context, state) => const StaffAccreditationScreen()),
        GoRoute(path: '/staff/institution', builder: (context, state) => const StaffInstitutionScreen()),
      ],
    );

    return MaterialApp.router(
      title: 'UNIASSIST',
      theme: KioskTheme.light,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}

class _KioskSession extends ConsumerStatefulWidget {
  const _KioskSession({required this.child});

  final Widget child;

  @override
  ConsumerState<_KioskSession> createState() => _KioskSessionState();
}

class _KioskSessionState extends ConsumerState<_KioskSession> {
  static const _timeout = Duration(minutes: 5);
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _resetTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _resetTimer() {
    _timer?.cancel();
    _timer = Timer(_timeout, _expireSession);
  }

  void _expireSession() {
    if (!mounted) return;
    ref.read(authProvider.notifier).logout();
    context.go('/');
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Session reset for student privacy.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerDown: (_) => _resetTimer(),
      onPointerMove: (_) => _resetTimer(),
      behavior: HitTestBehavior.translucent,
      child: widget.child,
    );
  }
}
