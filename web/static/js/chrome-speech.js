/**
 * Chrome-specific speech synthesis implementation
 */

// Chrome Text-to-Speech Helper
window.ChromeSpeech = {
  // Track if speech synthesis is currently active
  speaking: false,
  
  // Store available voices
  voices: [],
  
  // Initialize speech synthesis
  init: function() {
    console.log("Initializing Chrome speech synthesis");
    
    // Load voices
    this.loadVoices();
    
    // Chrome requires this event to load voices
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = this.loadVoices.bind(this);
    }
  },
  
  // Load available voices
  loadVoices: function() {
    this.voices = window.speechSynthesis.getVoices();
    console.log(`Loaded ${this.voices.length} voices`);
  },
  
  // Get a suitable English voice
  getEnglishVoice: function() {
    if (this.voices.length === 0) {
      return null;
    }
    
    // Try to find an English voice
    return this.voices.find(voice => 
      voice.lang === 'en-US' || 
      voice.lang === 'en_US' || 
      voice.lang === 'en-GB'
    ) || this.voices[0]; // Fallback to first voice
  },
  
  // Speak text
  speak: function(text, button) {
    if (!text || !window.speechSynthesis) {
      return false;
    }
    
    console.log("Chrome speaking:", text);
    
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    this.speaking = false;
    
    // Create utterance
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Try to set an English voice
    const englishVoice = this.getEnglishVoice();
    if (englishVoice) {
      utterance.voice = englishVoice;
    }
    
    // Set up event handlers
    utterance.onstart = () => {
      this.speaking = true;
      if (button) {
        const icon = button.querySelector('i');
        if (icon) {
          icon.classList.remove('fa-volume-up');
          icon.classList.add('fa-volume-mute');
        }
      }
    };
    
    utterance.onend = () => {
      this.speaking = false;
      if (button) {
        const icon = button.querySelector('i');
        if (icon) {
          icon.classList.remove('fa-volume-mute');
          icon.classList.add('fa-volume-up');
        }
      }
    };
    
    utterance.onerror = (event) => {
      console.error('Speech synthesis error:', event);
      this.speaking = false;
      if (button) {
        const icon = button.querySelector('i');
        if (icon) {
          icon.classList.remove('fa-volume-mute');
          icon.classList.add('fa-volume-up');
        }
      }
    };
    
    // Speak the text
    window.speechSynthesis.speak(utterance);
    
    // Chrome bug workaround - speech stops after ~15 seconds
    const intervalId = setInterval(() => {
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
      } else {
        clearInterval(intervalId);
      }
    }, 10000);
    
    return true;
  }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  window.ChromeSpeech.init();
});
