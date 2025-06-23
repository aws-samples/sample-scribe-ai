function Speech() {
  // Use the cross-browser speech recognition if available
  if (window.CrossBrowserSpeech && window.CrossBrowserSpeech.recognition) {
    console.log("Using CrossBrowserSpeech recognition");
    this.recognition = {
      start: function() {
        window.CrossBrowserSpeech.recognition.startCapture();
      },
      stop: function() {
        window.CrossBrowserSpeech.recognition.stopCapture();
      }
    };
    
    // Set up the onresult handler
    window.CrossBrowserSpeech.recognition.recognition.onresult = function(event) {
      // Forward the event to any listeners
      if (this.onresult) {
        this.onresult(event);
      }
    }.bind(this);
    
    this.startCapture = function() {
      this.recognition.start();
    };
    
    this.stopCapture = function() {
      this.recognition.stop();
    };
    
  } else if ('webkitSpeechRecognition' in window) {
    // Fallback to webkit-specific implementation
    console.log("Using webkitSpeechRecognition");
    this.recognition = new webkitSpeechRecognition();

    // settings
    this.recognition.continuous = true; // stop automatically
    this.recognition.lang = 'en-US';

    this.startCapture = function() {
      this.recognition.start();
    };

    this.stopCapture = function() {
      this.recognition.stop();
    };

    console.log("webkitSpeechRecognition is available.");
  } else {
    console.log("Speech recognition is not available in this browser.");
    
    // Create dummy methods to prevent errors
    this.startCapture = function() {
      alert("Speech recognition is not supported in your browser.");
    };
    
    this.stopCapture = function() {};
  }
}
