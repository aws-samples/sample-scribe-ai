// Audio Context Fix for Voice Interface
// This script ensures AudioContext and MediaStream have compatible sample rates

(function() {
    'use strict';
    
    // Store original AudioContext constructor
    const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;
    
    // Override AudioContext constructor to force 16kHz sample rate
    function FixedAudioContext(options = {}) {
        // Force 16kHz sample rate to match MediaStream constraints
        const fixedOptions = {
            ...options,
            sampleRate: 16000,
            latencyHint: options.latencyHint || 'interactive'
        };
        
        console.log('Creating AudioContext with fixed sample rate:', fixedOptions.sampleRate);
        return new OriginalAudioContext(fixedOptions);
    }
    
    // Copy static methods and properties
    Object.setPrototypeOf(FixedAudioContext, OriginalAudioContext);
    Object.defineProperty(FixedAudioContext, 'prototype', {
        value: OriginalAudioContext.prototype,
        writable: false
    });
    
    // Replace global AudioContext
    window.AudioContext = FixedAudioContext;
    if (window.webkitAudioContext) {
        window.webkitAudioContext = FixedAudioContext;
    }
    
    console.log('Audio context fix applied - forcing 16kHz sample rate');
})();
