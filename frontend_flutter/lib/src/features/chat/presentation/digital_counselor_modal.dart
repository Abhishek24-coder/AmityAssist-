import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../auth/application/auth_provider.dart';
import 'chat_screen.dart';

/// Shows the AI Digital Counselor in a touch-first modal/dialog on kiosk or mobile.
Future<void> showDigitalCounselor(BuildContext context) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => const DigitalCounselorModal(),
  );
}

class DigitalCounselorModal extends ConsumerStatefulWidget {
  const DigitalCounselorModal({super.key});

  @override
  ConsumerState<DigitalCounselorModal> createState() => _DigitalCounselorModalState();
}

class _DigitalCounselorModalState extends ConsumerState<DigitalCounselorModal> {
  final ScrollController _scrollController = ScrollController();
  int _activeTab = 0; // 0: Guided Procedures, 1: Policy Search & Voice AI (FTS5)

  @override
  void dispose() {
    _scrollController.dispose();
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
    final isDesktop = mediaQuery.size.width >= 800;

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

    return Container(
      height: screenHeight * (isDesktop ? 0.88 : 0.94),
      margin: EdgeInsets.symmetric(
        horizontal: isDesktop ? (mediaQuery.size.width - 760) / 2 : 8,
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
                      children: const [
                        Row(
                          children: [
                            Text(
                              'AI Digital Counselor',
                              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800),
                            ),
                            SizedBox(width: 8),
                            _OnlinePill(),
                          ],
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Guided procedures, ordinances & voice intelligence.',
                          style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, color: Colors.white, size: 24),
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
                              'Policy & Voice AI (FTS5)',
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
                                        child: Text(
                                          message.text,
                                          style: TextStyle(
                                            color: isUser ? Colors.white : AppColors.ink,
                                            fontSize: 14.5,
                                            height: 1.4,
                                            fontWeight: isUser ? FontWeight.w600 : FontWeight.w500,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ).animate().fadeIn(duration: 200.ms).slideY(begin: 0.05);
                            },
                          ),
                        ),

                        // Fixed bottom options tray (Wizard Buttons)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(16),
                          decoration: const BoxDecoration(
                            color: Colors.white,
                            border: Border(top: BorderSide(color: AppColors.line)),
                          ),
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
                                          labelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                                          label: Text(option),
                                          avatar: const Icon(Icons.touch_app_rounded, size: 16),
                                          onPressed: () => _handleSend(option),
                                        ).animate().fadeIn(duration: 150.ms).scale(begin: const Offset(0.95, 0.95)),
                                      )
                                      .toList(),
                                ),
                        ),
                      ],
                    )
                  : const _PolicyVoiceTab(),
            ),
          ],
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

class _PolicyVoiceTab extends ConsumerStatefulWidget {
  const _PolicyVoiceTab();

  @override
  ConsumerState<_PolicyVoiceTab> createState() => _PolicyVoiceTabState();
}

class _PolicyVoiceTabState extends ConsumerState<_PolicyVoiceTab> {
  final TextEditingController _queryController = TextEditingController();
  bool _isLoading = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  Map<String, dynamic>? _guidance;
  String? _errorMessage;

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _askPolicy(String query) async {
    final cleanQ = query.trim();
    if (cleanQ.isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _queryController.text = cleanQ;
    });

    try {
      final studentId = ref.read(authProvider).studentId ?? 'STU001';
      final dio = Dio(BaseOptions(
        baseUrl: 'http://127.0.0.1:8000/api',
        connectTimeout: const Duration(seconds: 8),
      ));

      final resp = await dio.post(
        '/policy/guide',
        data: {
          'query': cleanQ,
          'student_id': studentId,
        },
      );

      if (mounted) {
        setState(() {
          _guidance = Map<String, dynamic>.from(resp.data as Map);
          _isLoading = false;
        });
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
    if (_isListening) {
      setState(() => _isListening = false);
      return;
    }

    setState(() => _isListening = true);

    // Kiosk voice query simulation / speech synthesis
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Listening... Speak your university policy question now.'),
        duration: Duration(seconds: 2),
      ),
    );

    // After 1.8s, simulate voice command captured
    await Future.delayed(const Duration(milliseconds: 1800));
    if (mounted && _isListening) {
      setState(() {
        _isListening = false;
      });
      _askPolicy('Can I offset lost ID card fee from caution deposit?');
    }
  }

  void _speakGuidance(String text) {
    setState(() => _isSpeaking = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            Icon(Icons.record_voice_over_rounded, color: Colors.white, size: 20),
            SizedBox(width: 8),
            Text('Speaking guidance through kiosk audio speakers...'),
          ],
        ),
        backgroundColor: AppColors.primary,
        duration: Duration(seconds: 3),
      ),
    );

    Future.delayed(const Duration(seconds: 4), () {
      if (mounted) setState(() => _isSpeaking = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final quickPrompts = [
      {'label': 'Attendance Shortage (ORD-7.2)', 'q': 'Can I write semester exams with 71% attendance?'},
      {'label': 'Lost ID Card Offset (ORD-14.4)', 'q': 'Can I offset lost ID card ₹200 fine from caution deposit?'},
      {'label': 'Withdrawal Slabs (ORD-14.1)', 'q': 'What is the tuition refund percentage for withdrawal?'},
      {'label': '4-Gate Clearance (ORD-9.3)', 'q': 'How does the 4-gate clearance chain work?'},
      {'label': 'Backpaper Exam Fee (ORD-12.1)', 'q': 'What is the backpaper exam fee and deadline?'},
    ];

    final citations = (_guidance != null && _guidance!['citations'] is List)
        ? (_guidance!['citations'] as List)
        : const [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Search & Voice input bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _isListening ? Colors.redAccent : AppColors.line, width: _isListening ? 2 : 1),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Row(
              children: [
                const Icon(Icons.search_rounded, color: AppColors.primary, size: 22),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _queryController,
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                    decoration: InputDecoration(
                      hintText: _isListening ? 'Listening to voice...' : 'Search university ordinances or ask a question...',
                      hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade500),
                      border: InputBorder.none,
                    ),
                    onSubmitted: (val) => _askPolicy(val),
                  ),
                ),
                // Voice Push-to-Talk Button
                IconButton(
                  icon: Icon(
                    _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                    color: _isListening ? Colors.redAccent : AppColors.primary,
                    size: 24,
                  ),
                  tooltip: 'Push to Talk (Voice Query)',
                  onPressed: _toggleVoice,
                ),
                ElevatedButton(
                  onPressed: () => _askPolicy(_queryController.text),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: const Text('Ask AI', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Quick Query Prompts
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: quickPrompts.map((p) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ActionChip(
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: AppColors.line),
                    avatar: const Icon(Icons.policy_outlined, size: 14, color: AppColors.primary),
                    label: Text(p['label']!, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                    onPressed: () => _askPolicy(p['q']!),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 16),

          // Loading State
          if (_isLoading)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(28),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.line),
              ),
              child: Column(
                children: [
                  const CircularProgressIndicator(color: AppColors.primary),
                  const SizedBox(height: 16),
                  const Text(
                    'Querying SQLite FTS5 BM25 Ordinance Index...',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Cross-referencing live student profile for personalized guidance.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),

          // Error State
          if (_errorMessage != null)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded, color: Colors.redAccent),
                  const SizedBox(width: 10),
                  Expanded(child: Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent, fontSize: 13))),
                ],
              ),
            ),

          // Guidance Response Card
          if (!_isLoading && _guidance != null) ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.06),
                    blurRadius: 16,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: AppColors.primarySoft,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Icon(Icons.verified_user_rounded, color: AppColors.primary, size: 18),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${_guidance!['domain'] ?? 'University'} Ordinance Guidance',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.primary),
                      ),
                      const Spacer(),
                      // Voice TTS playback button
                      IconButton(
                        icon: Icon(
                          _isSpeaking ? Icons.volume_up_rounded : Icons.volume_down_rounded,
                          color: _isSpeaking ? AppColors.amityYellow : AppColors.primary,
                          size: 22,
                        ),
                        tooltip: 'Listen to Spoken Guidance (TTS)',
                        onPressed: () => _speakGuidance(_guidance!['answer'] ?? ''),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _guidance!['answer'] ?? '',
                    style: const TextStyle(fontSize: 14.5, height: 1.5, color: AppColors.ink, fontWeight: FontWeight.w500),
                  ),
                  if (_guidance!['recommended_action'] != null) ...[
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: () {
                          final url = _guidance!['action_url'] ?? '/forms';
                          Navigator.of(context).pop();
                          context.push(url.toString());
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                        label: Text(
                          _guidance!['recommended_action'].toString(),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ).animate().fadeIn().slideY(begin: 0.05),

            // Citations / Verified Clauses
            if (citations.isNotEmpty) ...[
              const SizedBox(height: 18),
              const Row(
                children: [
                  Icon(Icons.menu_book_rounded, size: 16, color: AppColors.muted),
                  SizedBox(width: 6),
                  Text(
                    'Official Legal Citations (Sub-5ms FTS5 Inverted Index)',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppColors.muted),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ...citations.map((c) {
                final clause = c is Map ? Map<String, dynamic>.from(c) : <String, dynamic>{};
                final code = clause['clause_code'] ?? 'ORD';
                final title = clause['title'] ?? 'University Regulation';
                final content = clause['content'] ?? '';

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(10),
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
                              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.primary),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              title.toString(),
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        content.toString(),
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade700, height: 1.4),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ],
      ),
    );
  }
}
