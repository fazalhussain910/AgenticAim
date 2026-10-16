"""
local_voice_coach.py — AgenticAim Real-Time Voice AI Esports Coach
===================================================================
Hands-Free, Ultra-Low-Latency Voice AI Coach for Competitive FPS Games.

Architecture:
  [Player Headset Mic]
         │
         ▼ (SpeechRecognition)
  [Transcribed Player Query]
         │
         ▼
  [AgenticAim LangGraph / Qdrant Hybrid RAG & AMD Token Factory]
         │
         ▼ (2-Sentence Precision Coaching)
  [Microsoft Edge Neural TTS: en-US-ChristopherNeural (+15% Rate)]
         │
         ▼ (pygame.mixer)
  [Player Headset Audio Output]

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

import asyncio
import os
import sys
import time
import tempfile
import logging
from typing import Any, Optional

try:
    import msvcrt
except ImportError:
    msvcrt = None

# ── Force UTF-8 output on Windows terminal ────────────────────────────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Suppress verbose internal loggers ─────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
for noisy in ("openai", "httpx", "httpcore", "urllib3", "qdrant_client", "edge_tts", "pygame"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

# Import AgenticAim core AI Brain
from graph import ask_ai_coach
from tracker import get_hardware_spec

# Voice & Audio Libraries
try:
    import speech_recognition as sr  # type: ignore
    from speech_recognition.exceptions import (  # type: ignore
        WaitTimeoutError,
        UnknownValueError,
        RequestError,
    )
except ImportError:
    import speech_recognition as sr  # type: ignore
    WaitTimeoutError = getattr(sr, "WaitTimeoutError", Exception)  # type: ignore
    UnknownValueError = getattr(sr, "UnknownValueError", Exception)  # type: ignore
    RequestError = getattr(sr, "RequestError", Exception)  # type: ignore

import edge_tts  # type: ignore

# Suppress Pygame welcome banner and load mixer
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame  # type: ignore
import pygame.mixer  # type: ignore


# ==============================================================================
# CONFIGURATION
# ==============================================================================
COACH_VOICE: str = "en-US-AriaNeural"         # Crisp, natural professional female esports coach
COACH_RATE: str  = "+12%"                     # Fast, natural esports comms tempo
TEMP_AUDIO_DIR: str = tempfile.gettempdir()


# ==============================================================================
# TERMINAL UI THEME & FORMATTING (HACKER / ESPORTS CYBERPUNK)
# ==============================================================================
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

def print_banner():
    banner = f"""{CYAN}
  █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗ █████╗ ██╗███╗   ███╗
 ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝██╔══██╗██║████╗ ████║
 ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║     ███████║██║██╔████╔██║
 ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║     ██╔══██║██║██║╚██╔╝██║
 ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗██║  ██║██║██║ ╚═╝ ██║
 ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝
              {BOLD}[ REAL-TIME NEURAL VOICE AI ESPORTS COACH ]{RESET}
               {GREEN}⚡ Powered by AMD Token Factory & Qdrant Cloud{RESET}
"""
    print(banner)

    hw = get_hardware_spec()
    print(f" {DIM}┌──────────────────────────────────────────────────────────────┐{RESET}")
    print(f" {DIM}│{RESET}  {BOLD}SYSTEM MONITOR:{RESET} CPU: {hw['cpu_name'][:30]:<30}  {DIM}│{RESET}")
    print(f" {DIM}│{RESET}  {BOLD}AUDIO ENGINE:{RESET}   Edge Neural TTS ({COACH_VOICE})  {DIM}│{RESET}")
    print(f" {DIM}│{RESET}  {BOLD}CLOUD OFFLOAD:{RESET}  100% LLM & Vision on AMD Cloud API            {DIM}│{RESET}")
    print(f" {DIM}└──────────────────────────────────────────────────────────────┘{RESET}\n")


# ==============================================================================
# TEXT-TO-SPEECH (TTS) AUDIO SYNTHESIS & PLAYBACK
# ==============================================================================
async def _synthesize_edge_tts(text: str, output_path: str):
    """Generate high-quality neural voice MP3 via Microsoft Edge TTS."""
    communicate = edge_tts.Communicate(text, voice=COACH_VOICE, rate=COACH_RATE)
    await communicate.save(output_path)


def speak_coach_response(text: str):
    """
    Synthesize text to speech using edge-tts and play it instantly using pygame.
    Ensures safe playback and clean temp file deletion.
    """
    if not text.strip():
        return

    temp_mp3 = os.path.join(TEMP_AUDIO_DIR, f"coach_voice_{int(time.time() * 1000)}.mp3")

    try:
        # Run async edge_tts in event loop
        asyncio.run(_synthesize_edge_tts(text, temp_mp3))

        # Initialize pygame mixer if not already active
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(temp_mp3)
        pygame.mixer.music.play()

        # Wait until playback finishes
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

        # Unload music so file lock is released
        pygame.mixer.music.unload()

    except Exception as e:
        print(f" {YELLOW}[Audio Warning]{RESET} TTS playback issue ({e}). Continuing text display.")
    finally:
        # Clean up temporary audio file
        if os.path.exists(temp_mp3):
            try:
                os.remove(temp_mp3)
            except Exception:
                pass


# ==============================================================================
# SPEECH-TO-TEXT (STT) MICROPHONE CAPTURE
# ==============================================================================
def listen_to_mic(recognizer: Any, microphone: Optional[Any]) -> Optional[str]:
    """
    Listens to the default audio input device and converts speech to text.
    Returns the transcribed text string or None if speech was unintelligible.
    """
    if microphone is None:
        return None

    with microphone as source:
        # Adjust for ambient background room noise for 0.4s
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        print(f" {CYAN}🎙️  [LISTENING...]{RESET} {DIM}Speak clearly into your mic (say 'exit' to quit)...{RESET}", flush=True)

        try:
            # 5-second phrase limit prevents infinite hanging in noisy rooms
            audio = recognizer.listen(source, timeout=6.0, phrase_time_limit=10.0)
        except (WaitTimeoutError, Exception) as e:
            if isinstance(e, WaitTimeoutError):
                return None
            print(f" {YELLOW}[Mic Alert]{RESET} Listen error: {e}")
            return None

    try:
        print(f" {MAGENTA}⚡ [TRANSCRIBING AUDIO...]{RESET}", flush=True)
        # Google Speech Recognition (free, reliable, built into SpeechRecognition)
        text = recognizer.recognize_google(audio)
        return text.strip()
    except UnknownValueError:
        print(f" {DIM}   [?] Speech not recognized. Try speaking closer to your mic.{RESET}")
        return None
    except RequestError as e:
        print(f" {RED}[!] STT Service connection error:{RESET} {e}")
        return None


# ==============================================================================
# MAIN REAL-TIME VOICE COACH LOOP
# ==============================================================================
def run_voice_coach():
    """Main interactive terminal loop combining Voice Input + AMD RAG + Neural TTS."""
    print_banner()

    recognizer = sr.Recognizer()  # type: ignore
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    # Check for working microphone
    mic = None
    try:
        mic = sr.Microphone()  # type: ignore
        # Test access
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
        print(f" {GREEN}✔ Microphone detected and calibrated successfully.{RESET}")
    except Exception as e:
        print(f" {YELLOW}⚠️  No default microphone accessible ({e}).{RESET}")
        print(f" {YELLOW}   Don't worry! You can type your questions and hear the Coach speak!{RESET}\n")
        mic = None

    # Interactive Input Mode Selector
    print(f" {BOLD}Select Input Mode:{RESET}")
    print(f"   {CYAN}[1]{RESET} 🎙️  Headset Mic Mode (Speak hands-free)")
    print(f"   {CYAN}[2]{RESET} ⌨️  Keyboard Mode (Type questions, hear Coach voice response)")
    
    mode_choice = "1"
    if mic is not None:
        try:
            raw_choice = input(f"\n {BOLD}Choose [1/2] (Default: 1): {RESET}").strip()
            if raw_choice in ("1", "2"):
                mode_choice = raw_choice
        except (EOFError, KeyboardInterrupt):
            return
    else:
        mode_choice = "2"

    use_mic = (mode_choice == "1" and mic is not None)
    if use_mic:
        print(f"\n {GREEN}✔ Mic mode active.{RESET} Speak clearly when you see {CYAN}[LISTENING...]{RESET}\n")
    else:
        print(f"\n {GREEN}✔ Keyboard mode active.{RESET} Type your questions and the Coach will speak back!\n")

    # Initial Coach Greeting
    intro_text = "Coach AgenticAim online and tuned in. What's the battle plan?"
    print(f" {BOLD}{GREEN}Coach:{RESET} {intro_text}")
    speak_coach_response(intro_text)

    chat_history = []

    while True:
        user_query = None

        if use_mic:
            user_query = listen_to_mic(recognizer, mic)
            if not user_query:
                # Give a quick option to type if mic missed the audio
                print(f" {DIM}   (Speak again, or press any key to type your question below){RESET}")
                try:
                    if msvcrt and msvcrt.kbhit():
                        user_query = input(f"\n {BOLD}{CYAN}You (Type):{RESET} ").strip()
                except Exception:
                    pass

        if not user_query:
            if not use_mic:
                try:
                    user_query = input(f"\n {BOLD}{CYAN}You:{RESET} ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
            else:
                continue

        if not user_query:
            continue

        print(f"\n {BOLD}{CYAN}You:{RESET} \"{user_query}\"")

        # Exit command
        if user_query.lower() in ("exit", "quit", "stop", "bye", "goodbye"):
            farewell = "Session concluded. Keep that crosshair at head height and click heads!"
            print(f"\n {BOLD}{GREEN}Coach:{RESET} {farewell}")
            speak_coach_response(farewell)
            break

        # ── Step 2: Query LangGraph RAG & AMD Token Factory ──────────────────
        print(f" {YELLOW}🧠 [COACH IS THINKING...]{RESET} {DIM}(Querying Qdrant Cloud RAG & AMD Token Factory){RESET}", flush=True)
        t0 = time.perf_counter()

        try:
            res = ask_ai_coach(user_message=user_query, chat_history=chat_history)
            reply = res.get("reply", "").strip()
            is_rag = res.get("is_rag_verified", False)
            sources = res.get("sources", [])
            hw = res.get("hardware_status", {})
            elapsed = time.perf_counter() - t0

            # Display RAG & Hardware status badges
            rag_badge = f"{GREEN}💡 [Verified by RAG: Qdrant Cloud]{RESET}" if is_rag else f"{DIM}[General Base]{RESET}"
            hw_badge  = f"{GREEN}{hw.get('safety_badge', '')}{RESET}" if hw.get('is_safe', True) else f"{RED}{hw.get('safety_badge', '')}{RESET}"

            print(f" {rag_badge}  {hw_badge}  {DIM}(Inference: {elapsed:.2f}s){RESET}")
            if sources:
                print(f" {DIM}   Sources: {', '.join(sources[:2])}{RESET}")

            # Display clean coach text
            print(f" {BOLD}{GREEN}Coach:{RESET} {reply}\n")

            # ── Step 3: Neural Voice Synthesis & Audio Playback ──────────────
            print(f" {CYAN}🗣️  [COACH SPEAKING...]{RESET} {DIM}(Voice: {COACH_VOICE}){RESET}", flush=True)
            speak_coach_response(reply)

            # Update conversation memory
            chat_history.append({"role": "user", "content": user_query})
            chat_history.append({"role": "assistant", "content": reply})

        except Exception as e:
            print(f" {RED}[!] AI Coach pipeline error:{RESET} {e}")
            fallback_msg = "My comms dropped momentarily. Keep your crosshair centered and let's go again."
            print(f" {BOLD}{GREEN}Coach:{RESET} {fallback_msg}\n")
            speak_coach_response(fallback_msg)

    print(f"\n {CYAN}════════════════════════════════════════════════════════════════{RESET}")
    print(f"  {BOLD}Voice Coach session closed.{RESET} Good luck in your tournament!")
    print(f" {CYAN}════════════════════════════════════════════════════════════════{RESET}\n")


if __name__ == "__main__":
    try:
        run_voice_coach()
    except KeyboardInterrupt:
        print("\n\n [Coach] Offline. Session interrupted by user.")
