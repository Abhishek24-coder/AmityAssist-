import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/kiosk_theme.dart';
import '../../../core/widgets/uniassist_logo.dart';
import 'assistant_fab.dart';

class KioskWelcomeScreen extends ConsumerStatefulWidget {
  const KioskWelcomeScreen({super.key});

  @override
  ConsumerState<KioskWelcomeScreen> createState() => _KioskWelcomeScreenState();
}

class _KioskWelcomeScreenState extends ConsumerState<KioskWelcomeScreen> {
  late Timer _clockTimer;
  DateTime _now = DateTime.now();
  bool _showSplash = true;

  @override
  void initState() {
    super.initState();
    _clockTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });

    // Auto-dismiss splash screen smoothly after handwriting animation finishes (3.8s)
    Future.delayed(const Duration(milliseconds: 3800), () {
      if (mounted) {
        setState(() => _showSplash = false);
      }
    });
  }

  @override
  void dispose() {
    _clockTimer.cancel();
    super.dispose();
  }

  String _formatTime(DateTime dt) {
    final hour = dt.hour.toString().padLeft(2, '0');
    final minute = dt.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  String _formatDate(DateTime dt) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return '${days[dt.weekday - 1]}, ${months[dt.month - 1]} ${dt.day}, ${dt.year}';
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 800;

    return Stack(
      children: [
        Scaffold(
          floatingActionButton: const AssistantFab(),
          floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
          body: SafeArea(
            child: Column(
              children: [
                // Top Kiosk Header Bar
                _KioskTopBar(
                  timeStr: _formatTime(_now),
                  dateStr: _formatDate(_now),
                ),

                // Main Content Body
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 960),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            // Hero Title
                            Text(
                              'Welcome to UniAssist',
                              style: TextStyle(
                                fontSize: isCompact ? 32 : 46,
                                fontWeight: FontWeight.w900,
                                color: AppColors.ink,
                                letterSpacing: -0.5,
                                decoration: TextDecoration.none,
                              ),
                              textAlign: TextAlign.center,
                            ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1),
                            const SizedBox(height: 12),
                            Text(
                              'Choose how you would like to continue',
                              style: TextStyle(
                                fontSize: isCompact ? 18 : 22,
                                fontWeight: FontWeight.w500,
                                color: AppColors.muted,
                                decoration: TextDecoration.none,
                              ),
                              textAlign: TextAlign.center,
                            ).animate(delay: 200.ms).fadeIn(duration: 400.ms),

                            SizedBox(height: isCompact ? 40 : 54),

                            // Two Large Touch Kiosk Cards
                            if (isCompact)
                              Column(
                                children: [
                                  _KioskCard(
                                    title: 'PUBLIC SERVICES',
                                    subtitle: '31 Official Forms, FAQs & Verification',
                                    icon: Icons.account_balance_rounded,
                                    iconColor: const Color(0xFF0D9488),
                                    onTap: () => context.go('/services'),
                                  ).animate(delay: 400.ms).fadeIn().slideY(begin: 0.1),
                                  const SizedBox(height: 24),
                                  _KioskCard(
                                    title: 'STUDENT / STAFF',
                                    subtitle: 'Clearance Cockpit, Fee Offsets & Portal',
                                    icon: Icons.badge_outlined,
                                    iconColor: const Color(0xFF2563EB),
                                    onTap: () => context.go('/login'),
                                  ).animate(delay: 500.ms).fadeIn().slideY(begin: 0.1),
                                ],
                              )
                            else
                              Row(
                                children: [
                                  Expanded(
                                    child: _KioskCard(
                                      title: 'PUBLIC SERVICES',
                                      subtitle: '31 Official Forms, FAQs & Verification',
                                      icon: Icons.account_balance_rounded,
                                      iconColor: const Color(0xFF0D9488),
                                      onTap: () => context.go('/services'),
                                    ).animate(delay: 400.ms).fadeIn().slideX(begin: -0.05),
                                  ),
                                  const SizedBox(width: 32),
                                  Expanded(
                                    child: _KioskCard(
                                      title: 'STUDENT / STAFF',
                                      subtitle: 'Clearance Cockpit, Fee Offsets & Portal',
                                      icon: Icons.badge_outlined,
                                      iconColor: const Color(0xFF2563EB),
                                      onTap: () => context.go('/login'),
                                    ).animate(delay: 500.ms).fadeIn().slideX(begin: 0.05),
                                  ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // Kiosk Footer Info Bar
                const _KioskBottomFooter(),
              ],
            ),
          ),
        ),

        // Modern Splash Screen Overlay with Assistant Avatar & Handwriting Typewriter Animation
        if (_showSplash)
          Positioned.fill(
            child: Material(
              color: Colors.white,
              child: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Color(0xFFF8FAFC),
                      Colors.white,
                      Color(0xFFEFF6FF),
                    ],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                ),
                child: Center(
                  child: SingleChildScrollView(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          // 1. Beautiful Digital Assistant Visual Avatar
                          const _AssistantAvatarVisual(),

                          const SizedBox(height: 36),

                          // 2. Handwriting Typewriter Main Title (NO yellow underline!)
                          const _HandwritingTypewriterText(
                            text: 'Welcome to UniAssist',
                            style: TextStyle(
                              fontSize: 34,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF0F172A),
                              letterSpacing: -0.5,
                              decoration: TextDecoration.none,
                            ),
                            startDelay: Duration(milliseconds: 300),
                            speed: Duration(milliseconds: 45),
                          ),

                          const SizedBox(height: 14),

                          // 3. Handwriting Subtitle
                          const _HandwritingTypewriterText(
                            text: 'Your friendly digital guide to everything on campus.',
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w500,
                              color: Color(0xFF475569),
                              letterSpacing: 0.2,
                              decoration: TextDecoration.none,
                            ),
                            startDelay: Duration(milliseconds: 1400),
                            speed: Duration(milliseconds: 28),
                          ),

                          const SizedBox(height: 32),

                          // 4. Subtle Ambient Loading Bar
                          Container(
                            width: 140,
                            height: 3,
                            decoration: BoxDecoration(
                              color: const Color(0xFFE2E8F0),
                              borderRadius: BorderRadius.circular(3),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(3),
                              child: const LinearProgressIndicator(
                                backgroundColor: Color(0xFFE2E8F0),
                                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF3B82F6)),
                              ),
                            ),
                          ).animate(delay: 800.ms).fadeIn(),
                        ],
                      ),
                    ),
                  ),
                ),
              ).animate(delay: 3300.ms).fadeOut(duration: 450.ms),
            ),
          ),
      ],
    );
  }
}

/// A modern, beautiful digital counselor character visual with animated pulse rings.
class _AssistantAvatarVisual extends StatelessWidget {
  const _AssistantAvatarVisual();

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        // Outer glowing pulse ring
        Container(
          width: 150,
          height: 150,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                const Color(0xFF3B82F6).withValues(alpha: 0.25),
                const Color(0xFF6366F1).withValues(alpha: 0.08),
                Colors.transparent,
              ],
            ),
          ),
        ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(
              begin: const Offset(0.9, 0.9),
              end: const Offset(1.15, 1.15),
              duration: 1800.ms,
              curve: Curves.easeInOut,
            ),

        // Middle crisp glass border ring
        Container(
          width: 116,
          height: 116,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(
              colors: [Color(0xFF2563EB), Color(0xFF7C3AED)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF3B82F6).withValues(alpha: 0.35),
                blurRadius: 28,
                offset: const Offset(0, 10),
              ),
            ],
          ),
        ),

        // Inner avatar surface
        Container(
          width: 104,
          height: 104,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.white,
          ),
          child: Center(
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Stylized friendly assistant character face & headset
                const Icon(
                  Icons.support_agent_rounded,
                  size: 64,
                  color: Color(0xFF1E40AF),
                ),
                // Sparkle indicator badge on top right
                Positioned(
                  right: 14,
                  top: 14,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      color: Color(0xFF10B981),
                    ),
                    child: const Icon(
                      Icons.auto_awesome_rounded,
                      size: 10,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    ).animate().fadeIn(duration: 500.ms).scale(duration: 600.ms, curve: Curves.easeOutBack);
  }
}

/// Types text character by character like natural handwriting with a blinking cursor.
class _HandwritingTypewriterText extends StatefulWidget {
  const _HandwritingTypewriterText({
    required this.text,
    required this.style,
    this.startDelay = Duration.zero,
    this.speed = const Duration(milliseconds: 40),
  });

  final String text;
  final TextStyle style;
  final Duration startDelay;
  final Duration speed;

  @override
  State<_HandwritingTypewriterText> createState() => _HandwritingTypewriterTextState();
}

class _HandwritingTypewriterTextState extends State<_HandwritingTypewriterText> {
  String _displayedText = '';
  Timer? _startTimer;
  Timer? _typeTimer;
  int _charIndex = 0;
  bool _showCursor = true;
  Timer? _cursorTimer;

  @override
  void initState() {
    super.initState();
    _startTimer = Timer(widget.startDelay, _startTyping);
    _cursorTimer = Timer.periodic(const Duration(milliseconds: 450), (_) {
      if (mounted) setState(() => _showCursor = !_showCursor);
    });
  }

  void _startTyping() {
    _typeTimer = Timer.periodic(widget.speed, (timer) {
      if (_charIndex < widget.text.length) {
        _charIndex++;
        if (mounted) {
          setState(() {
            _displayedText = widget.text.substring(0, _charIndex);
          });
        }
      } else {
        timer.cancel();
      }
    });
  }

  @override
  void dispose() {
    _startTimer?.cancel();
    _typeTimer?.cancel();
    _cursorTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDone = _displayedText.length == widget.text.length;

    return Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Flexible(
          child: Text(
            _displayedText,
            style: widget.style.copyWith(decoration: TextDecoration.none),
            textAlign: TextAlign.center,
          ),
        ),
        if (!isDone || _showCursor)
          Opacity(
            opacity: _showCursor ? 1.0 : 0.0,
            child: Container(
              margin: const EdgeInsets.only(left: 2),
              width: 3,
              height: (widget.style.fontSize ?? 20) * 0.9,
              decoration: BoxDecoration(
                color: widget.style.color ?? const Color(0xFF2563EB),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
      ],
    );
  }
}

class _KioskTopBar extends StatelessWidget {
  const _KioskTopBar({
    required this.timeStr,
    required this.dateStr,
  });

  final String timeStr;
  final String dateStr;

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isCompact = screenWidth < 850;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 18),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: Color(0xFFE2E8F0))),
      ),
      child: Row(
        children: [
          const UniAssistLogo(size: 36, showWordmark: true),
          const Spacer(),
          if (!isCompact) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.location_on_rounded, size: 16, color: Color(0xFF2563EB)),
                  const SizedBox(width: 8),
                  const Text(
                    'Campus Front Desk Kiosk',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF0F172A),
                      decoration: TextDecoration.none,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Text('•', style: TextStyle(color: Color(0xFF94A3B8), decoration: TextDecoration.none)),
                  const SizedBox(width: 12),
                  Text(
                    '$dateStr  $timeStr',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF64748B),
                      decoration: TextDecoration.none,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _KioskCard extends StatelessWidget {
  const _KioskCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.iconColor,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color iconColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          height: 290,
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFE2E8F0), width: 2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.03),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 90,
                height: 90,
                decoration: BoxDecoration(
                  color: iconColor.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: iconColor, size: 48),
              ),
              const SizedBox(height: 24),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                  color: Color(0xFF0F172A),
                  letterSpacing: 0.5,
                  decoration: TextDecoration.none,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF64748B),
                  decoration: TextDecoration.none,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _KioskBottomFooter extends StatelessWidget {
  const _KioskBottomFooter();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
      ),
      child: Row(
        children: const [
          Icon(Icons.shield_outlined, size: 16, color: Color(0xFF64748B)),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Sessions clear automatically after 5 minutes of inactivity for student privacy.',
              style: TextStyle(
                fontSize: 13,
                color: Color(0xFF64748B),
                fontWeight: FontWeight.w600,
                decoration: TextDecoration.none,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          SizedBox(width: 12),
          Text(
            'UniAssist Self-Service Kiosk v2.0',
            style: TextStyle(
              fontSize: 13,
              color: Color(0xFF334155),
              fontWeight: FontWeight.w800,
              decoration: TextDecoration.none,
            ),
          ),
        ],
      ),
    );
  }
}
