/// Non-web fallback stub for WebVoiceBridge.
class WebVoiceBridge {
  static bool get isSupported => false;

  static void startListening({
    String lang = 'en-IN',
    required void Function(String text) onResult,
    required void Function(String error) onError,
  }) {}

  static void stopListening() {}

  static void speak(
    String text, {
    String lang = 'en-IN',
    double rate = 0.95,
    void Function()? onComplete,
  }) {}

  static void stopSpeaking() {}
}
