# Voice Feature Documentation

## Overview

The Smart-ToDo app now supports voice input with push-to-talk functionality. Users can record their voice in English, Bengali, or Hindi, and the app will transcribe it and process it through the chat system.

## Features

- **Push-to-Talk**: Hold the microphone button to record, release to stop
- **Multi-language Support**: English, Bengali (বাংলা), and Hindi (हिन्दी)
- **Auto-detection**: Automatically detects the spoken language
- **Visual Feedback**: Recording indicator, audio level visualization, and processing status
- **Accessibility**: Keyboard support (Space key) and screen reader compatible

## Architecture

### Frontend Components

1. **useAudioRecorder Hook** (`frontend/src/hooks/useAudioRecorder.ts`)
   - Handles MediaRecorder API
   - Monitors audio levels for visualization
   - Manages recording state and timing

2. **VoiceButton Component** (`frontend/src/components/VoiceButton.tsx`)
   - Push-to-talk interface
   - Language selection menu
   - Visual recording indicators
   - Handles both desktop (mouse) and mobile (touch) events

3. **Speech Service** (`frontend/src/services/speechService.ts`)
   - Sends audio to backend API
   - Handles text-to-speech (browser API)
   - Manages microphone permissions

4. **Updated ChatInput** (`frontend/src/components/ChatInput.tsx`)
   - Integrated voice button
   - Auto-sends transcribed text after 500ms delay
   - Shows processing status

### Backend Components

1. **Speech Service** (`backend/app/services/speech_service.py`)
   - Integrates with HuggingFace Inference API
   - Uses OpenAI Whisper models for transcription
   - Validates audio format and size
   - Handles language detection

2. **Voice Message Endpoint** (`backend/app/api/v1/chat.py`)
   - `/api/v1/chat/voice-message` - POST endpoint
   - Accepts audio file upload
   - Returns transcription and optional chat response

3. **Speech Schemas** (`backend/app/schemas/speech.py`)
   - Pydantic models for API validation
   - TranscriptionResult, VoiceMessageResponse

## Usage

### For Users

1. **Recording Voice**:
   - Click and hold the microphone button (desktop)
   - Tap to start/stop recording (mobile)
   - Or press and hold Space key (keyboard)

2. **Language Selection**:
   - Click the language icon next to mic button
   - Select from: Auto-detect, English, Bengali, Hindi

3. **Visual Feedback**:
   - Red pulsing button while recording
   - Recording timer shows duration
   - Audio level bar shows input volume

4. **Processing**:
   - After recording, the app transcribes your speech
   - Text appears in the input field briefly
   - Message is auto-sent after 500ms

### For Developers

#### Configuration

1. **HuggingFace API Token**:
   - Set in admin panel or environment variable
   - Required for speech transcription
   - Free tier includes sufficient credits

2. **Supported Audio Formats**:
   - WebM with Opus codec (default from browser)
   - WAV format
   - Maximum file size: 10MB
   - Optimal sample rate: 16kHz

3. **API Usage**:
```typescript
// Frontend usage
const response = await speechService.processVoiceMessage(audioBlob, 'en');

// Response format
{
  transcription: {
    text: "Create a task to buy groceries",
    language: "en",
    confidence: 0.95
  },
  chatResponse: { ... } // Optional, if processed through chat
}
```

#### Testing

1. **Test Script** (`test_voice.py`):
   - Tests HuggingFace API directly
   - Validates endpoint configuration
   - Creates sample audio for testing

2. **Manual Testing**:
   - Ensure microphone permissions are granted
   - Test each language separately
   - Verify audio level indicators work
   - Check error handling (no mic, API errors)

## Troubleshooting

### Common Issues

1. **"Speech service is loading"**:
   - HuggingFace models load on first use
   - Wait 20-30 seconds and try again

2. **No microphone permission**:
   - Browser will prompt for permission
   - Check browser settings if denied

3. **Transcription errors**:
   - Ensure HuggingFace API token is set
   - Check audio quality and background noise
   - Verify language selection matches spoken language

4. **Bengali not working in TTS**:
   - Browser TTS support for Bengali varies by OS
   - Works best on Windows and Android
   - Falls back to English if unavailable

### Performance Tips

1. **Optimal Recording**:
   - Speak clearly and at normal pace
   - Minimize background noise
   - Keep recordings under 30 seconds

2. **Language Detection**:
   - Use specific language selection for better accuracy
   - Auto-detect works but may be slower

3. **API Limits**:
   - HuggingFace free tier: ~1000 minutes/month
   - Each request uses minimal credits
   - Cached responses reduce API calls

## Future Enhancements

1. **Planned Features**:
   - Voice responses using TTS
   - Continuous conversation mode
   - Voice commands ("stop recording")
   - Offline mode with browser APIs

2. **Possible Improvements**:
   - Real-time transcription display
   - Voice activity detection
   - Speaker identification
   - Custom wake words

## Security Considerations

1. **Audio Privacy**:
   - Audio is not stored on server
   - Processed in memory only
   - Deleted after transcription

2. **API Security**:
   - Requires authentication
   - Rate limited per user
   - Audio size validation

3. **Permissions**:
   - Explicit user consent for microphone
   - Clear recording indicators
   - No background recording