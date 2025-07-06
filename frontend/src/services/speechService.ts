import { api } from './api';

export interface TranscriptionResult {
  text: string;
  language?: string;
  confidence?: number;
}

export interface VoiceMessageResponse {
  transcription: TranscriptionResult;
  chatResponse: {
    message: any;
    conversationId?: string;
    tasks?: any[];
    action?: string;
    usedAI: boolean;
  };
}

export const speechService = {
  /**
   * Send audio blob to backend for transcription and processing
   */
  async processVoiceMessage(
    audioBlob: Blob,
    language: string = 'auto'
  ): Promise<VoiceMessageResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');
    formData.append('language', language);

    const response = await api.post<VoiceMessageResponse>(
      '/chat/voice-message',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Convert text to speech using browser's Web Speech API
   */
  async textToSpeech(
    text: string,
    language: string = 'en'
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!('speechSynthesis' in window)) {
        reject(new Error('Text-to-speech not supported in this browser'));
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      
      // Map language codes to speech synthesis languages
      const langMap: Record<string, string> = {
        'en': 'en-US',
        'hi': 'hi-IN',
        'bn': 'bn-IN', // Bengali might not be available on all systems
      };
      
      utterance.lang = langMap[language] || 'en-US';
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onend = () => resolve();
      utterance.onerror = (event) => reject(event);

      // Cancel any ongoing speech
      window.speechSynthesis.cancel();
      
      // Speak the text
      window.speechSynthesis.speak(utterance);
    });
  },

  /**
   * Check if text-to-speech is available for a given language
   */
  isTTSAvailable(language: string = 'en'): boolean {
    if (!('speechSynthesis' in window)) return false;

    const voices = window.speechSynthesis.getVoices();
    const langMap: Record<string, string> = {
      'en': 'en',
      'hi': 'hi',
      'bn': 'bn',
    };

    const targetLang = langMap[language] || 'en';
    return voices.some(voice => voice.lang.toLowerCase().startsWith(targetLang));
  },

  /**
   * Get available voices for a language
   */
  getAvailableVoices(language: string = 'en'): SpeechSynthesisVoice[] {
    if (!('speechSynthesis' in window)) return [];

    const voices = window.speechSynthesis.getVoices();
    const langMap: Record<string, string> = {
      'en': 'en',
      'hi': 'hi',
      'bn': 'bn',
    };

    const targetLang = langMap[language] || 'en';
    return voices.filter(voice => voice.lang.toLowerCase().startsWith(targetLang));
  },

  /**
   * Convert audio blob to base64 string
   */
  async audioToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        resolve(base64String.split(',')[1]); // Remove data URL prefix
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  },

  /**
   * Check if microphone permission is granted
   */
  async checkMicrophonePermission(): Promise<boolean> {
    try {
      const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      return result.state === 'granted';
    } catch {
      // Fallback for browsers that don't support permissions API
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        return true;
      } catch {
        return false;
      }
    }
  },
};