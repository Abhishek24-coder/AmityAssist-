// UniAssist Web Speech API Interop
// Provides high-reliability speech-to-text recognition and text-to-speech audio synthesis.

window.uniassistVoice = {
  recognition: null,
  isListening: false,
  isSpeaking: false,

  isSpeechSupported: function() {
    var hasRecognition = ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
    var hasSynthesis = ('speechSynthesis' in window);
    return hasRecognition && hasSynthesis;
  },

  startListening: function(lang, onResult, onError) {
    try {
      var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {
        if (onError) onError("Speech Recognition not supported in this browser.");
        return;
      }

      // 1. Immediately cancel active TTS playback so Chrome doesn't abort speech recognition
      if ('speechSynthesis' in window) {
        try { window.speechSynthesis.cancel(); } catch (e) {}
      }
      this.isSpeaking = false;

      // 2. Detach handlers from existing recognition before aborting to prevent leaked 'aborted' events
      if (this.recognition) {
        try {
          this.recognition.onstart = null;
          this.recognition.onresult = null;
          this.recognition.onerror = null;
          this.recognition.onend = null;
          this.recognition.abort();
        } catch (e) {}
        this.recognition = null;
      }

      var rec = new SpeechRec();
      rec.lang = lang || 'en-IN';
      rec.continuous = false;
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      var finalTranscript = '';
      var interimTranscript = '';

      rec.onstart = function() {
        window.uniassistVoice.isListening = true;
      };

      rec.onresult = function(event) {
        interimTranscript = '';
        for (var i = 0; i < event.results.length; ++i) {
          var item = event.results[i];
          if (item && item.length > 0) {
            var transcript = item[0].transcript;
            if (item.isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }
        }
      };

      rec.onerror = function(event) {
        window.uniassistVoice.isListening = false;
        var errCode = (event && event.error) ? event.error : "Speech error";

        // Ignore benign lifecycle aborts and silence timeouts
        if (errCode === 'aborted' || errCode === 'no-speech') {
          console.log("[UniAssist Voice] Benign recognition event: " + errCode);
          return;
        }

        if (onError) onError(errCode);
      };

      rec.onend = function() {
        window.uniassistVoice.isListening = false;
        var rawText = (finalTranscript || interimTranscript).trim();
        if (rawText.length > 0) {
          // Guard against immediate duplicate phrase stutter (e.g. "phrasePhrase" or "phrase phrase")
          var textToDispatch = rawText;
          var halfLen = Math.floor(rawText.length / 2);
          if (halfLen >= 4) {
            var firstHalf = rawText.substring(0, halfLen).trim().toLowerCase();
            var secondHalf = rawText.substring(halfLen).trim().toLowerCase();
            if (firstHalf === secondHalf) {
              textToDispatch = rawText.substring(0, halfLen).trim();
            }
          }
          if (onResult) onResult(textToDispatch);
        }
      };

      this.recognition = rec;
      rec.start();
    } catch (err) {
      window.uniassistVoice.isListening = false;
      var errStr = err.message || String(err);
      if (err.name === 'NotAllowedError') {
        errStr = "Microphone permission denied. Please allow microphone in browser.";
      }
      if (onError) onError(errStr);
    }
  },

  stopListening: function() {
    if (this.recognition) {
      try {
        this.recognition.onstart = null;
        this.recognition.onresult = null;
        this.recognition.onerror = null;
        this.recognition.onend = null;
        this.recognition.stop();
      } catch (e) {}
      this.recognition = null;
    }
    this.isListening = false;
  },

  getBestVoice: function(lang) {
    if (!('speechSynthesis' in window)) return null;
    var voices = window.speechSynthesis.getVoices() || [];
    if (!voices || voices.length === 0) return null;
    var target = (lang || 'en-IN').toLowerCase();

    // 1. Hindi voice selection (hi-IN, hi)
    if (target.startsWith('hi')) {
      var hindiVoice = voices.find(function(v) {
        var vl = (v.lang || '').toLowerCase();
        var vn = (v.name || '').toLowerCase();
        return vl === 'hi-in' || vl.startsWith('hi') ||
               vn.includes('hindi') || vn.includes('हिन्दी') ||
               vn.includes('swara') || vn.includes('madhur') ||
               vn.includes('kalpana') || vn.includes('hemant');
      });
      if (hindiVoice) return hindiVoice;
    }

    // 2. Indian English voice for Hinglish / Indian English (en-IN, hi-latn)
    if (target === 'en-in' || target === 'hi-latn') {
      var inVoice = voices.find(function(v) {
        var vl = (v.lang || '').toLowerCase();
        var vn = (v.name || '').toLowerCase();
        return vl === 'en-in' || vl === 'en_in' ||
               vn.includes('india') || vn.includes('neerja') ||
               vn.includes('prabhat') || vn.includes('ravi');
      });
      if (inVoice) return inVoice;
    }

    // 3. Match by language prefix (e.g. en)
    var langPrefix = target.split('-')[0];
    var matchedVoice = voices.find(function(v) {
      return (v.lang || '').toLowerCase().startsWith(langPrefix);
    });
    if (matchedVoice) return matchedVoice;

    // 4. Fallback to default
    return voices.find(function(v) { return v.default; }) || voices[0];
  },

  speak: function(text, lang, rate) {
    if (!('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      var clean = (text || '').replace(/[#*`_\[\]()]/g, '').trim();
      if (!clean) return;

      var utterance = new SpeechSynthesisUtterance(clean);
      var targetLang = lang || 'en-IN';
      utterance.lang = targetLang;
      utterance.rate = rate || 0.95;

      var bestVoice = this.getBestVoice(targetLang);
      if (bestVoice) {
        utterance.voice = bestVoice;
      }

      window.uniassistVoice.isSpeaking = true;
      utterance.onend = function() {
        window.uniassistVoice.isSpeaking = false;
        if (window._onUniAssistTtsEnd) window._onUniAssistTtsEnd();
      };
      utterance.onerror = function(e) {
        console.warn('[UniAssist Voice] TTS error:', e);
        window.uniassistVoice.isSpeaking = false;
        if (window._onUniAssistTtsEnd) window._onUniAssistTtsEnd();
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('[UniAssist Voice] Speak exception:', e);
      window.uniassistVoice.isSpeaking = false;
      if (window._onUniAssistTtsEnd) window._onUniAssistTtsEnd();
    }
  },

  stopSpeaking: function() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.isSpeaking = false;
    if (window._onUniAssistTtsEnd) window._onUniAssistTtsEnd();
  }
};

// Pre-warm voices on startup
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  window.speechSynthesis.getVoices();
  if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = function() {
      window.speechSynthesis.getVoices();
    };
  }
}
