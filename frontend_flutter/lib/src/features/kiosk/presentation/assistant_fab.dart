import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../chat/presentation/digital_counselor_modal.dart';
import '../../../core/theme/kiosk_theme.dart';
import '../../../core/services/page_context_service.dart';

class AssistantFab extends ConsumerWidget {
  const AssistantFab({super.key, this.currentRoute});

  final String? currentRoute;

  void _showModeSelection(BuildContext context, WidgetRef ref) {
    if (currentRoute != null) {
      ref.read(pageContextProvider.notifier).setRoute(currentRoute!);
    }
    showDialog(
      context: context,
      builder: (context) {
        return Dialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.support_agent_rounded, size: 56, color: AppColors.primary),
                const SizedBox(height: 16),
                const Text(
                  'How would you like to communicate?',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.ink),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Expanded(
                      child: _ModeButton(
                        icon: Icons.mic_rounded,
                        label: 'Voice Conversation',
                        color: AppColors.teal,
                        onTap: () {
                          Navigator.pop(context);
                          if (currentRoute != null) {
                            ref.read(pageContextProvider.notifier).setRoute(currentRoute!);
                          }
                          showDigitalCounselor(
                            context,
                            initialTab: 1,
                            autoStartVoice: false,
                            currentRoute: currentRoute,
                          );
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _ModeButton(
                        icon: Icons.chat_bubble_rounded,
                        label: 'Chat',
                        color: AppColors.primary,
                        onTap: () {
                          Navigator.pop(context);
                          if (currentRoute != null) {
                            ref.read(pageContextProvider.notifier).setRoute(currentRoute!);
                          }
                          showDigitalCounselor(
                            context,
                            initialTab: 0,
                            currentRoute: currentRoute,
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FloatingActionButton.extended(
      onPressed: () => _showModeSelection(context, ref),
      backgroundColor: AppColors.primary,
      icon: const Icon(Icons.support_agent_rounded, color: Colors.white, size: 28),
      label: const Text(
        'Ask UniAssist',
        style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _ModeButton extends StatelessWidget {
  const _ModeButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          border: Border.all(color: color.withValues(alpha: 0.3), width: 2),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 40, color: color),
            const SizedBox(height: 12),
            Text(
              label,
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: color),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
