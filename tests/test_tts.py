"""
tests/test_tts.py — Isolated TTS
==============================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.tts import TextToSpeech
from config import TTS_CONFIG


def test_tts():
    print("=" * 55)
    print("  TTS COMPONENT TEST — Day 4")
    print("=" * 55)
    print("You should HEAR speech through your speakers/headphones.")
    print()

    tts = TextToSpeech(TTS_CONFIG)

    # First, list all voices so you can pick your favourite
    tts.list_voices()
    print("If you want a different voice, change 'voice_index' in config.py")
    print("and re-run this test.")
    print()

    # Test phrases
    test_phrases = [
        "Hello! I am Taara, your offline AI assistant.",
        "All of my processing happens on your local device.",
        "No internet connection is required for me to work.",
    ]

    latencies = []

    for i, phrase in enumerate(test_phrases, 1):
        print(f"─── Phrase {i} ───")
        print(f"  Text: {phrase}")
        latency = tts.speak(phrase)
        print(f"  ⏱  TTS time: {latency:.2f}s")
        latencies.append(latency)
        print()

    # Summary
    print("=" * 55)
    avg = sum(latencies) / len(latencies)
    print(f"  ✅ TTS TEST PASSED")
    print(f"  📊 Average TTS time: {avg:.2f}s")
    print()
    print("  If you heard all 3 phrases clearly, TTS is working.")
    print("  If not:")
    print("  - Check Windows audio output device")
    print("  - Try: pip install --force-reinstall pyttsx3")
    print("=" * 55)


if __name__ == "__main__":
    test_tts()