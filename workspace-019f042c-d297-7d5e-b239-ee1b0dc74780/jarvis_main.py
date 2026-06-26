"""
JARVIS v4 - Main Controller
===========================
The brain that connects core engine, commands, HUD, chat DB, RAG, and agent tools.
Handles: startup, wake word detection, command processing,
text mode fallback, and graceful shutdown.

v4 Changes:
- Integrated SQLite chat history (jarvis_chat_db)
- RAG document Q&A (jarvis_rag)
- Multi-agent tool calling (jarvis_agent_tools)
- Modern CustomTkinter HUD (jarvis_hud)
"""

import os
import sys
import time
import signal
import atexit
import threading
from datetime import datetime

from jarvis_core import (
    voice, speak, listener, brain, memory,
    GROQ_API_KEY, OWNER_NAME, WAKE_WORD, MAX_MEMORY,
    AGENT_TOOLS_ENABLED, RAG_ENABLED,
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

# v4 imports
try:
    from jarvis_chat_db import (
        chat_db, create_conversation,
        add_user_message as db_add_user_msg,
        add_assistant_message as db_add_ai_msg,
        get_conversation_messages, get_ai_context,
    )
    CHAT_DB_AVAILABLE = True
except ImportError:
    CHAT_DB_AVAILABLE = False
    print("[WARNING] Chat database not available. Chat history disabled.")

try:
    from jarvis_rag import rag_engine
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("[WARNING] RAG system not available. Document Q&A disabled.")

try:
    from jarvis_agent_tools import agent, ask_with_tools
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("[WARNING] Agent tools not available. Tool calling disabled.")


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
          v4.0 - Upgraded AI Assistant
"""


# ============================================================
# STARTUP SEQUENCE
# ============================================================

def startup():
    """Run the full JARVIS startup sequence."""
    print(JARVIS_LOGO)
    print("=" * 60)
    print(f"[{get_timestamp()}] Starting up...")

    # Load config
    print(f"[{get_timestamp()}] Configuration loaded.")
    print(f"[{get_timestamp()}] Owner: {OWNER_NAME}")
    print(f"[{get_timestamp()}] Wake word: '{WAKE_WORD}'")

    # Feature flags
    print(f"[{get_timestamp()}] Features:")
    print(f"  - Chat History (SQLite): {'ON' if CHAT_DB_AVAILABLE else 'OFF'}")
    print(f"  - RAG Document Q&A: {'ON' if RAG_AVAILABLE else 'OFF'}")
    print(f"  - Agent Tool Calling: {'ON' if AGENT_AVAILABLE else 'OFF'}")

    # Initialize chat DB
    if CHAT_DB_AVAILABLE:
        conv_id = create_conversation("Default Session")
        hud.current_conversation_id = conv_id
        print(f"[{get_timestamp()}] Chat database initialized. Conv ID: {conv_id}")

    # Initialize RAG
    if RAG_AVAILABLE and rag_engine.is_ready():
        stats = rag_engine.get_stats()
        print(f"[{get_timestamp()}] RAG system ready. {stats.get('total_documents', 0)} documents indexed.")

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
    print(f"[{get_timestamp()}] Starting Modern HUD...")
    hud.start()
    time.sleep(1)

    # Set up HUD callbacks
    hud.on_send_message = handle_text_command

    # Greeting
    greeting = get_time_greeting()
    speak(greeting)

    # Feature summary
    speak("All systems operational. Say my name to activate.")
    print(f"[{get_timestamp()}] JARVIS v4 is running!")
    print("=" * 60)

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

    # Save user message to DB
    if CHAT_DB_AVAILABLE and hud.current_conversation_id:
        db_add_user_msg(hud.current_conversation_id, text)

    # --------------------------------------------------------
    # PRIORITY 1 - v4 Features
    # --------------------------------------------------------

    # Document Q&A (RAG)
    if RAG_AVAILABLE and any(w in text_lower for w in [
        "ask document", "ask my document", "what does my document",
        "what does the document", "search document", "document says",
        "in my file", "in the file", "uploaded file", "uploaded document"
    ]):
        result = handle_rag_query(text)
        speak(result)
        return True

    # Agent tool query (explicit)
    if AGENT_AVAILABLE and any(w in text_lower for w in [
        "search the web", "look up online", "what's the weather in",
        "calculate ", "run python", "execute code", "system info detailed",
    ]):
        result = handle_agent_query(text)
        speak(result)
        return True

    # --------------------------------------------------------
    # PRIORITY 2 - Exact keyword matches
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
    # PRIORITY 3 - Pattern-based commands
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
                topic = text.split(trigger, 1)[1].strip()
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
        reminder_text = text_lower
        time_str = ""
        message = ""

        if "in " in reminder_text:
            parts = reminder_text.split("in ", 1)[1]
            time_words = parts.split()[:3]
            time_str = " ".join(time_words)
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
    # PRIORITY 4 - AI fallback (with tools if enabled)
    # --------------------------------------------------------

    # Try agent tools first if enabled
    if AGENT_AVAILABLE and AGENT_TOOLS_ENABLED:
        try:
            result = ask_with_tools(text)
            response = result.get("response", "I'm not sure how to help with that.")
            speak(response)

            # Show tool calls in HUD
            tool_calls = result.get("tool_calls", [])
            if tool_calls:
                tc_summary = ", ".join([t["tool"] for t in tool_calls])
                update_hud(status='thinking', response=f"Used tools: {tc_summary}")

            return True
        except Exception as e:
            print(f"[AGENT ERROR] {e}")
            # Fall through to basic AI

    # Basic AI response
    ai_response = brain.ask_jarvis(text)
    speak(ai_response)
    return True


def handle_text_command(text: str):
    """Handle text commands from the GUI input."""
    update_hud(status='thinking', command=text)

    try:
        process_command(text)
    except Exception as e:
        print(f"[COMMAND ERROR] {e}")
        speak("Something went wrong with that command.")
        update_hud(status='idle')


def handle_rag_query(text: str) -> str:
    """Handle a RAG document query."""
    if not RAG_AVAILABLE:
        return "RAG system is not available."

    try:
        # Extract the actual question
        question = text
        for prefix in [
            "ask document", "ask my document", "what does my document say about",
            "what does the document say about", "search document for",
            "document says", "in my file", "in the file",
            "uploaded file", "uploaded document"
        ]:
            if prefix in text.lower():
                question = text.lower().split(prefix, 1)[1].strip()
                break

        result = rag_engine.ask_document(question)

        if result["context"]:
            # Generate AI response with context
            ai_response = brain.ask_with_context(question, result["context"])

            # Save to chat DB
            if CHAT_DB_AVAILABLE and hud.current_conversation_id:
                db_add_ai_msg(hud.current_conversation_id, ai_response)
                hud.add_ai_message(ai_response)

            return ai_response
        else:
            msg = f"I couldn't find relevant information in your documents for: '{question}'."
            if CHAT_DB_AVAILABLE and hud.current_conversation_id:
                db_add_ai_msg(hud.current_conversation_id, msg)
            return msg

    except Exception as e:
        return f"Document Q&A error: {str(e)}"


def handle_agent_query(text: str) -> str:
    """Handle an agent tool query."""
    if not AGENT_AVAILABLE:
        return "Agent tools are not available."

    try:
        result = ask_with_tools(text)
        response = result.get("response", "No response from agent.")

        # Save to chat DB
        if CHAT_DB_AVAILABLE and hud.current_conversation_id:
            db_add_ai_msg(hud.current_conversation_id, response)
            hud.add_ai_message(response)

        return response
    except Exception as e:
        return f"Agent error: {str(e)}"


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

    print(f"[{get_timestamp()}] No command received. Going back to sleep.")
    update_hud(status='idle')
    return False


# ============================================================
# TEXT MODE FALLBACK
# ============================================================

def text_mode():
    """Run JARVIS in text-only mode when microphone is unavailable."""
    print("\n" + "=" * 60)
    print("  TEXT MODE - Type commands at the prompt")
    print("  Type 'exit' or 'quit' to shutdown")
    print("=" * 60 + "\n")

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

    # Save chat stats
    if CHAT_DB_AVAILABLE:
        try:
            stats = chat_db.get_stats()
            print(f"[{get_timestamp()}] Chat stats: {stats['total_conversations']} conversations, "
                  f"{stats['total_messages']} messages")
        except Exception:
            pass

    # Stop HUD
    hud.stop()

    speak("Session ended. " + summary)
    print(f"[{get_timestamp()}] {summary}")
    print(f"[{get_timestamp()}] JARVIS v4 shutdown complete.")
    print("=" * 60)

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
