import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../../../core/services/voice_service.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../../core/services/tts_service.dart';
import '../../../core/services/stt_service.dart';
import '../../../core/services/page_context_service.dart';
import '../../auth/application/auth_provider.dart';
import '../../../core/widgets/formatted_markdown_text.dart';
import 'chat_screen.dart';

/// Shows the AI Digital Counselor in a touch-first modal/dialog on kiosk or mobile.
Future<void> showDigitalCounselor(
  BuildContext context, {
  int initialTab = 0,
  bool autoStartVoice = false,
  String? currentRoute,
}) {
  final screenWidth = MediaQuery.of(context).size.width;
  final isMobile = screenWidth < 700;

  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    constraints: BoxConstraints(
      maxWidth: isMobile ? double.infinity : 780,
    ),
    builder: (context) => DigitalCounselorModal(
      initialTab: initialTab,
      autoStartVoice: autoStartVoice,
      currentRoute: currentRoute,
    ),
  );
}

class DigitalCounselorModal extends ConsumerStatefulWidget {
  const DigitalCounselorModal({
    super.key,
    this.initialTab = 0,
    this.autoStartVoice = false,
    this.currentRoute,
  });

  final int initialTab;
  final bool autoStartVoice;
  final String? currentRoute;

  @override
  ConsumerState<DigitalCounselorModal> createState() => _DigitalCounselorModalState();
}

class _DigitalCounselorModalState extends ConsumerState<DigitalCounselorModal> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _chatTextController = TextEditingController();
  late int _activeTab;

  @override
  void initState() {
    super.initState();
    _activeTab = widget.initialTab;
    if (widget.currentRoute != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(pageContextProvider.notifier).setRoute(widget.currentRoute!);
        }
      });
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _chatTextController.dispose();
    super.dispose();
  }

  void _handleSend(String option) {
    ref.read(advisorProvider.notifier).handleInput(option);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent + 200,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(advisorProvider);
    final mediaQuery = MediaQuery.of(context);
    final screenHeight = mediaQuery.size.height;
    final screenWidth = mediaQuery.size.width;
    final isMobile = screenWidth < 700;

    // Auto-scroll when new messages arrive
    ref.listen<ChatState>(advisorProvider, (previous, next) {
      if (previous?.messages.length != next.messages.length) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scrollController.hasClients) {
            _scrollController.animateTo(
              _scrollController.position.maxScrollExtent + 200,
              duration: const Duration(milliseconds: 240),
              curve: Curves.easeOut,
            );
          }
        });
      }
    });

    return Center(
      child: Container(
        width: isMobile ? double.infinity : 780,
        height: screenHeight * (isMobile ? 0.94 : 0.88),
        margin: EdgeInsets.symmetric(
          horizontal: isMobile ? 8 : 16,
          vertical: 12,
        ),
        decoration: BoxDecoration(
          color: AppColors.panel,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.18),
              blurRadius: 32,
              offset: const Offset(0, 8),
            ),
          ],
          border: Border.all(color: AppColors.line),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Column(
            children: [
            // Modal Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: const BoxDecoration(
                color: AppColors.primary,
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.support_agent_rounded, color: Colors.white, size: 26),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: const [
                            Flexible(
                              child: Text(
                                'AI Digital Counselor',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 17,
                                  fontWeight: FontWeight.w800,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            SizedBox(width: 8),
                            _OnlinePill(),
                          ],
                        ),
                        const SizedBox(height: 2),
                        const Text(
                          'Guided procedures, ordinances & voice intelligence.',
                          style: TextStyle(
                            color: Colors.white70,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                          overflow: TextOverflow.ellipsis,
                          maxLines: 1,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, color: Colors.white, size: 22),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),

            // Tab Selector (Phase 29 Expansion)
            Container(
              color: AppColors.ink,
              child: Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () => setState(() => _activeTab = 0),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(
                              color: _activeTab == 0 ? AppColors.amityYellow : Colors.transparent,
                              width: 3,
                            ),
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.alt_route_rounded, size: 16, color: _activeTab == 0 ? Colors.white : Colors.white60),
                            const SizedBox(width: 6),
                            Text(
                              'Guided Procedures',
                              style: TextStyle(
                                color: _activeTab == 0 ? Colors.white : Colors.white60,
                                fontWeight: _activeTab == 0 ? FontWeight.bold : FontWeight.w500,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: InkWell(
                      onTap: () => setState(() => _activeTab = 1),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(
                              color: _activeTab == 1 ? AppColors.amityYellow : Colors.transparent,
                              width: 3,
                            ),
                          ),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.policy_rounded, size: 16, color: _activeTab == 1 ? Colors.white : Colors.white60),
                            const SizedBox(width: 6),
                            Text(
                              'Policy & Voice AI',
                              style: TextStyle(
                                color: _activeTab == 1 ? Colors.white : Colors.white60,
                                fontWeight: _activeTab == 1 ? FontWeight.bold : FontWeight.w500,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Main Content Area
            Expanded(
              child: _activeTab == 0
                  ? Column(
                      children: [
                        // Chat Messages Stream
                        Expanded(
                          child: ListView.builder(
                            controller: _scrollController,
                            padding: const EdgeInsets.all(16),
                            itemCount: state.messages.length,
                            itemBuilder: (context, index) {
                              final message = state.messages[index];
                              final isUser = message.isUser;

                              return Padding(
                                padding: const EdgeInsets.only(bottom: 14),
                                child: Column(
                                  crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                                  children: [
                                    Align(
                                      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                                      child: Container(
                                        constraints: BoxConstraints(maxWidth: mediaQuery.size.width * 0.72),
                                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                                        decoration: BoxDecoration(
                                          color: isUser ? AppColors.primary : AppColors.primarySoft,
                                          borderRadius: BorderRadius.circular(10),
                                          border: Border.all(color: isUser ? AppColors.primary : AppColors.line),
                                        ),
                                        child: FormattedMarkdownText(
                                          text: message.text,
                                          isUser: isUser,
                                          fontSize: 14.5,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ).animate().fadeIn(duration: 200.ms).slideY(begin: 0.05);
                            },
                          ),
                        ),

                        // Bottom tray with Quick Action Chips + Interactive Message Input Box
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          decoration: const BoxDecoration(
                            color: Colors.white,
                            border: Border(top: BorderSide(color: AppColors.line)),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (state.currentOptions.isNotEmpty) ...[
                                SingleChildScrollView(
                                  scrollDirection: Axis.horizontal,
                                  child: Row(
                                    children: state.currentOptions
                                        .map(
                                          (option) => Padding(
                                            padding: const EdgeInsets.only(right: 8),
                                            child: ActionChip(
                                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                              labelStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                                              label: Text(option),
                                              avatar: const Icon(Icons.touch_app_rounded, size: 14),
                                              onPressed: () => _handleSend(option),
                                            ),
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ),
                                const SizedBox(height: 10),
                              ],
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: _chatTextController,
                                      decoration: InputDecoration(
                                        hintText: 'Type your question or query here...',
                                        hintStyle: const TextStyle(fontSize: 14),
                                        isDense: true,
                                        filled: true,
                                        fillColor: AppColors.panel,
                                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                        border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(24),
                                          borderSide: const BorderSide(color: AppColors.line),
                                        ),
                                        enabledBorder: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(24),
                                          borderSide: const BorderSide(color: AppColors.line),
                                        ),
                                      ),
                                      onSubmitted: (text) {
                                        if (text.trim().isNotEmpty) {
                                          _handleSend(text.trim());
                                          _chatTextController.clear();
                                        }
                                      },
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  // Stop Generating / Stop TTS button in chat tab
                                  IconButton(
                                    tooltip: 'Stop response / Stop speaking',
                                    icon: const Icon(Icons.stop_circle_rounded, size: 22),
                                    color: Colors.redAccent,
                                    onPressed: () {
                                      TtsService().stop();
                                      WebVoiceBridge.stopSpeaking();
                                    },
                                  ),
                                  const SizedBox(width: 4),
                                  IconButton(
                                    tooltip: 'Switch to Voice AI',
                                    icon: const Icon(Icons.mic_rounded, color: AppColors.teal),
                                    onPressed: () => setState(() => _activeTab = 1),
                                  ),
                                  const SizedBox(width: 4),
                                  IconButton.filled(
                                    tooltip: 'Send message',
                                    onPressed: () {
                                      final text = _chatTextController.text.trim();
                                      if (text.isNotEmpty) {
                                        _handleSend(text);
                                        _chatTextController.clear();
                                      }
                                    },
                                    icon: const Icon(Icons.send_rounded, size: 18),
                                    style: IconButton.styleFrom(
                                      backgroundColor: AppColors.primary,
                                      foregroundColor: Colors.white,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],
                    )
                  : _PolicyVoiceTab(
                      autoStartVoice: widget.autoStartVoice,
                      currentRoute: widget.currentRoute,
                    ),
            ),
          ],
        ),
      ),
    ),
  );
}
}

class _OnlinePill extends StatelessWidget {
  const _OnlinePill();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.success,
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(radius: 3, backgroundColor: Colors.white),
          SizedBox(width: 4),
          Text(
            'ACTIVE',
            style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 0.5),
          ),
        ],
      ),
    );
  }
}

class _VoiceChatTurn {
  final bool isUser;
  final String text;
  final String? speechText;
  final String? engine;
  final String? domain;
  final String? recommendedAction;
  final String? actionUrl;
  final String? screenInstruction;
  final List<dynamic> citations;
  final String? status;
  final bool isAmbiguous;
  final List<dynamic> clarificationOptions;
  final DateTime timestamp;

  _VoiceChatTurn({
    required this.isUser,
    required this.text,
    this.speechText,
    this.engine,
    this.domain,
    this.recommendedAction,
    this.actionUrl,
    this.screenInstruction,
    this.citations = const [],
    this.status,
    this.isAmbiguous = false,
    this.clarificationOptions = const [],
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

class _PolicyVoiceTab extends ConsumerStatefulWidget {
  const _PolicyVoiceTab({
    this.autoStartVoice = false,
    this.currentRoute,
  });

  final bool autoStartVoice;
  final String? currentRoute;

  @override
  ConsumerState<_PolicyVoiceTab> createState() => _PolicyVoiceTabState();
}

class _PolicyVoiceTabState extends ConsumerState<_PolicyVoiceTab> {
  final TextEditingController _queryController = TextEditingController();
  final ScrollController _voiceScrollController = ScrollController();
  final List<_VoiceChatTurn> _conversationHistory = [];
  bool _isLoading = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  String? _errorMessage;

  // Language onboarding & selector state
  bool _hasChosenLanguage = false;
  String _selectedLanguage = 'en-IN';
  String _counselorGreeting = '';

  static const _languageOptions = [
    {'code': 'en-IN', 'label': 'English', 'icon': '🇬🇧'},
    {'code': 'hi-IN', 'label': 'हिन्दी', 'icon': '🇮🇳'},
    {'code': 'hi-Latn', 'label': 'Hinglish', 'icon': '🔤'},
  ];

  StreamSubscription<String>? _sttSub;
  StreamSubscription<bool>? _ttsSub;

  @override
  void initState() {
    super.initState();
    _ttsSub = TtsService().onSpeakingStateChanged.listen((speaking) {
      if (mounted) setState(() => _isSpeaking = speaking);
    });

    _sttSub = SttService().onTranscriptChanged.listen((transcript) {
      if (mounted) setState(() => _queryController.text = transcript);
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_voiceScrollController.hasClients) {
        _voiceScrollController.animateTo(
          _voiceScrollController.position.maxScrollExtent + 350,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _selectLanguageAndGreet(String langCode) {
    final route = widget.currentRoute ?? ref.read(pageContextProvider).route;
    final isPublicRoute = route == '/' || route == '/services' || route == '/login' || route == '/welcome' || route.isEmpty;
    final auth = ref.read(authProvider);
    final isAuth = auth.isAuthenticated && !isPublicRoute;
    final isStaff = isAuth && (auth.isStaff || route.contains('staff'));
    final staffRole = auth.staffRole ?? 'Registrar Staff';
    final studentId = (isAuth && !isStaff) ? auth.studentId : null;

    String greeting;
    if (isStaff) {
      if (langCode == 'hi-IN') {
        greeting = 'नमस्ते! मैं आपका प्रशासनिक AI परामर्शदाता हूँ। आप $staffRole के रूप में लंबित विड्रॉल कतार, डिजिटल नोटशीट, OCR सत्यापन, अथवा विश्वविद्यालय अध्यादेशों की जांच कर सकते हैं। बताइए, मैं आपकी क्या सहायता करूँ?';
      } else if (langCode == 'hi-Latn') {
        greeting = 'Hello! Main aapka Administrative Counselor hoon. Aap $staffRole ke roop me pending withdrawal queue, digital notesheets, OCR document verification, ya university ordinances ke baare mein pooch sakte hain. Main aapki kya help karoon?';
      } else {
        greeting = 'Hello! I am your University Administrative Digital Counselor. As $staffRole, you can ask about pending student withdrawal queues, notesheets review, OCR document audit, or ordinance verifications. How can I assist you today?';
      }
    } else if (isAuth && studentId != null) {
      if (langCode == 'hi-IN') {
        greeting = 'नमस्ते! मैं आपका डिजिटल यूनिवर्सिटी काउंसलर हूँ। आप मुझसे अपनी उपस्थिति, फीस स्थिति, विड्रॉल प्रक्रिया या किसी भी नियम के बारे में पूछ सकते हैं। बताइए, मैं आपकी क्या सहायता करूँ?';
      } else if (langCode == 'hi-Latn') {
        greeting = 'Hello! Main aapka University Counselor hoon. Apni attendance, exam rules, fee status, withdrawal refund ya kisi bhi policy ke baare mein poochiye! Main aapki kya help karoon?';
      } else {
        greeting = 'Hello! I am your University Digital Counselor. You can ask me about your attendance, fee status, withdrawal clearance, or any campus policy. How can I help you today?';
      }
    } else {
      // Unauthenticated Guest
      if (langCode == 'hi-IN') {
        greeting = 'नमस्ते! मैं UniAssist का आधिकारिक विश्वविद्यालय AI परामर्शदाता हूँ। आप मुझसे विश्वविद्यालय नियमावली, उपस्थिति नियम (75%), फीस रिफंड स्लैब और सभी 31 फॉर्मों के बारे में जानकारी प्राप्त कर सकते हैं। व्यक्तिगत उपस्थिति या आवेदन देखने के लिए कृपया लॉगिन करें।';
      } else if (langCode == 'hi-Latn') {
        greeting = 'Namaste! Main UniAssist ka official university AI counselor hoon. Aap mujhse university ordinances, attendance rules (75%), fee refund slabs aur sabhi 31 forms ke baare me pooch sakte hain. Apne personal records dekhne ke liye please login karein.';
      } else {
        greeting = 'Welcome to UniAssist! I am your University Policy and Procedures AI Counselor. You can ask me about institutional ordinances, 75% attendance rules, fee refund slabs, and university forms. To view your personal academic records, please sign in.';
      }
    }

    setState(() {
      _selectedLanguage = langCode;
      _hasChosenLanguage = true;
      _counselorGreeting = greeting;
      _conversationHistory.clear();
      _conversationHistory.add(_VoiceChatTurn(
        isUser: false,
        text: greeting,
        speechText: greeting,
        domain: 'Campus Counselor',
        engine: 'UniAssist Voice AI',
      ));
    });

    // Auto-speaking disabled: student can tap listen/speak button if audio is desired.
    // Auto-listening removed: microphone is strictly push-to-talk to prevent ambient room noise pickup
  }

  void _restartConversation() {
    TtsService().stop();
    WebVoiceBridge.stopSpeaking();
    WebVoiceBridge.stopListening();
    setState(() {
      _isListening = false;
      _isSpeaking = false;
      _isLoading = false;
      _errorMessage = null;
      _queryController.clear();
      _conversationHistory.clear();
      _conversationHistory.add(_VoiceChatTurn(
        isUser: false,
        text: _counselorGreeting.isNotEmpty ? _counselorGreeting : 'Ready to help you. What would you like to know?',
        speechText: _counselorGreeting,
        domain: 'Campus Counselor',
        engine: 'UniAssist Voice AI',
      ));
    });
    _scrollToBottom();
  }

  @override
  void dispose() {
    TtsService().stop();
    SttService().stopListening();
    WebVoiceBridge.stopListening();
    WebVoiceBridge.stopSpeaking();
    _sttSub?.cancel();
    _ttsSub?.cancel();
    _queryController.dispose();
    _voiceScrollController.dispose();
    super.dispose();
  }

  Future<void> _askPolicy(String query, {bool speak = false}) async {
    final cleanQ = query.trim();
    if (cleanQ.isEmpty) return;

    setState(() {
      _conversationHistory.add(_VoiceChatTurn(
        isUser: true,
        text: cleanQ,
      ));
      _isLoading = true;
      _errorMessage = null;
      _queryController.clear();
    });
    _scrollToBottom();

    try {
      final dio = ref.read(apiClientProvider);
      final route = widget.currentRoute ?? ref.read(pageContextProvider).route;
      final isPublicRoute = route == '/' || route == '/services' || route == '/login' || route == '/welcome' || route.isEmpty;
      final auth = ref.read(authProvider);
      final isAuth = auth.isAuthenticated && !isPublicRoute;
      final isStaff = isAuth && (auth.isStaff || route.contains('staff'));
      final studentId = (isAuth && !isStaff) ? auth.studentId : null;
      final staffRole = isStaff ? (auth.staffRole ?? 'Registrar Staff') : null;
      final staffUsername = isStaff ? (auth.staffUsername ?? 'Staff') : null;

      final pageContext = PageContextState.fromRoute(route);
      final pageContextJson = pageContext.toJson();
      pageContextJson['route'] = route;
      if (isStaff) {
        pageContextJson['is_staff'] = true;
        pageContextJson['staff_role'] = staffRole;
        pageContextJson['staff_username'] = staffUsername;
        pageContextJson.remove('student_id');
      } else if (studentId != null && studentId.isNotEmpty) {
        pageContextJson['student_id'] = studentId;
        pageContextJson['is_staff'] = false;
      } else {
        pageContextJson.remove('student_id');
        pageContextJson['is_staff'] = false;
      }

      // Extract sliding window of recent conversation turns (max 6 turns before current query)
      final historyPayload = _conversationHistory
          .take(_conversationHistory.length - 1)
          .toList()
          .reversed
          .take(6)
          .toList()
          .reversed
          .map((t) => {
                'role': t.isUser ? 'user' : 'assistant',
                'content': t.text,
              })
          .toList();

      final requestData = {
        'spoken_text': cleanQ,
        'query': cleanQ,
        'student_id': studentId,
        'is_staff': isStaff,
        'staff_role': staffRole,
        'staff_username': staffUsername,
        'language': _selectedLanguage,
        'page_context': pageContextJson,
        'conversation_history': historyPayload,
      };

      final requestOptions = (isAuth && studentId != null)
          ? null
          : Options(headers: {'Authorization': ''});

      Response resp;
      try {
        resp = await dio.post(
          '/voice/query',
          data: requestData,
          options: requestOptions,
        );
      } catch (_) {
        resp = await dio.post(
          '/policy/guide',
          data: requestData,
          options: requestOptions,
        );
      }

      if (mounted) {
        final data = Map<String, dynamic>.from(resp.data as Map);
        final answer = (data['answer'] ?? data['response_text'] ?? '').toString();
        final speech = (data['speech_text'] ?? answer).toString();
        final engine = data['engine']?.toString() ?? 'Ollama Local AI (Llama 3.2)';
        final domain = data['domain']?.toString();
        final recAction = data['recommended_action']?.toString();
        final actionUrl = data['action_url']?.toString();
        final screenInst = data['screen_instruction']?.toString();
        final citations = (data['citations'] is List) ? (data['citations'] as List) : const [];
        final status = data['status']?.toString();
        final isAmbiguous = data['is_ambiguous'] == true || status == 'trigger_cross_question';
        final clarOptions = (data['clarification_options'] is List)
            ? (data['clarification_options'] as List)
            : const [];

        final detectedLang = data['detected_language']?.toString() ??
            (data['speech_params'] is Map ? data['speech_params']['lang']?.toString() : null) ??
            data['language']?.toString();

        setState(() {
          if (detectedLang != null &&
              (detectedLang == 'hi-IN' ||
                  detectedLang == 'hi-Latn' ||
                  detectedLang == 'en-IN')) {
            _selectedLanguage = detectedLang;
          }
          _conversationHistory.add(_VoiceChatTurn(
            isUser: false,
            text: (speak && speech.isNotEmpty) ? speech : answer,
            speechText: speech,
            engine: engine,
            domain: domain,
            recommendedAction: recAction,
            actionUrl: actionUrl,
            screenInstruction: screenInst,
            citations: citations,
            status: status,
            isAmbiguous: isAmbiguous,
            clarificationOptions: clarOptions,
          ));
          _isLoading = false;
        });
        _scrollToBottom();

        // Trigger pulse highlight if target button exists
        if (data['highlight_target'] != null) {
          ref
              .read(buttonHighlightProvider.notifier)
              .triggerHighlight(data['highlight_target'].toString());
        }

        if (speak && speech.isNotEmpty) {
          _speakGuidance(speech, lang: detectedLang);
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Unable to fetch policy guidance. Please verify server connection.';
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _toggleVoice() async {
    // 1. Immediately stop any active TTS speech so browser doesn't block the microphone
    WebVoiceBridge.stopSpeaking();
    if (_isSpeaking) {
      setState(() => _isSpeaking = false);
    }

    if (_isListening) {
      WebVoiceBridge.stopListening();
      setState(() => _isListening = false);
      return;
    }

    setState(() {
      _isListening = true;
      _errorMessage = null;
    });

    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.mic_rounded, color: Colors.white, size: 20),
            const SizedBox(width: 8),
            Text(
              _selectedLanguage == 'hi-IN'
                  ? 'सुन रहे हैं... कृपया अपना प्रश्न बोलें।'
                  : 'Listening... Speak your question now.',
            ),
          ],
        ),
        duration: const Duration(seconds: 4),
        backgroundColor: AppColors.primary,
      ),
    );

    WebVoiceBridge.startListening(
      lang: _selectedLanguage == 'hi-Latn' ? 'en-IN' : _selectedLanguage,
      onResult: (text) {
        if (mounted) {
          setState(() => _isListening = false);
          _queryController.text = text;
          _askPolicy(text, speak: true);
        }
      },
      onError: (err) {
        if (mounted) {
          setState(() => _isListening = false);
          final errLower = err.toLowerCase();
          if (errLower.contains('aborted') || errLower.contains('no-speech')) {
            return;
          }
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Voice: $err. You can also tap any quick prompt below.'),
              duration: const Duration(seconds: 4),
              backgroundColor: Colors.orange.shade800,
            ),
          );
        }
      },
    );
  }

  void _speakGuidance(String text, {String? lang}) {
    if (text.isEmpty) return;
    setState(() => _isSpeaking = true);
    final chosen = lang ?? _selectedLanguage;
    final targetLang = chosen == 'hi-Latn' ? 'en-IN' : chosen;
    WebVoiceBridge.speak(
      text,
      lang: targetLang,
      rate: 0.95,
      onComplete: () {
        if (mounted) setState(() => _isSpeaking = false);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final isStaff = auth.isStaff || (widget.currentRoute != null && widget.currentRoute!.contains('staff'));

    final quickPrompts = isStaff
        ? [
            {'label': 'Pending Withdrawals Queue', 'q': 'Which students have pending withdrawal requests in the review queue?'},
            {'label': 'Review Digital Notesheets', 'q': 'How do I review and mark active disciplinary notesheets?'},
            {'label': 'OCR Document Audit', 'q': 'How does OCR identity extraction and fraud verification work?'},
            {'label': 'Clearance Pipeline Desk', 'q': 'What are the 4 clearance gates and approval SLAs for staff?'},
            {'label': 'What page are we on?', 'q': 'What page are we on and what should I do next?'},
          ]
        : [
            {'label': 'What page are we on?', 'q': 'What page are we on and what should I do next?'},
            {'label': 'Attendance Shortage (ORD-7.2)', 'q': 'Can I write semester exams with 71% attendance?'},
            {'label': 'Lost ID Card Offset (ORD-14.4)', 'q': 'Can I offset lost ID card ₹200 fine from caution deposit?'},
            {'label': 'Withdrawal Slabs (ORD-14.1)', 'q': 'What is the tuition refund percentage for withdrawal?'},
            {'label': '4-Gate Clearance (ORD-9.3)', 'q': 'How does the 4-gate clearance chain work?'},
            {'label': 'Backpaper Exam Fee (ORD-12.1)', 'q': 'What is the backpaper exam fee and deadline?'},
          ];

    final stopButton = IconButton(
      tooltip: 'Stop response / speaking',
      icon: Icon(
        _isSpeaking || _isListening ? Icons.stop_circle_rounded : Icons.stop_rounded,
        color: _isSpeaking || _isListening ? Colors.redAccent : AppColors.primary,
        size: 22,
      ),
      onPressed: () {
        TtsService().stop();
        WebVoiceBridge.stopListening();
        WebVoiceBridge.stopSpeaking();
        SttService().stopListening();
        setState(() {
          _isListening = false;
          _isSpeaking = false;
        });
      },
    );

    if (!_hasChosenLanguage) {
      return _buildLanguageSelectionPrompt(context);
    }

    return Column(
      key: ValueKey('policy_voice_tab_$_selectedLanguage'),
      children: [
        // 1. Top Controls Bar: Active Language & Controls
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(bottom: BorderSide(color: AppColors.line)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primarySoft,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      _selectedLanguage == 'hi-IN'
                          ? '🇮🇳 हिन्दी'
                          : (_selectedLanguage == 'hi-Latn' ? '🔤 Hinglish' : '🇬🇧 English'),
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.primary),
                    ),
                    const SizedBox(width: 4),
                    const Icon(Icons.check_circle_rounded, size: 13, color: AppColors.primary),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              TextButton.icon(
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                onPressed: () {
                  TtsService().stop();
                  WebVoiceBridge.stopSpeaking();
                  setState(() => _hasChosenLanguage = false);
                },
                icon: const Icon(Icons.tune_rounded, size: 13, color: AppColors.muted),
                label: const Text('Change', style: TextStyle(fontSize: 11.5, color: AppColors.muted)),
              ),
              const SizedBox(width: 4),
              ..._languageOptions.map((opt) {
                final isSelected = _selectedLanguage == opt['code'];
                return Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(8),
                    onTap: () {
                      if (!isSelected) {
                        _selectLanguageAndGreet(opt['code']!);
                      }
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.primary : Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: isSelected ? AppColors.primary : AppColors.line),
                      ),
                      child: Text(
                        '${opt['icon']} ${opt['label']}',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                          color: isSelected ? Colors.white : AppColors.ink,
                        ),
                      ),
                    ),
                  ),
                );
              }),
              const Spacer(),
              // Real-time Ollama status pill
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.shade300),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Colors.green,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    const Text(
                      'OLLAMA AI READY',
                      style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        color: Colors.green,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              // New conversation / reset button
              IconButton(
                tooltip: 'Start new topic / reset history',
                icon: const Icon(Icons.restart_alt_rounded, size: 20, color: AppColors.muted),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: _restartConversation,
              ),
            ],
          ),
        ),

        // 2. Interactive Multi-Turn Conversation Stream
        Expanded(
          child: ListView.builder(
            controller: _voiceScrollController,
            padding: const EdgeInsets.all(16),
            itemCount: _conversationHistory.length + (_isLoading ? 1 : 0) + (_errorMessage != null ? 1 : 0),
            itemBuilder: (context, index) {
              if (index < _conversationHistory.length) {
                final turn = _conversationHistory[index];
                if (turn.isUser) {
                  // User Speech Bubble (Right-aligned)
                  return Align(
                    alignment: Alignment.centerRight,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 14, left: 48),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [AppColors.primary, Color(0xFF1E3A8A)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(16),
                          topRight: Radius.circular(16),
                          bottomLeft: Radius.circular(16),
                          bottomRight: Radius.circular(4),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primary.withValues(alpha: 0.18),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text(
                                'You',
                                style: TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(width: 4),
                              const Icon(Icons.mic_rounded, color: Colors.white70, size: 13),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            turn.text,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14.5,
                              fontWeight: FontWeight.w500,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ).animate().fadeIn(duration: 200.ms).slideY(begin: 0.05),
                  );
                } else {
                  // Counselor Assistant Bubble (Left-aligned)
                  return Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 18, right: 32),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(4),
                          topRight: Radius.circular(16),
                          bottomLeft: Radius.circular(16),
                          bottomRight: Radius.circular(16),
                        ),
                        border: Border.all(color: AppColors.line),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.04),
                            blurRadius: 12,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Header: Avatar, Domain, Engine Badge, Audio button
                          Row(
                            children: [
                              Container(
                                width: 34,
                                height: 34,
                                decoration: BoxDecoration(
                                  color: AppColors.primary,
                                  borderRadius: BorderRadius.circular(17),
                                ),
                                child: const Icon(Icons.support_agent_rounded, color: Colors.white, size: 19),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '${turn.domain ?? 'University'} Ordinance Guidance',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                        color: AppColors.primary,
                                      ),
                                    ),
                                    if (turn.engine != null)
                                      Row(
                                        children: [
                                          Icon(
                                            turn.engine!.contains('Ollama') ? Icons.memory_rounded : Icons.auto_awesome,
                                            size: 11,
                                            color: turn.engine!.contains('Ollama')
                                                ? Colors.green.shade700
                                                : Colors.purple.shade700,
                                          ),
                                          const SizedBox(width: 3),
                                          Text(
                                            turn.engine!,
                                            style: TextStyle(
                                              fontSize: 10.5,
                                              color: turn.engine!.contains('Ollama')
                                                  ? Colors.green.shade800
                                                  : Colors.purple.shade700,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                        ],
                                      ),
                                  ],
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.volume_up_rounded, color: AppColors.primary, size: 21),
                                tooltip: 'Listen to Spoken Guidance (TTS)',
                                onPressed: () => _speakGuidance(turn.speechText ?? turn.text),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          FormattedMarkdownText(
                            text: turn.text,
                            isUser: false,
                            fontSize: 14,
                            customTextColor: AppColors.ink,
                          ),
                          // Interactive Disambiguation Chips (Cross-Question Options)
                          if (turn.clarificationOptions.isNotEmpty) ...[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF0FDF4),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: const Color(0xFF86EFAC)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Row(
                                    children: [
                                      Icon(Icons.help_outline_rounded, size: 16, color: Color(0xFF15803D)),
                                      SizedBox(width: 6),
                                      Text(
                                        'Please select your purpose to proceed:',
                                        style: TextStyle(
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.bold,
                                          color: Color(0xFF15803D),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 10),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: turn.clarificationOptions.map<Widget>((opt) {
                                      final optMap = opt is Map ? opt : {'label': opt.toString(), 'value': opt.toString()};
                                      final label = optMap['label']?.toString() ?? opt.toString();
                                      final value = optMap['value']?.toString() ?? label;
                                      return ActionChip(
                                        backgroundColor: Colors.white,
                                        side: const BorderSide(color: Color(0xFF16A34A), width: 1.2),
                                        elevation: 1,
                                        label: Text(
                                          label,
                                          style: const TextStyle(
                                            color: Color(0xFF15803D),
                                            fontWeight: FontWeight.bold,
                                            fontSize: 12.5,
                                          ),
                                        ),
                                        onPressed: () {
                                          _askPolicy(value, speak: true);
                                        },
                                      );
                                    }).toList(),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          // Screen Instruction if present
                          if (turn.screenInstruction != null) ...[
                            const SizedBox(height: 10),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: AppColors.primarySoft,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: AppColors.primary.withValues(alpha: 0.15)),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.touch_app_rounded, size: 14, color: AppColors.primary),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      turn.screenInstruction!,
                                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.primary),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          // Recommended Action Navigation Button
                          if (turn.recommendedAction != null) ...[
                            const SizedBox(height: 14),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                onPressed: () {
                                  final url = turn.actionUrl ?? (isStaff ? '/staff' : '/forms');
                                  Navigator.of(context).pop();
                                  if (widget.currentRoute != url) {
                                    context.push(url);
                                  }
                                },
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: AppColors.primary,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 10),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                                icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                                label: Text(
                                  turn.recommendedAction!,
                                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                              ),
                            ),
                          ],
                          // Citations (Legal Ordinances)
                          if (turn.citations.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            const Row(
                              children: [
                                Icon(Icons.menu_book_rounded, size: 14, color: AppColors.muted),
                                SizedBox(width: 6),
                                Text(
                                  'Official Legal Citations (Sub-5ms FTS5 Inverted Index)',
                                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5, color: AppColors.muted),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            ...turn.citations.map((c) {
                              final clause = c is Map ? Map<String, dynamic>.from(c) : <String, dynamic>{};
                              final code = clause['clause_code'] ?? 'ORD';
                              final title = clause['title'] ?? 'University Regulation';
                              final content = clause['content'] ?? '';

                              return Container(
                                margin: const EdgeInsets.only(bottom: 6),
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: Colors.grey.shade50,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Colors.grey.shade200),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: AppColors.primary.withValues(alpha: 0.1),
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            code.toString(),
                                            style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: AppColors.primary),
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Expanded(
                                          child: Text(
                                            title.toString(),
                                            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      content.toString(),
                                      style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700, height: 1.35),
                                    ),
                                  ],
                                ),
                              );
                            }),
                          ],
                        ],
                      ),
                    ).animate().fadeIn(duration: 250.ms).slideY(begin: 0.05),
                  );
                }
              }

              // Loading State Shimmer Card
              if (_isLoading && index == _conversationHistory.length) {
                return Container(
                  margin: const EdgeInsets.only(bottom: 14, right: 40),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.line),
                  ),
                  child: Row(
                    children: [
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _selectedLanguage == 'hi-IN'
                                  ? 'ओलामा (Llama 3.2) से परामर्श तैयार हो रहा है...'
                                  : 'Ollama (Llama 3.2) is synthesizing guidance...',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                            Text(
                              'Verified against University FTS5 Ordinance Knowledge Base',
                              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ).animate().fadeIn();
              }

              // Error State Banner
              if (_errorMessage != null) {
                return Container(
                  margin: const EdgeInsets.only(bottom: 14),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline_rounded, color: Colors.redAccent, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent, fontSize: 12.5)),
                      ),
                    ],
                  ),
                );
              }

              return const SizedBox.shrink();
            },
          ),
        ),

        // 3. Bottom Tray: Quick Prompt Chips + Audio/Text Input Bar
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: const BoxDecoration(
            color: Colors.white,
            border: Border(top: BorderSide(color: AppColors.line)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Quick Prompt Chips
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: quickPrompts.map((p) {
                    return Padding(
                      padding: const EdgeInsets.only(right: 8, bottom: 8),
                      child: ActionChip(
                        backgroundColor: AppColors.panel,
                        side: const BorderSide(color: AppColors.line),
                        avatar: const Icon(Icons.chat_bubble_outline_rounded, size: 13, color: AppColors.primary),
                        label: Text(p['label']!, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600)),
                        onPressed: () => _askPolicy(p['q']!, speak: true),
                      ),
                    );
                  }).toList(),
                ),
              ),

              // Voice push-to-talk & Text Input row
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _queryController,
                      decoration: InputDecoration(
                        hintText: _isListening
                            ? (_selectedLanguage == 'hi-IN' ? 'सुन रहे हैं... बोलिए...' : 'Listening... Speak now...')
                            : (_selectedLanguage == 'hi-IN'
                                ? 'प्रश्न पूछें या माइक दबाएं...'
                                : 'Ask counselor or tap mic to speak...'),
                        hintStyle: TextStyle(fontSize: 13.5, color: _isListening ? Colors.redAccent : Colors.grey.shade500),
                        isDense: true,
                        filled: true,
                        fillColor: AppColors.panel,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: _isListening ? Colors.redAccent : AppColors.line),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: _isListening ? Colors.redAccent : AppColors.line),
                        ),
                      ),
                      onSubmitted: (text) {
                        if (text.trim().isNotEmpty) {
                          _askPolicy(text.trim(), speak: true);
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 6),
                  // Push to Talk Mic Button
                  IconButton.filled(
                    tooltip: _isListening ? 'Stop Listening' : 'Push to Talk (Microphone)',
                    style: IconButton.styleFrom(
                      backgroundColor: _isListening ? Colors.redAccent : AppColors.teal,
                      foregroundColor: Colors.white,
                    ),
                    icon: Icon(_isListening ? Icons.graphic_eq_rounded : Icons.mic_rounded, size: 20),
                    onPressed: _toggleVoice,
                  ),
                  const SizedBox(width: 4),
                  // Stop TTS / Stop speaking
                  stopButton,
                  const SizedBox(width: 4),
                  // Send Text Button
                  IconButton.filled(
                    tooltip: 'Send text query',
                    style: IconButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                    ),
                    icon: const Icon(Icons.send_rounded, size: 18),
                    onPressed: () {
                      final text = _queryController.text.trim();
                      if (text.isNotEmpty) {
                        _askPolicy(text, speak: true);
                      }
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLanguageSelectionPrompt(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isMobile = screenWidth < 600;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 620),
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 20,
                offset: const Offset(0, 6),
              ),
            ],
            border: Border.all(color: AppColors.line),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Avatar & Header
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.primary, AppColors.teal],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: 0.25),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Icon(Icons.record_voice_over_rounded, color: Colors.white, size: 32),
              ),
              const SizedBox(height: 16),
              const Text(
                '👋 Welcome to UniAssist',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.ink),
              ),
              const SizedBox(height: 4),
              const Text(
                'AI Digital Campus & Policy Counselor',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.primary),
              ),
              const SizedBox(height: 8),
              Text(
                'Please choose your preferred language to begin voice counseling.\nशुरू करने के लिए अपनी पसंदीदा भाषा चुनें:',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, height: 1.4, color: Colors.grey.shade700),
              ),
              const SizedBox(height: 24),

              // Language Choice Cards
              if (isMobile)
                Column(
                  children: [
                    _buildLanguageCard(
                      flag: '🇬🇧',
                      title: 'English',
                      subtitle: 'Continue in English',
                      badgeText: '✨ Voice AI & Policy Guidance',
                      buttonText: 'Select English ➔',
                      isAccent: false,
                      onTap: () => _selectLanguageAndGreet('en-IN'),
                    ),
                    const SizedBox(height: 14),
                    _buildLanguageCard(
                      flag: '🇮🇳',
                      title: 'हिन्दी',
                      subtitle: 'हिंदी में आगे बढ़ें',
                      badgeText: '✨ शुद्ध हिंदी उच्चारण और परामर्श',
                      buttonText: 'हिंदी चुनें ➔',
                      isAccent: true,
                      onTap: () => _selectLanguageAndGreet('hi-IN'),
                    ),
                  ],
                )
              else
                Row(
                  children: [
                    Expanded(
                      child: _buildLanguageCard(
                        flag: '🇬🇧',
                        title: 'English',
                        subtitle: 'Continue in English',
                        badgeText: '✨ Voice AI & Policy Guidance',
                        buttonText: 'Select English ➔',
                        isAccent: false,
                        onTap: () => _selectLanguageAndGreet('en-IN'),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: _buildLanguageCard(
                        flag: '🇮🇳',
                        title: 'हिन्दी',
                        subtitle: 'हिंदी में आगे बढ़ें',
                        badgeText: '✨ शुद्ध हिंदी उच्चारण और परामर्श',
                        buttonText: 'हिंदी चुनें ➔',
                        isAccent: true,
                        onTap: () => _selectLanguageAndGreet('hi-IN'),
                      ),
                    ),
                  ],
                ),

              const SizedBox(height: 18),
              // Hinglish link
              InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: () => _selectLanguageAndGreet('hi-Latn'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('🔤', style: TextStyle(fontSize: 14)),
                      const SizedBox(width: 6),
                      Text(
                        'Prefer Hinglish? हिंग्लिश में बात करें (Conversational) ➔',
                        style: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w600,
                          color: Colors.blueGrey.shade700,
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(duration: 250.ms).scale(begin: const Offset(0.97, 0.97));
  }

  Widget _buildLanguageCard({
    required String flag,
    required String title,
    required String subtitle,
    required String badgeText,
    required String buttonText,
    required bool isAccent,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: isAccent ? Colors.amber.shade50.withValues(alpha: 0.4) : AppColors.primarySoft,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isAccent ? Colors.amber.shade400 : AppColors.primary.withValues(alpha: 0.35),
            width: 1.5,
          ),
        ),
        child: Column(
          children: [
            Text(flag, style: const TextStyle(fontSize: 38)),
            const SizedBox(height: 8),
            Text(
              title,
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w800,
                color: isAccent ? Colors.deepOrange.shade900 : AppColors.primary,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey.shade700),
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: Colors.black.withValues(alpha: 0.08)),
              ),
              child: Text(
                badgeText,
                style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: Colors.grey.shade800),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: isAccent ? Colors.deepOrange.shade800 : AppColors.primary,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Text(
                  buttonText,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
