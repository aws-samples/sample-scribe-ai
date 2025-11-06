type VoiceConfig = {
  id: string;
  additionalPrompt: string;
};

const promptForLanguage = (lang: string) => {
  return `Please respond exclusively in ${lang}. If you have a question or suggestion, ask it in ${lang}. I want to ensure that our communication remains in ${lang}.`;
};

// see https://docs.aws.amazon.com/nova/latest/userguide/prompting-speech-voice-language.html
export const voiceConfigurations: { [key: string]: VoiceConfig } = {
  tiffany: {
    id: 'tiffany',
    additionalPrompt: 'Please respond exclusively in English.',
  },
  matthew: {
    id: 'matthew',
    additionalPrompt: 'Please respond exclusively in English.',
  },
  amy: {
    id: 'amy',
    additionalPrompt: 'Please respond exclusively in English. Use British English as your language for your responses.',
  },
  ambre: {
    id: 'ambre',
    additionalPrompt: promptForLanguage('French'),
  },
  florian: {
    id: 'florian',
    additionalPrompt: promptForLanguage('French'),
  },
  beatrice: {
    id: 'beatrice',
    additionalPrompt: promptForLanguage('Italian'),
  },
  lorenzo: {
    id: 'lorenzo',
    additionalPrompt: promptForLanguage('Italian'),
  },
  greta: {
    id: 'greta',
    additionalPrompt: promptForLanguage('German'),
  },
  lennart: {
    id: 'lennart',
    additionalPrompt: promptForLanguage('German'),
  },
  lupe: {
    id: 'lupe',
    additionalPrompt: promptForLanguage('Spanish'),
  },
  carlos: {
    id: 'carlos',
    additionalPrompt: promptForLanguage('Spanish'),
  },
};
