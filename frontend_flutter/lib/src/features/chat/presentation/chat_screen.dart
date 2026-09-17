import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../../core/widgets/uniassist_logo.dart';

class ChatMessage {
  const ChatMessage({
    required this.text,
    required this.isUser,
  });

  final String text;
  final bool isUser;
}

class ChatState {
  const ChatState({
    this.messages = const [],
    this.currentOptions = const [],
  });

  final List<ChatMessage> messages;
  final List<String> currentOptions;

  ChatState copyWith({
    List<ChatMessage>? messages,
    List<String>? currentOptions,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      currentOptions: currentOptions ?? this.currentOptions,
    );
  }
}

class AdvisorNotifier extends StateNotifier<ChatState> {
  AdvisorNotifier() : super(const ChatState()) {
    _initWelcome();
  }

  void _initWelcome() {
    state = ChatState(
      messages: const [
        ChatMessage(
          text: 'Welcome to the UniAssist Advisor.\nI can guide you through university procedures step-by-step.\n\nWhat do you need help with today?',
          isUser: false,
        ),
      ],
      currentOptions: const [
        'Withdrawal',
        'Certificates',
        'Grievances',
        'Scholarships',
        'Hostel',
      ],
    );
  }

  void handleInput(String option) {
    // Add user message
    final newMessages = List<ChatMessage>.from(state.messages)..add(ChatMessage(text: option, isUser: true));
    
    state = state.copyWith(messages: newMessages, currentOptions: []);
    
    // Simulate slight delay for natural feel
    Future.delayed(const Duration(milliseconds: 300), () {
      _processResponse(option);
    });
  }

  void _processResponse(String option) {
    final newMessages = List<ChatMessage>.from(state.messages);
    List<String> nextOptions = [];
    String replyText = '';

    // Core State Machine Logic
    switch (option) {
      // ── Main Menu ──────────────────────────────────────
      case 'Withdrawal':
        replyText = "I can help you complete the withdrawal process.\nLet's begin.\n\nStep 1: Please select your withdrawal reason.";
        nextOptions = ['Academic', 'Financial', 'Medical', 'Personal', 'Other'];
        break;
      
      // ── Withdrawal Workflow ────────────────────────────
      case 'Academic':
      case 'Financial':
      case 'Medical':
      case 'Personal':
      case 'Other':
        // Assuming they came from Withdrawal step 1
        if (state.messages.any((m) => m.text.contains('withdrawal reason'))) {
          replyText = "Got it. Your reason is noted.\n\nStep 2: You must fill out the Official Withdrawal Form.\nWould you like to download it now or print it at the kiosk?";
          nextOptions = ['Download Form', 'Print at Kiosk', 'I already have it'];
        } else {
          _fallback(newMessages);
          return;
        }
        break;

      case 'Download Form':
      case 'Print at Kiosk':
      case 'I already have it':
        replyText = "Excellent.\n\nStep 3: Required Documents.\nYou will need:\n- Completed Withdrawal Form\n- Student ID Card\n- Cancelled Cheque (for refunds)\n- No Dues Certificate\n\nStep 4: Do you have all these documents ready?";
        nextOptions = ['Yes, all ready', 'What is a cancelled cheque?', 'How to get No Dues?'];
        break;
      
      case 'What is a cancelled cheque?':
        replyText = "A cancelled cheque is a cheque with two diagonal lines and the word CANCELLED written across it.\n\nPurpose: Used to verify your bank account details for refund processing.\n\nCommon mistakes:\n- Wrong account holder\n- Unclear image\n- Missing account information\n\nDo you have your documents ready now?";
        nextOptions = ['Yes, all ready', 'How to get No Dues?'];
        break;
      
      case 'How to get No Dues?':
        replyText = "You must clear your dues from the Library, Hostel, and Accounts departments. The 'No Dues Certificate' form must be signed by the respective department heads.\n\nDo you have your documents ready now?";
        nextOptions = ['Yes, all ready'];
        break;

      case 'Yes, all ready':
        replyText = "Great. Let's review the checklist:\nWithdrawal Form ✓\nStudent ID ✓\nCancelled Cheque ✓\nNo Dues Certificate ✓\n\nStep 5: Please submit these physical documents in a clear folder to the Registrar's Office (Block A, Room 102).\n\nStep 6: Departments involved in processing are Registrar, Dean of Academics, and Finance.\n\nAre you ready for the timeline information?";
        nextOptions = ['Yes, show timeline'];
        break;
      
      case 'Yes, show timeline':
        replyText = "Step 7 & 8: Timelines & Refunds.\n\nAccording to university guidelines, academic processing takes 3–5 working days, and finance processing generally takes 7–10 working days.\n\nImportant: I cannot predict the exact date, this is the official timeline.\n\nStep 9: Workflow complete! You will receive email updates as your file moves between departments.\nIs there anything else you need?";
        nextOptions = ['Start Over', 'Exit'];
        break;

      // ── Other Main Options (Stubs) ─────────────────────
      case 'Certificates':
        replyText = "I can help with Certificates.\nWhat kind of certificate do you need?";
        nextOptions = ['Bonafide', 'Migration', 'Provisional Degree', 'Start Over'];
        break;
      
      case 'Bonafide':
      case 'Migration':
      case 'Provisional Degree':
        replyText = "For this certificate, you will need:\n- ID Proof\n- Fee Clearance\n\nSubmission: Online Portal or Kiosk Form Drop.\nTimeline: 3-5 working days.\n\nWould you like to proceed?";
        nextOptions = ['Yes, proceed', 'Start Over'];
        break;
      
      case 'Yes, proceed':
        replyText = "Great. Please download the respective form from the Guest Services section, fill it, and submit it at Counter 3.\nCan I help with anything else?";
        nextOptions = ['Start Over'];
        break;

      case 'Grievances':
        replyText = "I can help you file a grievance.\nPlease categorize your issue:";
        nextOptions = ['Academic Issue', 'Fee Issue', 'Hostel Issue', 'Exam Issue'];
        break;

      case 'Academic Issue':
      case 'Fee Issue':
      case 'Hostel Issue':
      case 'Exam Issue':
        replyText = "Thank you. To resolve this, you need to submit a formal grievance ticket. The standard response time is 3 working days.\n\nYou can track the status in your Dashboard.\nWould you like to initiate the ticket now?";
        nextOptions = ['Yes, create ticket', 'Start Over'];
        break;
      
      case 'Yes, create ticket':
        replyText = "Ticket created successfully! (Simulated). Your reference number is GRV-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}.\nAnything else?";
        nextOptions = ['Start Over'];
        break;
      
      case 'Scholarships':
        replyText = "Scholarship Assistance:\nTo apply, you need a minimum CGPA of 8.0, previous semester marksheets, and an income certificate.\n\nDeadline: October 15th.\nWould you like to check your eligibility?";
        nextOptions = ['Check Eligibility', 'Start Over'];
        break;

      case 'Check Eligibility':
        replyText = "You meet the CGPA requirement! You can submit your application via the Scholarship portal on your dashboard.\nAnything else?";
        nextOptions = ['Start Over'];
        break;
      
      case 'Hostel':
        replyText = "Hostel Services.\nWhat do you need help with?";
        nextOptions = ['Hostel Entry', 'Hostel Exit', 'Maintenance', 'Start Over'];
        break;
      
      case 'Hostel Entry':
      case 'Hostel Exit':
      case 'Maintenance':
        replyText = "Process Guidance: Please ensure you have your room allotment letter and ID. Fill the requisition form available in the Forms section and submit to the Warden.\n\nTimeline: 24-48 hours for processing.\nAnything else?";
        nextOptions = ['Start Over'];
        break;

      case 'Start Over':
        _initWelcome();
        return;
      
      case 'Exit':
        replyText = "Thank you for using the UniAssist Advisor. Have a great day!";
        nextOptions = ['Start Over'];
        break;

      default:
        _fallback(newMessages);
        return;
    }

    newMessages.add(ChatMessage(text: replyText, isUser: false));
    state = state.copyWith(messages: newMessages, currentOptions: nextOptions);
  }

  void _fallback(List<ChatMessage> newMessages) {
    newMessages.add(const ChatMessage(
      text: 'I could not find official information for this request or the workflow got interrupted.\n\nLet\'s start over.',
      isUser: false,
    ));
    state = state.copyWith(messages: newMessages, currentOptions: ['Start Over']);
  }
}

final advisorProvider = StateNotifierProvider.autoDispose<AdvisorNotifier, ChatState>((ref) {
  return AdvisorNotifier();
});

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _scrollController = ScrollController();

  void _send(String option) {
    ref.read(advisorProvider.notifier).handleInput(option);
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent + 200, // overshoot slightly for new content
        duration: const Duration(milliseconds: 240),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(advisorProvider);
    
    // Auto-scroll when new messages arrive if we're near the bottom
    ref.listen<ChatState>(advisorProvider, (previous, next) {
      if (previous?.messages.length != next.messages.length) {
        _scrollToBottom();
      }
    });

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 76,
        title: const UniAssistLogo(size: 42, showWordmark: true),
      ),
      body: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 14, 22, 0),
          child: Column(
            children: [
              const _AdvisorHeader(),
              const SizedBox(height: 14),
              Expanded(
                child: Card(
                  margin: EdgeInsets.zero,
                  child: ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(18),
                    itemCount: state.messages.length,
                    itemBuilder: (context, index) {
                      final message = state.messages[index];
                      return _ChatBubble(message: message)
                          .animate()
                          .fadeIn(duration: 200.ms)
                          .slideY(begin: 0.05);
                    },
                  ),
                ),
              ),
              // The fixed bottom options tray
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 20),
                child: state.currentOptions.isEmpty
                    ? const Center(
                        child: Padding(
                          padding: EdgeInsets.all(12.0),
                          child: CircularProgressIndicator(),
                        ),
                      )
                    : Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 12,
                        runSpacing: 12,
                        children: state.currentOptions
                            .map(
                              (option) => ActionChip(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                                label: Text(option),
                                avatar: const Icon(Icons.touch_app_rounded, size: 18),
                                onPressed: () => _send(option),
                              ).animate().fadeIn(duration: 150.ms).scale(begin: const Offset(0.95, 0.95)),
                            )
                            .toList(),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AdvisorHeader extends StatelessWidget {
  const _AdvisorHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.line),
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.tealSoft,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.support_agent_rounded, color: AppColors.teal, size: 30),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Digital Counselor', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 3),
                Text(
                  'Guided procedures and official university workflows.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.muted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    return Padding(
      padding: EdgeInsets.only(
        left: isUser ? 80 : 0,
        right: isUser ? 0 : 80,
        bottom: 14,
      ),
      child: Column(
        crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
            decoration: BoxDecoration(
              color: isUser ? AppColors.primary : AppColors.primarySoft,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: isUser ? AppColors.primary : AppColors.line),
            ),
            child: Text(
              message.text,
              style: TextStyle(
                color: isUser ? Colors.white : AppColors.ink,
                fontSize: 15.5,
                height: 1.42,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
