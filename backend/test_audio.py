import os
import sys
from app.services.audio_analysis import get_audio_model, analyze_audio_bytes
# Set correct local path for Windows instead of Docker's /app/
os.environ["AUDIO_MODEL_PATH"] = "ml/audio/audio_classifier.h5"

try:
    
    
    print("1. Attempting to load model...")
    model = get_audio_model()
    if model is None:
        print("Model failed to load. Check logs.")
        sys.exit(1)
    print("Model loaded successfully!")
    
    print("2. Attempting to create mock audio data...")
    import wave
    import struct
    import math
    
    # Generate 1-second 440Hz sine wave WAV file
    mock_wav_path = "test_tone.wav"
    with wave.open(mock_wav_path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        for i in range(16000):
            value = int(32767.0 * math.cos(440.0 * math.pi * float(i) / 16000.0))
            w.writeframesraw(struct.pack("<h", value))
            
    print("3. Attempting to parse audio and run inference...")
    with open(mock_wav_path, "rb") as f:
        audio_bytes = f.read()
        
    result = analyze_audio_bytes(audio_bytes, mime_type="audio/wav")
    print(f"Inference Result: {result}")
    
    # Cleanup
    if os.path.exists(mock_wav_path):
        os.remove(mock_wav_path)
        
    print("SUCCESS: Audio pipeline ran without code errors.")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
