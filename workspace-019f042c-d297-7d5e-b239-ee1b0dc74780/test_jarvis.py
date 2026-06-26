"""
JARVIS v3 - Test Suite
======================
Run this to test all components before launching JARVIS.
Prints PASS or FAIL for each test.
"""

import os
import sys
import time
from datetime import datetime


def print_header(title):
    """Print a formatted test section header."""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


def print_result(test_name, passed, message=""):
    """Print a test result."""
    status = "PASS" if passed else "FAIL"
    symbol = "[OK]" if passed else "[XX]"
    print(f"  {symbol} {test_name}: {status}")
    if message:
        print(f"       -> {message}")
    return passed


def test_environment():
    """Test 1: Environment and imports."""
    print_header("TEST 1: Environment & Imports")
    passed = 0
    failed = 0

    # Python version
    py_version = sys.version_info
    version_ok = py_version.major >= 3 and py_version.minor >= 8
    if print_result("Python 3.8+", version_ok,
                    f"Python {py_version.major}.{py_version.minor}.{py_version.micro}"):
        passed += 1
    else:
        failed += 1

    # .env file exists
    env_exists = os.path.exists(".env")
    print_result(".env file exists", env_exists,
                 "Found" if env_exists else "Missing! Copy from .env.example")
    if env_exists:
        passed += 1
    else:
        failed += 1

    # Required packages
    packages = [
        ("groq", "Groq AI client"),
        ("speech_recognition", "Speech recognition"),
        ("pyttsx3", "Text-to-speech"),
        ("pyautogui", "GUI automation"),
        ("psutil", "System info"),
        ("requests", "HTTP requests"),
        ("pyjokes", "Jokes"),
        ("pyperclip", "Clipboard"),
        ("dotenv", "Environment variables"),
    ]

    for module_name, description in packages:
        try:
            __import__(module_name)
            if print_result(f"{description}", True):
                passed += 1
            else:
                failed += 1
        except ImportError:
            if print_result(f"{description}", False,
                            f"Run: pip install {module_name}"):
                passed += 1
            else:
                failed += 1

    return passed, failed


def test_groq_api():
    """Test 2: Groq API connectivity."""
    print_header("TEST 2: Groq AI Brain")
    passed = 0
    failed = 0

    try:
        from jarvis_core import GROQ_API_KEY, brain

        # Check API key exists
        key_exists = bool(GROQ_API_KEY and GROQ_API_KEY != "your_groq_key_here")
        if print_result("API Key configured", key_exists):
            passed += 1
        else:
            failed += 1
            print("       -> Set GROQ_API_KEY in your .env file")
            return passed, failed

        # Test API call
        print("       -> Testing API call...")
        response = brain.ask_jarvis("Say 'hello' and nothing else.")
        api_works = bool(response and len(response) > 0)
        if print_result("Groq API response", api_works,
                        f"Response: {response[:50]}..." if api_works else "No response"):
            passed += 1
        else:
            failed += 1

    except Exception as e:
        print_result("Groq API", False, str(e))
        failed += 2

    return passed, failed


def test_voice():
    """Test 3: Text-to-speech engine."""
    print_header("TEST 3: Voice Engine (TTS)")
    passed = 0
    failed = 0

    try:
        from jarvis_core import voice

        # Engine init
        init_ok = voice.engine is not None
        if print_result("TTS Engine initialized", init_ok):
            passed += 1
        else:
            failed += 1
            return passed, failed

        # Voice available
        voices = voice.engine.getProperty('voices')
        voice_count = len(voices)
        has_voices = voice_count > 0
        if print_result(f"Voices available ({voice_count})", has_voices):
            passed += 1
        else:
            failed += 1

        # Test speak (silent - just check no crash)
        print("       -> Testing speak function...")
        voice.speak("Test successful.")
        if print_result("Speak function", True):
            passed += 1
        else:
            failed += 1

    except Exception as e:
        print_result("Voice engine", False, str(e))
        failed += 3

    return passed, failed


def test_microphone():
    """Test 4: Microphone availability."""
    print_header("TEST 4: Microphone")
    passed = 0
    failed = 0

    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        with mic as source:
            print("       -> Calibrating for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)

        if print_result("Microphone detected", True,
                        "Ambient noise calibrated"):
            passed += 1
        else:
            failed += 1

    except Exception as e:
        print_result("Microphone", False, str(e))
        print("       -> Voice commands will not work. Use text mode.")
        failed += 1

    return passed, failed


def test_commands():
    """Test 5: Command functions (non-destructive tests only)."""
    print_header("TEST 5: Command Functions")
    passed = 0
    failed = 0

    try:
        from jarvis_commands import (
            tell_joke, motivate, flip_coin, roll_dice, calculate,
            get_weather, get_time, get_date
        )

        # Joke
        joke = tell_joke()
        if print_result("tell_joke()", bool(joke)):
            passed += 1
        else:
            failed += 1

        # Motivation
        quote = motivate()
        if print_result("motivate()", bool(quote)):
            passed += 1
        else:
            failed += 1

        # Coin flip
        coin = flip_coin()
        if print_result("flip_coin()", "heads" in coin.lower() or "tails" in coin.lower()):
            passed += 1
        else:
            failed += 1

        # Dice roll
        dice = roll_dice(6)
        if print_result("roll_dice()", "rolled" in dice.lower()):
            passed += 1
        else:
            failed += 1

        # Calculate
        calc = calculate("15 percent of 3000")
        if print_result("calculate()", "450" in calc):
            passed += 1
        else:
            failed += 1

        # Time
        t = get_time()
        if print_result("get_time()", bool(t)):
            passed += 1
        else:
            failed += 1

        # Date
        d = get_date()
        if print_result("get_date()", bool(d)):
            passed += 1
        else:
            failed += 1

    except Exception as e:
        print_result("Commands test", False, str(e))
        failed += 7

    return passed, failed


def test_hud():
    """Test 6: HUD overlay."""
    print_header("TEST 6: HUD Overlay")
    passed = 0
    failed = 0

    try:
        from jarvis_hud import hud, update_hud

        # Start HUD
        print("       -> Starting HUD...")
        hud.start()
        time.sleep(1)

        if print_result("HUD started", hud._running):
            passed += 1
        else:
            failed += 1

        # Update HUD
        update_hud(status='listening', command='test command',
                   response='test response', memory_count=5)
        time.sleep(0.5)

        if print_result("HUD update", hud._running):
            passed += 1
        else:
            failed += 1

        # Stop HUD
        hud.stop()
        time.sleep(0.5)

        if print_result("HUD stopped", not hud._running):
            passed += 1
        else:
            failed += 1

    except Exception as e:
        print_result("HUD test", False, str(e))
        failed += 3

    return passed, failed


def test_folders():
    """Test 7: Required folders exist."""
    print_header("TEST 7: Folder Structure")
    passed = 0
    failed = 0

    folders = ["memory", "notes", "screenshots", "logs"]
    for folder in folders:
        exists = os.path.isdir(folder)
        if print_result(f"Folder: {folder}/", exists):
            passed += 1
        else:
            failed += 1

    return passed, failed


# ============================================================
# MAIN TEST RUNNER
# ============================================================

def run_all_tests():
    """Run the complete test suite."""
    print("\n" + "=" * 50)
    print("  JARVIS v3 - Component Test Suite")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    total_passed = 0
    total_failed = 0

    # Run all test groups
    tests = [
        test_environment,
        test_groq_api,
        test_voice,
        test_microphone,
        test_commands,
        test_hud,
        test_folders,
    ]

    for test_func in tests:
        try:
            p, f = test_func()
            total_passed += p
            total_failed += f
        except Exception as e:
            print(f"\n  [XX] Test group crashed: {e}")
            total_failed += 1

    # Summary
    total = total_passed + total_failed
    print("\n" + "=" * 50)
    print(f"  RESULTS: {total_passed}/{total} tests passed")
    print("=" * 50)

    if total_failed == 0:
        print("\n  [OK] All tests passed! JARVIS is ready to run.")
        print("       Launch with: run.bat")
    else:
        print(f"\n  [WARNING] {total_failed} test(s) failed.")
        print("  Common fixes:")
        print("  - Run: install.bat")
        print("  - Add your GROQ_API_KEY to .env file")
        print("  - Check microphone is connected (for voice mode)")
        print("  - Install Windows Media Features (for TTS voices)")

    print()
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
