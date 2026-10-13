import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Represents the active screen context known to the AI assistant
/// without exposing sensitive student PII.
@immutable
class PageContextState {
  final String route;
  final String screenName;
  final List<String> availableActions;
  final String? primaryAction;

  const PageContextState({
    required this.route,
    required this.screenName,
    required this.availableActions,
    this.primaryAction,
  });

  Map<String, dynamic> toJson() => {
        'route': route,
        'screen_name': screenName,
        'available_actions': availableActions,
        if (primaryAction != null) 'primary_action': primaryAction,
      };

  factory PageContextState.fromRoute(String route) {
    final cleanRoute = route.toLowerCase().trim();
    if (cleanRoute.contains('withdrawal/flow')) {
      return const PageContextState(
        route: '/withdrawal/flow',
        screenName: 'Withdrawal Clearance Workflow',
        availableActions: [
          'Verify Academic Clearance Gate',
          'Review Library & Lab Dues',
          'Calculate Caution Deposit Refund',
          'Submit Final Clearance'
        ],
        primaryAction: 'Verify Academic Clearance Gate',
      );
    } else if (cleanRoute.contains('withdrawal')) {
      return const PageContextState(
        route: '/withdrawal',
        screenName: 'Program Withdrawal Portal',
        availableActions: [
          'Initiate Withdrawal Request',
          'Review Refund Policy',
          'Contact Counselor',
          'Download Clearance Checklist'
        ],
        primaryAction: 'Initiate Withdrawal Request',
      );
    } else if (cleanRoute.contains('academics')) {
      return const PageContextState(
        route: '/academics',
        screenName: 'Academics & Examination Registry',
        availableActions: [
          'Register for Backpaper Exam',
          'Download Grade Cards',
          'Request Duplicate Marksheet',
          'Apply for Re-evaluation'
        ],
        primaryAction: 'Register for Backpaper Exam',
      );
    } else if (cleanRoute.contains('forms')) {
      return const PageContextState(
        route: '/forms',
        screenName: 'Institutional Forms & Applications Catalog',
        availableActions: [
          'Hostel Allotment Application',
          'Bonafide Certificate Request',
          'Fee Concession Form',
          'Identity Card Replacement'
        ],
        primaryAction: 'Bonafide Certificate Request',
      );
    } else if (cleanRoute.contains('scholarship')) {
      return const PageContextState(
        route: '/scholarship',
        screenName: 'Merit & Need Scholarships Portal',
        availableActions: [
          'Apply for Merit Scholarship',
          'Upload Income Certificate',
          'Check Disbursement Status'
        ],
        primaryAction: 'Apply for Merit Scholarship',
      );
    } else if (cleanRoute.contains('grievance')) {
      return const PageContextState(
        route: '/grievance',
        screenName: 'Student Grievance Redressal Desk',
        availableActions: [
          'Submit Grievance Ticket',
          'Track Complaint Status',
          'Contact Student Welfare Dean'
        ],
        primaryAction: 'Submit Grievance Ticket',
      );
    } else if (cleanRoute.contains('request-status')) {
      return const PageContextState(
        route: '/request-status',
        screenName: 'Service Request Status Tracker',
        availableActions: [
          'View Active Applications',
          'Check Approval Timeline',
          'Download Acknowledgement Slip'
        ],
        primaryAction: 'View Active Applications',
      );
    } else if (cleanRoute.contains('documents')) {
      return const PageContextState(
        route: '/documents',
        screenName: 'Digital Document Center & Certificates',
        availableActions: [
          'Download Degree Certificate',
          'View Verified Transcripts',
          'Request Migration Certificate'
        ],
        primaryAction: 'Download Degree Certificate',
      );
    } else if (cleanRoute.contains('notices')) {
      return const PageContextState(
        route: '/notices',
        screenName: 'Official University Notices & Circulars',
        availableActions: [
          'Read Academic Calendar',
          'View Examination Circulars',
          'Filter Campus Notifications'
        ],
        primaryAction: 'Read Academic Calendar',
      );
    } else if (cleanRoute.contains('notifications')) {
      return const PageContextState(
        route: '/notifications',
        screenName: 'Student Notifications & Alerts',
        availableActions: [
          'Mark All as Read',
          'Check Fee Reminders',
          'View Attendance Alerts'
        ],
        primaryAction: 'Check Fee Reminders',
      );
    } else if (cleanRoute.contains('chat')) {
      return const PageContextState(
        route: '/chat',
        screenName: 'AI Student Advisory & Counseling Chat',
        availableActions: [
          'Ask Academic Counselor',
          'Inquire About Fees & Rules',
          'Get Campus Assistance'
        ],
        primaryAction: 'Ask Academic Counselor',
      );
    } else if (cleanRoute.contains('staff')) {
      return const PageContextState(
        route: '/staff',
        screenName: 'Registrar Staff Desk & Decision Registry',
        availableActions: [
          'Review Disciplinary Notesheet',
          'Scan Physical Document (OCR)',
          'Filter Pending Approvals'
        ],
        primaryAction: 'Review Disciplinary Notesheet',
      );
    } else if (cleanRoute.contains('services')) {
      return const PageContextState(
        route: '/services',
        screenName: 'Guest University Services Directory',
        availableActions: [
          'Explore Campus Services',
          'View Department Counters',
          'Check Office Hours'
        ],
        primaryAction: 'Explore Campus Services',
      );
    } else if (cleanRoute.contains('login')) {
      return const PageContextState(
        route: '/login',
        screenName: 'Student Identity Sign-In',
        availableActions: [
          'Enter Student Enrollment ID',
          'Scan Campus Smart Card',
          'Sign In with University Credentials'
        ],
        primaryAction: 'Enter Student Enrollment ID',
      );
    }

    return const PageContextState(
      route: '/dashboard',
      screenName: 'Student Services Kiosk Dashboard',
      availableActions: [
        'Explore Services Catalog',
        'Check Active Request Status',
        'Ask Digital Counselor',
        'Switch Language / Theme'
      ],
      primaryAction: 'Explore Services Catalog',
    );
  }
}

class PageContextNotifier extends StateNotifier<PageContextState> {
  PageContextNotifier() : super(PageContextState.fromRoute('/dashboard'));

  void setRoute(String route) {
    state = PageContextState.fromRoute(route);
  }

  void updateContext({
    required String screenName,
    required List<String> availableActions,
    String? primaryAction,
  }) {
    state = PageContextState(
      route: state.route,
      screenName: screenName,
      availableActions: availableActions,
      primaryAction: primaryAction,
    );
  }
}

final pageContextProvider =
    StateNotifierProvider<PageContextNotifier, PageContextState>((ref) {
  return PageContextNotifier();
});

/// Provides current button/action target to pulse highlight on screen
class HighlightNotifier extends StateNotifier<String?> {
  HighlightNotifier() : super(null);

  void triggerHighlight(String actionId) {
    state = actionId;
    Future.delayed(const Duration(seconds: 4), () {
      if (state == actionId) {
        state = null;
      }
    });
  }

  void clear() {
    state = null;
  }
}

final buttonHighlightProvider =
    StateNotifierProvider<HighlightNotifier, String?>((ref) {
  return HighlightNotifier();
});
