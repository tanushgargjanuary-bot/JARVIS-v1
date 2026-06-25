"""
JARVIS v3 - Main Controller
===========================
The brain that connects core engine, commands, and HUD.
Handles: startup, wake word detection, command processing,
text mode fallback, and graceful shutdown.
"""

import os
import sys
import time
import signal
import atexit
from datetime import datetime

from jarvis_core import (
    voice, speak, listener, brain, memory,
    GROQ_API_KEY, OWNER_NAME, WAKE_WORD, MAX_MEMORY,
    get_time_greeting, get_timestamp, BASE_DIR
)
from jarvis_hud import hud, update_hud
from jarvis_commands import (
    # PC Control
    open_app, close_app, volume_control, brightness_control,
    take_screenshot, get_system_info, pc_sleep, pc_restart,
    # Clipboard
    copy_to_clipboard, read_clipboard, clear_clipboard,
    # Typing
    type_text,
    # Web
    open_website, search_web, get_weather,
    # CSE Features
    explain_concept, debug_assistant, code_complexity,
    generate_code, interview_prep, explain_error,
    # Notes
    create_note, read_last_note, list_notes,
    # Fun
    tell_joke, motivate, roast_me, fun_fact,
    flip_coin, roll_dice, calculate,
    # Daily
    set_reminder, morning_briefing,
    # Pomodoro
    pomodoro_timer, stop_pomodoro,
    # Utility
    get_time, get_date, shutdown_jarvis,
)


# ============================================================
# ASCII ART
# ============================================================

JARVIS_LOGO = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
          v3.0 - Your AI Assistant
"""


# ============================================================
# STARTUP SEQUENCE
# ============================================================

def startup():
    """Run the full JARVIS startup sequence."""
    print(JARVIS_LOGO)
    print("=" * 50)
    print(f"[{get_timestamp()}] Starting up...")

    # Load config (already done in jarvis_core imports)
    print(f"[{get_timestamp()}] Configuration loaded.")
    print(f"[{get_timestamp()}] Owner: {OWNER_NAME}")
    print(f"[{get_timestamp()}] Wake word: '{WAKE_WORD}'")

    # Test microphone
    mic_available = listener.is_available()
    if mic_available:
        print(f"[{get_timestamp()}] Microphone: OK")
    else:
        print(f"[{get_timestamp()}] Microphone: NOT AVAILABLE - falling back to text mode")

    # Test Groq API key
    if GROQ_API_KEY and GROQ_API_KEY != "your_groq_key_here":
        print(f"[{get_timestamp()}] Groq API: Key present")
    else:
        print(f"[{get_timestamp()}] [WARNING] Groq API key not configured!")
        print(f"[{get_timestamp()}] Set GROQ_API_KEY in your .env file.")
        print(f"[{get_timestamp()}] Get a free key at: https://console.groq.com/keys")

    # Start HUD
    print(f"[{get_timestamp()}] Starting HUD...")
    hud.start()
    time.sleep(0.5)

    # Greeting
    greeting = get_time_greeting()
    speak(greeting)

    # Feature summary
    speak("Voice control ready. Say my name to activate.")
    print(f"[{get_timestamp()}] JARVIS v3 is running!")
    print("=" * 50)

    return mic_available


# ============================================================
# COMMAND PROCESSOR
# ============================================================

def process_command(text: str) -> bool:
    """
    Process a voice/text command and execute the appropriate action.
    Returns True if command was handled, False otherwise.
    """
    if not text:
        return False

    text_lower = text.lower().strip()
    words = text_lower.split()

    update_hud(status='thinking', command=text)

    # --------------------------------------------------------
    # PRIORITY 1 - Exact keyword matches
    # --------------------------------------------------------

    # Greetings
    if any(w in text_lower for w in ["hello", "hi ", "hey", "greetings"]):
        speak(f"Hello, {OWNER_NAME}. How can I help?")
        return True

    # Goodbye
    if any(w in text_lower for w in ["goodbye", "bye", "see you", "shutdown", "turn off"]):
        speak("Shutting down. Goodbye!")
        shutdown()
        return True

    # Time
    if any(w in text_lower for w in ["what time", "current time", "what's the time"]):
        speak(get_time())
        return True

    # Date
    if any(w in text_lower for w in ["what date", "today's date", "what day"]):
        speak(get_date())
        return True

    # Weather
    if any(w in text_lower for w in ["weather", "temperature", "forecast"]):
        result = get_weather()
        speak(result)
        return True

    # System info
    if any(w in text_lower for w in ["system info", "cpu usage", "ram usage", "battery"]):
        result = get_system_info()
        speak(result)
        return True

    # Screenshot
    if any(w in text_lower for w in ["screenshot", "screen shot", "capture screen"]):
        result = take_screenshot()
        speak(result)
        return True

    # Joke
    if "joke" in text_lower:
        speak(tell_joke())
        return True

    # Motivation
    if any(w in text_lower for w in ["motivate", "inspire", "motivation"]):
        speak(motivate())
        return True

    # Roast
    if "roast" in text_lower:
        speak(roast_me())
        return True

    # Fun fact
    if any(w in text_lower for w in ["fun fact", "tell me a fact", "random fact"]):
        speak(fun_fact())
        return True

    # Coin flip
    if any(w in text_lower for w in ["flip a coin", "coin flip", "heads or tails"]):
        speak(flip_coin())
        return True

    # Dice roll
    if any(w in text_lower for w in ["roll a dice", "roll dice", "roll a die"]):
        # Check for sides specification
        nums = [int(w) for w in words if w.isdigit()]
        sides = nums[0] if nums else 6
        speak(roll_dice(sides))
        return True

    # Clipboard read
    if any(w in text_lower for w in ["read clipboard", "what's on clipboard", "clipboard"]):
        result = read_clipboard()
        speak(result)
        return True

    # Clipboard clear
    if any(w in text_lower for w in ["clear clipboard", "empty clipboard"]):
        result = clear_clipboard()
        speak(result)
        return True

    # Morning briefing
    if any(w in text_lower for w in ["morning briefing", "good morning", "briefing"]):
        result = morning_briefing()
        speak(result)
        return True

    # Session info
    if any(w in text_lower for w in ["session info", "session status"]):
        speak(memory.get_session_summary())
        return True

    # Notes list
    if any(w in text_lower for w in ["list notes", "show notes", "my notes"]):
        result = list_notes()
        speak(result)
        return True

    # Read last note
    if any(w in text_lower for w in ["read note", "last note"]):
        result = read_last_note()
        speak(result)
        return True

    # Stop pomodoro
    if any(w in text_lower for w in ["stop pomodoro", "cancel pomodoro"]):
        result = stop_pomodoro()
        speak(result)
        return True

    # Volume
    if "volume" in text_lower:
        if any(w in text_lower for w in ["up", "increase", "higher", "louder"]):
            speak(volume_control("up"))
        elif any(w in text_lower for w in ["down", "decrease", "lower", "quieter"]):
            speak(volume_control("down"))
        elif any(w in text_lower for w in ["mute", "unmute", "silent"]):
            speak(volume_control("mute"))
        elif any(w in text_lower for w in ["percent", "%", "set"]):
            speak(volume_control(text_lower))
        else:
            speak("Say volume up, volume down, or volume mute.")
        return True

    # Brightness
    if "brightness" in text_lower:
        if any(w in text_lower for w in ["up", "increase", "higher", "brighter"]):
            speak(brightness_control("up"))
        elif any(w in text_lower for w in ["down", "decrease", "lower", "dimmer"]):
            speak(brightness_control("down"))
        elif any(w in text_lower for w in ["percent", "%", "set"]):
            speak(brightness_control(text_lower))
        else:
            speak("Say brightness up, brightness down, or set brightness to a percentage.")
        return True

    # --------------------------------------------------------
    # PRIORITY 2 - Pattern-based commands (partial matches)
    # --------------------------------------------------------

    # Open app
    if any(w in text_lower for w in ["open ", "launch ", "start "]):
        for trigger in ["open ", "launch ", "start "]:
            if trigger in text_lower:
                app_name = text_lower.split(trigger, 1)[1].strip()
                if app_name:
                    result = open_app(app_name)
                    speak(result)
                    return True

    # Close app
    if any(w in text_lower for w in ["close ", "kill ", "quit "]):
        for trigger in ["close ", "kill ", "quit "]:
            if trigger in text_lower:
                app_name = text_lower.split(trigger, 1)[1].strip()
                if app_name:
                    result = close_app(app_name)
                    speak(result)
                    return True

    # Open website
    if any(w in text_lower for w in ["go to ", "visit "]):
        for trigger in ["go to ", "visit "]:
            if trigger in text_lower:
                site = text_lower.split(trigger, 1)[1].strip()
                if site:
                    result = open_website(site)
                    speak(result)
                    return True

    # Search web
    if any(w in text_lower for w in ["search for ", "search ", "look up ", "google "]):
        for trigger in ["search for ", "search ", "look up ", "google "]:
            if trigger in text_lower:
                query = text_lower.split(trigger, 1)[1].strip()
                if query:
                    # Detect search engine
                    engine = "google"
                    for eng in ["youtube", "github", "stackoverflow", "leetcode", "geeksforgeeks", "bing", "duckduckgo"]:
                        if eng in text_lower:
                            engine = eng
                            break
                    result = search_web(engine, query)
                    speak(result)
                    return True

    # Calculate
    if any(w in text_lower for w in ["calculate ", "what is ", "compute ", "math "]):
        for trigger in ["calculate ", "what is ", "compute ", "math "]:
            if trigger in text_lower:
                expr = text_lower.split(trigger, 1)[1].strip()
                if expr:
                    speak(calculate(expr))
                    return True

    # Explain concept
    if any(w in text_lower for w in ["explain ", "what is ", "what are ", "how does ", "define "]):
        for trigger in ["explain ", "what is ", "what are ", "how does ", "define "]:
            if trigger in text_lower:
                topic = text.split(trigger, 1)[1].strip()  # Use original case
                if topic:
                    speak(explain_concept(topic))
                    return True

    # Debug assistant
    if any(w in text_lower for w in ["debug", "fix my code", "error in my code"]):
        result = debug_assistant()
        speak(result)
        return True

    # Code complexity
    if any(w in text_lower for w in ["complexity", "big o", "time complexity", "space complexity"]):
        speak("Describe the algorithm for complexity analysis.")
        desc = listen_or_input()
        if desc:
            speak(code_complexity(desc))
        return True

    # Generate code
    if any(w in text_lower for w in ["generate code", "write code", "code for", "create code"]):
        speak("What code should I generate?")
        desc = listen_or_input()
        if desc:
            result = generate_code(desc)
            speak(result)
        return True

    # Interview prep
    if any(w in text_lower for w in ["interview", "prep me", "quiz me"]):
        speak("What topic for interview preparation?")
        topic = listen_or_input()
        if topic:
            speak(interview_prep(topic))
        return True

    # Explain error
    if any(w in text_lower for w in ["error message", "what does this error mean", "explain error"]):
        speak("What is the error message?")
        error_msg = listen_or_input()
        if error_msg:
            speak(explain_error(error_msg))
        return True

    # Create note
    if any(w in text_lower for w in ["create note", "take note", "new note", "write note"]):
        result = create_note()
        speak(result)
        return True

    # Set reminder
    if any(w in text_lower for w in ["remind me", "set reminder", "reminder"]):
        # Parse: "remind me in 5 minutes drink water"
        reminder_text = text_lower
        time_str = ""
        message = ""

        # Extract time portion
        if "in " in reminder_text:
            parts = reminder_text.split("in ", 1)[1]
            # Time is usually first 2-3 words after "in"
            time_words = parts.split()[:3]
            time_str = " ".join(time_words)
            # Message is the rest
            remaining = " ".join(parts.split()[3:])
            if remaining:
                message = remaining
            else:
                message = "Time's up!"
        else:
            time_str = "5 minutes"
            message = reminder_text.replace("remind me", "").replace("set reminder", "").strip()
            if not message:
                message = "Reminder!"

        result = set_reminder(time_str, message)
        speak(result)
        return True

    # Pomodoro timer
    if any(w in text_lower for w in ["pomodoro", "focus timer", "study timer"]):
        nums = [int(w) for w in words if w.isdigit()]
        mins = nums[0] if nums else 25
        result = pomodoro_timer(mins)
        speak(result)
        return True

    # Type text
    if any(w in text_lower for w in ["type this", "type ", "write this"]):
        speak("What should I type?")
        text_to_type = listen_or_input()
        if text_to_type:
            result = type_text(text_to_type)
            speak(result)
        return True

    # Copy to clipboard
    if any(w in text_lower for w in ["copy to clipboard", "copy this"]):
        speak("What should I copy?")
        text_to_copy = listen_or_input()
        if text_to_copy:
            result = copy_to_clipboard(text_to_copy)
            speak(result)
        return True

    # Sleep / Restart
    if "sleep" in text_lower and "pc" in text_lower:
        result = pc_sleep()
        speak(result)
        return True

    if "restart" in text_lower and "pc" in text_lower:
        result = pc_restart()
        speak(result)
        return True

    # --------------------------------------------------------
    # PRIORITY 3 - Groq AI fallback
    # --------------------------------------------------------

    # Send to AI for general conversation
    ai_response = brain.ask_jarvis(text)
    speak(ai_response)
    return True


# ============================================================
# WAKE WORD SYSTEM
# ============================================================

def listen_for_wake_word() -> bool:
    """
    Continuously listen for the wake word.
    Returns True when wake word detected.
    """
    detected = listener.listen_for_wake_word(timeout=2)
    if detected and WAKE_WORD in detected:
        print(f"[{get_timestamp()}] Wake word detected: '{detected}'")
        update_hud(status='listening')
        speak("Yes?")
        return True
    return False


def activate_mode():
    """
    Activated mode: listen for a command within 8 seconds.
    Returns True if a command was processed.
    """
    print(f"[{get_timestamp()}] Activated - listening for command...")
    update_hud(status='listening')

    command = listener.listen(timeout=6, phrase_time_limit=8)

    if command:
        update_hud(status='thinking', command=command)
        try:
            process_command(command)
        except Exception as e:
            print(f"[COMMAND ERROR] {e}")
            speak("Something went wrong with that command.")
        return True

    # Timeout - go back to sleep
    print(f"[{get_timestamp()}] No command received. Going back to sleep.")
    update_hud(status='idle')
    return False


# ============================================================
# TEXT MODE FALLBACK
# ============================================================

def text_mode():
    """Run JARVIS in text-only mode when microphone is unavailable."""
    print("\n" + "=" * 50)
    print("  TEXT MODE - Type commands at the prompt")
    print("  Type 'exit' or 'quit' to shutdown")
    print("=" * 50 + "\n")

    speak("Text mode active. Type your commands.")

    while True:
        try:
            user_input = input("JARVIS> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input.lower() in ['exit', 'quit', 'goodbye', 'bye']:
            speak("Goodbye!")
            break

        update_hud(status='thinking', command=user_input)
        try:
            process_command(user_input)
        except Exception as e:
            print(f"[ERROR] {e}")
            speak("That command caused an error.")

    shutdown()


# ============================================================
# MAIN LOOP
# ============================================================

def listen_or_input() -> str:
    """
    Helper: listen via mic if available, otherwise use text input.
    Returns the captured string or None.
    """
    if listener.is_available():
        return listener.listen(timeout=8, phrase_time_limit=10)
    else:
        try:
            return input("[INPUT] ").strip()
        except (EOFError, KeyboardInterrupt):
            return None


def main_loop():
    """Main voice-controlled loop with wake word detection."""
    mic_failures = 0
    max_failures = 5

    speak("Voice mode active. Say my name to wake me.")

    while True:
        try:
            if not listener.is_available():
                mic_failures += 1
                if mic_failures >= max_failures:
                    speak("Microphone keeps failing. Switching to text mode.")
                    text_mode()
                    return
                time.sleep(1)
                continue

            # Listen for wake word
            if listen_for_wake_word():
                mic_failures = 0
                activate_mode()
            else:
                time.sleep(0.5)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[MAIN LOOP ERROR] {e}")
            time.sleep(1)

    shutdown()


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown():
    """Graceful shutdown sequence."""
    print(f"\n[{get_timestamp()}] Shutting down JARVIS...")

    # Save session stats
    summary = memory.get_session_summary()
    memory.log_session_event(f"SESSION END - {summary}")

    # Stop HUD
    hud.stop()

    speak("Session ended." + summary)
    print(f"[{get_timestamp()}] {summary}")
    print(f"[{get_timestamp()}] JARVIS v3 shutdown complete.")
    print("=" * 50)

    sys.exit(0)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    speak("Goodbye!")
    shutdown()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)

    # Startup
    mic_ok = startup()

    # Choose mode
    if mic_ok:
        main_loop()
    else:
        text_mode()
