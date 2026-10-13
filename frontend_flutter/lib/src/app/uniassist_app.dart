import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/kiosk_theme.dart';
import '../features/kiosk/presentation/assistant_fab.dart';
import '../core/services/page_context_service.dart';
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
import '../features/staff/presentation/staff_procedure_wizard_screen.dart';
import '../features/withdrawal/presentation/withdrawal_flow_screen.dart';
import '../features/withdrawal/presentation/withdrawal_home_screen.dart';

class UniAssistApp extends ConsumerWidget {
  const UniAssistApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = GoRouter(
      initialLocation: '/',
      observers: [
        _PageContextObserver((route) {
          ref.read(pageContextProvider.notifier).setRoute(route);
        }),
      ],
      routes: [
        GoRoute(path: '/', builder: (context, state) => const KioskWelcomeScreen()),
        GoRoute(path: '/services', builder: (context, state) => const GuestServicesScreen()),
        GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
        GoRoute(path: '/dashboard', builder: (context, state) => const _KioskSession(route: '/dashboard', child: DashboardScreen())),
        GoRoute(path: '/request-status', builder: (context, state) => const _KioskSession(route: '/request-status', child: RequestStatusScreen())),
        GoRoute(path: '/documents', builder: (context, state) => const _KioskSession(route: '/documents', child: DocumentCenterScreen())),
        GoRoute(path: '/forms', builder: (context, state) => const _KioskSession(route: '/forms', child: FormsCatalogScreen())),
        GoRoute(path: '/academics', builder: (context, state) => const _KioskSession(route: '/academics', child: AcademicsScreen())),
        GoRoute(path: '/scholarship', builder: (context, state) => const _KioskSession(route: '/scholarship', child: ScholarshipScreen())),
        GoRoute(path: '/grievance', builder: (context, state) => const _KioskSession(route: '/grievance', child: GrievanceScreen())),
        GoRoute(path: '/withdrawal', builder: (context, state) => const _KioskSession(route: '/withdrawal', child: WithdrawalHomeScreen())),
        GoRoute(path: '/withdrawal/flow', builder: (context, state) => const _KioskSession(route: '/withdrawal/flow', child: WithdrawalFlowScreen())),
        GoRoute(path: '/notifications', builder: (context, state) => const _KioskSession(route: '/notifications', child: NotificationsScreen())),
        GoRoute(path: '/notices', builder: (context, state) => const _KioskSession(route: '/notices', child: NoticesScreen())),
        GoRoute(path: '/chat', builder: (context, state) => const _KioskSession(route: '/chat', child: ChatScreen())),
        GoRoute(path: '/staff', builder: (context, state) => const _StaffSession(route: '/staff', child: StaffDashboardScreen())),
        GoRoute(path: '/staff/withdrawals', builder: (context, state) => const _StaffSession(route: '/staff/withdrawals', child: StaffWithdrawalScreen())),
        GoRoute(path: '/staff/grievances', builder: (context, state) => const _StaffSession(route: '/staff/grievances', child: StaffGrievanceScreen())),
        GoRoute(path: '/staff/documents', builder: (context, state) => const _StaffSession(route: '/staff/documents', child: StaffDocumentScreen())),
        GoRoute(path: '/staff/notesheets', builder: (context, state) => const _StaffSession(route: '/staff/notesheets', child: StaffNotesheetScreen())),
        GoRoute(path: '/staff/registry', builder: (context, state) => const _StaffSession(route: '/staff/registry', child: StaffRegistryScreen())),
        GoRoute(path: '/staff/ocr', builder: (context, state) => const _StaffSession(route: '/staff/ocr', child: StaffDocumentOcrScreen())),
        GoRoute(path: '/staff/accreditation', builder: (context, state) => const _StaffSession(route: '/staff/accreditation', child: StaffAccreditationScreen())),
        GoRoute(path: '/staff/institution', builder: (context, state) => const _StaffSession(route: '/staff/institution', child: StaffInstitutionScreen())),
        GoRoute(path: '/staff/procedures', builder: (context, state) => const _StaffSession(route: '/staff/procedures', child: StaffProcedureWizardScreen())),
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
  const _KioskSession({required this.child, this.route});

  final Widget child;
  final String? route;

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
    if (widget.route != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(pageContextProvider.notifier).setRoute(widget.route!);
        }
      });
    }
  }

  @override
  void didUpdateWidget(_KioskSession oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.route != null && widget.route != oldWidget.route) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(pageContextProvider.notifier).setRoute(widget.route!);
        }
      });
    }
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
      child: Stack(
        children: [
          widget.child,
          Positioned(
            right: 24,
            bottom: 24,
            child: AssistantFab(currentRoute: widget.route),
          ),
        ],
      ),
    );
  }
}

class _StaffSession extends StatelessWidget {
  const _StaffSession({required this.child, this.route = '/staff'});
  final Widget child;
  final String route;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        Positioned(
          right: 24,
          bottom: 24,
          child: AssistantFab(currentRoute: route),
        ),
      ],
    );
  }
}

class _PageContextObserver extends NavigatorObserver {
  final void Function(String route) onRouteChanged;
  _PageContextObserver(this.onRouteChanged);

  void _notifyIfValid(Route<dynamic>? route) {
    if (route == null) return;
    final name = route.settings.name ?? route.settings.arguments?.toString() ?? '';
    if (name.isNotEmpty && !name.contains('ModalBottomSheet')) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        onRouteChanged(name);
      });
    }
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPush(route, previousRoute);
    _notifyIfValid(route);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPop(route, previousRoute);
    _notifyIfValid(previousRoute);
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    super.didReplace(newRoute: newRoute, oldRoute: oldRoute);
    _notifyIfValid(newRoute);
  }
}
