// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use
import 'dart:async';
import 'dart:js' as js;
import 'package:flutter/foundation.dart';

/// Service providing real audible speech synthesis via Web SpeechSynthesis API.
class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;
  TtsService._internal();

  bool _isSpeaking = false;
  bool get isSpeaking => _isSpeaking;

  final _speakStateController = StreamController<bool>.broadcast();
  Stream<bool> get onSpeakingStateChanged => _speakStateController.stream;

  /// Speaks the provided [text] out loud through the device audio.
  void speak(String text, {String lang = 'en-IN', double rate = 1.0, double pitch = 1.0, VoidCallback? onComplete}) {
    if (!kIsWeb) {
      debugPrint('[TtsService] Non-web platform: $text');
      onComplete?.call();
      return;
    }

    try {
      // Cancel previous utterances
      stop();

      final cleanText = text
          .replaceAll(RegExp(r'[\*\_#`>]'), '') // strip markdown
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();

      if (cleanText.isEmpty) return;

      _isSpeaking = true;
      _speakStateController.add(true);

      // Invoke window.speechSynthesis via JS context
      js.context.callMethod('eval', [
        """
        (function(text, lang, rate, pitch) {
          if (!('speechSynthesis' in window)) return;
          window.speechSynthesis.cancel();
          if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
          }

          var doSpeak = function() {
            var utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = lang || 'en-IN';
            utterance.rate = rate || 1.0;
            utterance.pitch = pitch || 1.0;
            
            var voices = window.speechSynthesis.getVoices() || [];
            var targetLang = (lang || 'en-IN').toLowerCase();
            var preferred = null;

            if (targetLang.startsWith('hi')) {
              preferred = voices.find(function(v) {
                var vl = (v.lang || '').toLowerCase().replace('_', '-');
                var vn = (v.name || '').toLowerCase();
                return vl === 'hi-in' || vl.startsWith('hi') ||
                       vn.includes('hindi') || vn.includes('हिन्दी') ||
                       vn.includes('swara') || vn.includes('madhur') ||
                       vn.includes('kalpana') || vn.includes('hemant') ||
                       vn.includes('google hindi');
              });
            } else if (targetLang === 'en-in' || targetLang === 'hi-latn') {
              preferred = voices.find(function(v) {
                var vl = (v.lang || '').toLowerCase().replace('_', '-');
                var vn = (v.name || '').toLowerCase();
                return vl === 'en-in' || vl.startsWith('en-in') ||
                       vn.includes('india') || vn.includes('neerja') ||
                       vn.includes('prabhat') || vn.includes('ravi');
              });
            }

            if (!preferred && !targetLang.startsWith('hi')) {
              preferred = voices.find(function(v) {
                return (v.lang || '').toLowerCase().startsWith(targetLang.split('-')[0]);
              }) || voices.find(function(v) {
                return (v.lang || '').toLowerCase().startsWith('en');
              });
            }

            if (preferred) utterance.voice = preferred;

            utterance.onend = function() {
              if (window._onUniAssistTtsEnd) window._onUniAssistTtsEnd();
            };
            utterance.onerror = function(e) {
              console.warn('TTS error:', e);
              if (window._onUniAssistTtsEnd) window._onUniAssistTtsEnd();
            };

            window.speechSynthesis.resume();
            window.speechSynthesis.speak(utterance);
          };

          if (window.speechSynthesis.getVoices().length === 0) {
            window.speechSynthesis.onvoiceschanged = function() {
              window.speechSynthesis.onvoiceschanged = null;
              doSpeak();
            };
            // Fallback timeout in case onvoiceschanged does not fire
            setTimeout(doSpeak, 100);
          } else {
            doSpeak();
          }
        })(${_escapeJsString(cleanText)}, '$lang', $rate, $pitch)
        """
      ]);

      // Attach JS callback handler
      js.context['_onUniAssistTtsEnd'] = () {
        _isSpeaking = false;
        _speakStateController.add(false);
        onComplete?.call();
      };
    } catch (e) {
      debugPrint('[TtsService] Error speaking: $e');
      _isSpeaking = false;
      _speakStateController.add(false);
      onComplete?.call();
    }
  }

  /// Immediately stop any speaking audio.
  void stop() {
    if (!kIsWeb) return;
    try {
      js.context.callMethod('eval', [
        "if ('speechSynthesis' in window) window.speechSynthesis.cancel();"
      ]);
      _isSpeaking = false;
      _speakStateController.add(false);
    } catch (e) {
      debugPrint('[TtsService] Error stopping speech: $e');
    }
  }

  static String _escapeJsString(String s) {
    final escaped = s
        .replaceAll(r'\', r'\\')
        .replaceAll("'", r"\'")
        .replaceAll('"', r'\"')
        .replaceAll('\n', ' ')
        .replaceAll('\r', '');
    return "'$escaped'";
  }
}
