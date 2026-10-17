import 'package:flutter/material.dart';

import '../theme/kiosk_theme.dart';

/// Formats plain text containing basic markdown bold (`**text**`),
/// bullet points (`•`, `- `, `* `), and numbered lists into clean,
/// beautifully styled Flutter RichText without displaying raw markdown asterisks.
class FormattedMarkdownText extends StatelessWidget {
  const FormattedMarkdownText({
    super.key,
    required this.text,
    this.isUser = false,
    this.fontSize = 15.0,
    this.customTextColor,
  });

  final String text;
  final bool isUser;
  final double fontSize;
  final Color? customTextColor;

  @override
  Widget build(BuildContext context) {
    final baseColor = customTextColor ?? (isUser ? Colors.white : AppColors.ink);
    final lines = text.split('\n');
    final children = <Widget>[];

    for (int i = 0; i < lines.length; i++) {
      final line = lines[i];
      if (line.trim().isEmpty) {
        children.add(const SizedBox(height: 6));
        continue;
      }

      final trimmed = line.trimLeft();
      final isBullet = trimmed.startsWith('•') ||
          trimmed.startsWith('- ') ||
          trimmed.startsWith('* ');

      // Clean leading bullet indicator if needed
      String contentLine = line;
      String bulletPrefix = '';
      if (isBullet) {
        if (trimmed.startsWith('•')) {
          bulletPrefix = '• ';
          contentLine = trimmed.substring(1).trimLeft();
        } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          bulletPrefix = '• ';
          contentLine = trimmed.substring(2).trimLeft();
        }
      }

      final spans = _parseMarkdownSpans(contentLine, baseColor);

      if (isBullet) {
        children.add(
          Padding(
            padding: const EdgeInsets.only(left: 6, bottom: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  bulletPrefix,
                  style: TextStyle(
                    color: isUser ? Colors.white70 : AppColors.primary,
                    fontWeight: FontWeight.bold,
                    fontSize: fontSize,
                    height: 1.42,
                  ),
                ),
                Expanded(
                  child: RichText(
                    text: TextSpan(
                      style: TextStyle(
                        color: baseColor,
                        fontSize: fontSize,
                        height: 1.42,
                        fontFamily: 'Inter',
                      ),
                      children: spans,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      } else {
        children.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: RichText(
              text: TextSpan(
                style: TextStyle(
                  color: baseColor,
                  fontSize: fontSize,
                  height: 1.42,
                  fontFamily: 'Inter',
                ),
                children: spans,
              ),
            ),
          ),
        );
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: children,
    );
  }

  List<InlineSpan> _parseMarkdownSpans(String line, Color baseColor) {
    final spans = <InlineSpan>[];
    // Match bold patterns: **content**
    final boldRegex = RegExp(r'\*\*(.*?)\*\*');
    int lastEnd = 0;

    for (final match in boldRegex.allMatches(line)) {
      if (match.start > lastEnd) {
        spans.add(TextSpan(
          text: line.substring(lastEnd, match.start),
          style: TextStyle(
            color: baseColor,
            fontWeight: FontWeight.normal,
            fontSize: fontSize,
          ),
        ));
      }

      final boldContent = match.group(1) ?? '';
      spans.add(TextSpan(
        text: boldContent,
        style: TextStyle(
          color: baseColor,
          fontWeight: FontWeight.bold,
          fontSize: fontSize,
        ),
      ));
      lastEnd = match.end;
    }

    if (lastEnd < line.length) {
      spans.add(TextSpan(
        text: line.substring(lastEnd),
        style: TextStyle(
          color: baseColor,
          fontWeight: FontWeight.normal,
          fontSize: fontSize,
        ),
      ));
    }

    return spans;
  }
}
