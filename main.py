# ── Imports ──────────────────────────────────────────────────────────────────
import ctypes
import json
import os
import queue
import re
import subprocess
import threading
import time
import math
import random
from datetime import datetime
import sys

import pyaudio
import win32con
import win32gui
import winreg
import psutil
import win32process
from screeninfo import get_monitors
import pyautogui
import audioop
import asyncio
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, IAudioMeterInformation
from vosk import KaldiRecognizer, Model
from difflib import SequenceMatcher

from talkingLogic import get_news_command
from talkingLogic import createAnswer

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

import requests

from gui import CreateBackground, root, ShowMusicOverlay, StartGUILoop, ShowSystemInfoGraph, UpdateTodoList
import gui

def ensure_ollama():
    try:
        requests.get("http://localhost:11434")
    except:
        subprocess.Popen(["ollama", "serve"])
        time.sleep(2)

ensure_ollama()


name = "KURT" #Künstliche Universelle Reaktions-Technologie
not_wanted_wake_words = ["ja"]
debug = False

programmed_cmds = ["minimiere", "minimieren", "öffne", "öffnen", "öffnet", "maximiere", "schließe", "schließen", "verschiebe", "verschieben", "tauschen", "tausche", "tausch", "rückgängig"]

minimize_cmds = [programmed_cmds[0], programmed_cmds[1]]
open_cmds = [programmed_cmds[2], programmed_cmds[3], programmed_cmds[4]]
maximize_cmds = [programmed_cmds[5]]
close_cmds = [programmed_cmds[6], programmed_cmds[7]]
move_cmds = [programmed_cmds[8], programmed_cmds[9]]
switch_cmds = [programmed_cmds[10], programmed_cmds[11], programmed_cmds[12]]
undo_commands = [programmed_cmds[13]]

return_cmd = ["stopp", "stop", "ende", "schnauze", "ruhig"]

speed_of_wave = 5
current_volume = 0
peak_volume = 0
isSpeaking = False

lastCommand = 0
last_hwnd = 0
last_title = ""

load_dotenv()

client_id = os.getenv("CLIENTID")
client_secret = os.getenv("CLIENTSECRET")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-modify-playback-state user-read-playback-state"
))

last_time_talking_to_jarvis = datetime.now()
last_time_talking_delta = datetime.now()
sleepingInterval = 300
current_jarvis_mode = ""

clap_state = {
    "count": 0,
    "first_clap_time": None,
    "peak_start": None,
    "in_peak": False,
}

oldVolume = {}

activeIndexForInnerIndicator = 0
direction_while_talking = 1
direction_while_talking_jarvis = 1

command_prompt = """Classify the user's intent into exactly one category. Reply with ONLY the category number, nothing else.

Categories:
0  = unclear              (nothing fits confidently)

--- To-Do ---
1  = todo_show            (viewing, listing, or asking about existing tasks)
2  = todo_create          (add or save a new task)
3  = todo_delete          (remove or complete a task)

--- Music ---
4  = music_play           (start or resume playback)
5  = music_pause          (pause or stop playback)
6 = music_skip           (skip to the next song)
7 = music_previous       (go back to the previous song)
8 = music_volume_up      (increase the volume)
9 = music_volume_down    (decrease the volume)
10 = music_volume_set     (set volume to a specific value)

--- System ---
11  = system_shutdown_ai   (close or stop the assistant)
12  = system_restart_ai    (restart the assistant)
13  = system_open_program  (launch an application or file)
14 = system_coding_mode   (switch to coding mode)

--- Info ---
15  = info_search          (search the web or google something)
16 = info_time            (ask for the current time)
17 = info_news            (ask for todays news)

Reply with one or two digits only!!!
USER INPUT: """

max_cmds = 17

# ─────────────────────────────────────────────────────────────────────────────
# Monitor Setup
# ─────────────────────────────────────────────────────────────────────────────

active_monitors = get_monitors()
active_monitors_size = []
for i,m in enumerate(active_monitors):
    active_monitors_size.append((i, m.x, m.y))

print(active_monitors_size)

# ─────────────────────────────────────────────────────────────────────────────
# Audio/ Volume Control Setup
# ─────────────────────────────────────────────────────────────────────────────

devices   = AudioUtilities.GetSpeakers()
interface = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume    = interface.QueryInterface(IAudioEndpointVolume)

VK_MEDIA_PLAY_PAUSE  = 0xB3
VK_MEDIA_NEXT_TRACK  = 0xB0
VK_MEDIA_PREV_TRACK  = 0xB1

def press_key(hexKeyCode):
    ctypes.windll.user32.keybd_event(hexKeyCode, 0, 0, 0)
    ctypes.windll.user32.keybd_event(hexKeyCode, 0, 2, 0)

def sound_while_speaking():
    global oldVolume
    sessions = AudioUtilities.GetAllSessions()
    print(f"[DEBUG] Anzahl Sessions: {len(list(sessions))}")
    
    sessions = AudioUtilities.GetAllSessions()  # nochmal holen, list() verbraucht den Iterator
    for session in sessions:
        if session.Process:
            try:
                proc = psutil.Process(session.Process.pid)
                proc_name = proc.name().lower()
                print(f"[DEBUG] Session gefunden: {proc_name} (PID: {session.Process.pid})")

                if "powershell" in proc_name:
                    print(f"[DEBUG] Übersprungen: {proc_name}")
                    continue

                session_volume = session.SimpleAudioVolume
                current = session_volume.GetMasterVolume()
                print(f"[DEBUG] Setze {proc_name} von {current:.2f} auf 0.1")
                oldVolume[session.Process.pid] = current
                session_volume.SetMasterVolume(current * 0.1, None)

            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"[DEBUG] Fehler: {e}")
                continue

def sound_to_before():
    global oldVolume
    sessions = AudioUtilities.GetAllSessions()

    for session in sessions:
        if session.Process:
            try:
                proc = psutil.Process(session.Process.pid)
                proc_name = proc.name().lower()

                if "powershell" in proc_name:
                    continue

                pid = session.Process.pid
                if pid in oldVolume:  # Nur zurücksetzen wenn gespeichert
                    session_volume = session.SimpleAudioVolume
                    session_volume.SetMasterVolume(oldVolume[pid], None)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    oldVolume.clear()

# ─────────────────────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH
# ─────────────────────────────────────────────────────────────────────────────

tts_queue = queue.Queue()

def speak_to_me(content):
    tts_queue.put(content)

tts_volume_level = 0.0

def measure_tts_volume():
    """Läuft im Thread während Jarvis spricht"""
    global tts_volume_level
    while isSpeaking:
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and "powershell" in session.Process.name().lower():
                    meter = session._ctl.QueryInterface(IAudioMeterInformation)
                    tts_volume_level = meter.GetPeakValue()  # 0.0 - 1.0
                    break
            else:
                tts_volume_level = 0.0
        except:
            tts_volume_level = 0.0
        time.sleep(0.03)  # ~30fps
    tts_volume_level = 0.0

def tts_worker():
    global isSpeaking

    while True:
        text = tts_queue.get()
        isSpeaking = True
        sound_while_speaking()
        threading.Thread(target=measure_tts_volume, daemon=True).start()

        subprocess.run([        # ✅ Blockiert bis Sprache fertig!
            "powershell", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = 3; "
            f"$s.Speak('{text}')"
        ], creationflags=subprocess.CREATE_NO_WINDOW)

        last_time_talking_to_jarvis = datetime.now()

        isSpeaking = False
        sound_to_before()

threading.Thread(target=tts_worker, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# Speech-Recognition (VOSK)
# ─────────────────────────────────────────────────────────────────────────────

english_words = ["discord", "spotify", "chrome", "edge", "firefox", "youtube", "google"]

model = Model(r"D:\Programmier Projekte\Python Projekte\Jarvis\vosk-model-small-de-0.15")
rec   = KaldiRecognizer(model, 16000)

model_en = Model(r"D:\Programmier Projekte\Python Projekte\Jarvis\vosk-model-small-en-us-0.15")
rec_en = KaldiRecognizer(model_en, 16000)

mic    = pyaudio.PyAudio()
stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=2048)
stream.start_stream()
subprocess.run(["powershell", "-Command", ""], creationflags=subprocess.CREATE_NO_WINDOW)

def similar(a, b):
    ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return ratio > 0.6   # 60% Ähnlichkeit reicht meist

isLastLineListening = False
def record_text():
    global current_volume, peak_volume
    isLastLineListening = False

    while True:
        data = stream.read(2048, exception_on_overflow=False)

        rms = audioop.rms(data, 2)
        current_volume = rms / 32767
        peak_volume = max(peak_volume, current_volume)

        de_done = rec.AcceptWaveform(data)
        rec_en.AcceptWaveform(data)

        if de_done:
            result_de = json.loads(rec.Result()).get("text", "")
            result_en = json.loads(rec_en.Result()).get("text", "")

            # Englische Wörter aus EN-Ergebnis ersetzen
            words_de = result_de.split()
            words_en = result_en.split()

            for i, word_de in enumerate(words_de):
                for word_en in english_words:
                    # Wenn ein deutsches Wort klingt wie ein englisches → ersetzen
                    if word_en in words_en and similar(word_de, word_en):
                        words_de[i] = word_en

            result_de = " ".join(words_de)
            return result_de
        else:
            if isLastLineListening:
                isLastLineListening = True
                print("Höre:")

def is_wake_word(text):
    for i, word in enumerate(text.split()):
        word = word.lower()
        ratio = SequenceMatcher(None, word, name.lower()).ratio()
        if ratio > .6 and word not in not_wanted_wake_words:
            if debug: print(f"Wake-Word Match: '{word}' → {ratio:.2f}")
            return True, i #Returns if wake word is spoken and the index of the wake word

    return False, -1


# ─────────────────────────────────────────────────────────────────────────────
# Helping functions
# ─────────────────────────────────────────────────────────────────────────────

def text_to_number(text):
    """Wandelt deutschsprachige Zahlwörter in int um."""
    text = text.lower().replace(" ", "")

    base = {
        "null": 0, "eins": 1, "ein": 1, "zwei": 2, "drei": 3,
        "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8,
        "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
        "zwanzig": 20, "dreißig": 30, "vierzig": 40,
        "fünfzig": 50, "sechzig": 60, "siebzig": 70,
        "achtzig": 80, "neunzig": 90, "hundert": 100,
    }

    if text in base:
        return base[text]

    if "und" in text:
        parts = text.split("und")
        if len(parts) == 2:
            return base.get(parts[1], 0) + base.get(parts[0], 0)

    return None

def output_text(text):
    with open("output.txt", "a") as f:
        f.write(text + "\n")

def open_chrome(url, incognito):
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    args   = [chrome, "--incognito", url] if incognito else [chrome, url]
    subprocess.Popen(args)

def get_desired_monitor(command):
    for word in command.strip().split():
        monitor = text_to_number(word)

    if monitor != None: 
        return monitor 
    else: 
        return None

def get_process_name_from_hwnd(hwnd):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        return process.name()
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# Window Management
# ─────────────────────────────────────────────────────────────────────────────

def get_windows():
    windows = []

    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                # Prozessname zum Fenster herausfinden
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    proc_name = process.name().lower()
                except:
                    proc_name = ""
                windows.append((hwnd, title, proc_name))

    win32gui.EnumWindows(enum_handler, None)
    return windows

def get_installed_programs_with_path():
    programs  = []
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    for path in reg_paths:
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        except Exception:
            continue

        for i in range(winreg.QueryInfoKey(reg)[0]):
            try:
                subkey_name  = winreg.EnumKey(reg, i)
                subkey       = winreg.OpenKey(reg, subkey_name)
                name         = winreg.QueryValueEx(subkey, "DisplayName")[0]
                try:
                    install_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                except Exception:
                    install_path = None
                programs.append((name, install_path))
            except Exception:
                pass

    return programs

def get_start_menu_programs():
    paths = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
    ]
    programs = []

    for path in paths:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".lnk"):
                    programs.append((file, os.path.join(root, file)))

    return programs

def get_specific_program_in_startmenu(name):
    paths = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
    ]
    program = None

    for path in paths:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".lnk"):
                    program = file + os.path.join(root, file)

    return program

def _score_match(keyword, title_low, proc_name):
    """Gibt einen Übereinstimmungs-Score zurück."""
    score = 0
    if keyword == title_low:
        score += 100
    if keyword in proc_name:
        score += 80
    if keyword in title_low:
        score += 50
    for word in keyword.split():
        if word in title_low:
            score += 10
    return score

def find_best_window(keyword, already_open):
    keyword = keyword.lower()

    if already_open:
        windows    = get_windows()
        best_match = None
        best_score = 0
        best_title = None

        for hwnd, title, proc_name in windows:
            title_low = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß ]", "", title.lower())
            if debug: print("Vergleiche", keyword, "mit:", title_low)

            score = _score_match(keyword, title_low, proc_name)
            if score > best_score and score > 50:
                best_score = score
                best_match = hwnd
                best_title = title

        if debug: print("best window:", best_title)
        return best_match, best_score

    else:
        if debug: print("Suche nach installiertem Programm...")
        windows    = get_start_menu_programs()
        best_score = 0
        best_path  = None
        best_title = None

        for title, install_path in windows:
            title_low = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß ]", "", title.lower())
            title_low = title_low[:-3]          # .lnk-Endung entfernen
            if debug: print("Vergleiche", keyword, "mit:", title_low)

            score = _score_match(keyword, title_low, "")
            if score > best_score and score > 50:
                best_score = score
                best_path  = install_path

        if debug:
            print("Best Score:", best_score)
            print("Best window:", best_title)
            print("Best match:", best_path)
        return best_path, best_score

def handle_window(window, hwnd, command):
    """
    command: 1 = minimieren | 2 = maximieren | 3 = öffnen/fokussieren | 4 = schließen | 5 = move | 6 = change monitor
    """
    global last_hwnd
    global lastCommand

    #hwnd = find_best_window(window, True)
    print(hwnd)

    if hwnd:
        if command == 1:
            win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MINIMIZE, 0)

            title = get_process_name_from_hwnd(hwnd)

            speak_to_me(f"Ich habe {title} minimiert")
        elif command == 2:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

            title = get_process_name_from_hwnd(hwnd)

            speak_to_me(f"Ichh habe {title} maximiert")
        elif command == 3:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

            title = get_process_name_from_hwnd(hwnd)

            speak_to_me(f"Ich habe {title} geöffnet")
        elif command == 4:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

            title = get_process_name_from_hwnd(hwnd)

            speak_to_me(f"Ich habe {title} geschlossen")
        elif command == 5:
            monitor_to_move = int(hwnd[-1:])
            best_hwnd = int(hwnd[:-1])
            win32gui.ShowWindow(best_hwnd, win32con.SW_RESTORE)
            time.sleep(.1)

            # Erst aktuelle Größe holen
            rect = win32gui.GetWindowRect(best_hwnd)
            breite = rect[2] - rect[0]
            hoehe = rect[3] - rect[1]

            # Dann verschieben mit gleicher Größe
            win32gui.MoveWindow(
                best_hwnd,
                active_monitors_size[monitor_to_move][1],  # x
                active_monitors_size[monitor_to_move][2],  # y
                breite,
                hoehe,
                True
            )
                            
            time.sleep(0.5)
            handle_window("", best_hwnd, 2)
            print("Neue Position:", win32gui.GetWindowRect(best_hwnd))

            title = get_process_name_from_hwnd(hwnd)

            speak_to_me(f"Ich habe {title} auf Monitor {monitor_to_move} verschoben")
        elif command == 6:
            hwnd_1 = ""
            hwnd_2 = ""
            for i, char in enumerate(hwnd):
                if char == "/":
                    hwnd_2 = hwnd[i + 1:]
                    break
                hwnd_1 += char

            hwnd_1 = int(hwnd_1)
            hwnd_2 = int(hwnd_2)

            rect_1 = win32gui.GetWindowRect(hwnd_1)
            rect_2 = win32gui.GetWindowRect(hwnd_2)

            win32gui.MoveWindow(
                hwnd_1,
                rect_2[0],  # x
                rect_2[1],  # y
                rect_2[2] - rect_2[0],  # breite
                rect_2[3] - rect_2[1],  # höhe
                True
            )

            win32gui.MoveWindow(
                hwnd_2,
                rect_1[0],  # x
                rect_1[1],  # y
                rect_1[2] - rect_1[0],  # breite
                rect_1[3] - rect_1[1],  # höhe
                True
            )

            title_1 = get_process_name_from_hwnd(hwnd_1)
            title_2 = get_process_name_from_hwnd(hwnd_2)

            speak_to_me(f"Ich habe {title_1} mit {title_2} getauscht.")
                
        last_hwnd = hwnd
        lastCommand = command
    else:
        if command == 3:
            try:
                os.startfile(window)

                speak_to_me("Ich habe das Programm gestartet")
            except Exception:
                if debug: print("Ich kann dein Programm nicht öffnen.")
                if debug: speak_to_me("Ich kann dein Programm nicht öffnen.")
        else:
            if debug: print("Ich habe kein Fenster gefunden, das zu deinem Befehl passt.")
            if debug: speak_to_me("Ich habe kein Fenster gefunden, das zu deinem Befehl passt.")


# ─────────────────────────────────────────────────────────────────────────────
# OVERLAY (tkinter)
# ─────────────────────────────────────────────────────────────────────────────

def show_status(text):
    global reset_pending, reset_time
    #canvas.itemconfig(overlay_label, text=text)
    reset_pending = True
    reset_time    = time.time() + 1


# ─────────────────────────────────────────────────────────────────────────────
# GUI Handler
# ─────────────────────────────────────────────────────────────────────────────

offset = 0

"""def ChangeInnerCircle(color):
    canvas.itemconfig(capsule)

def ChangeFirstRing(current_ring_angle, speed_of_ring, color):
    canvas.itemconfig(first_ring, start=current_ring_angle + speed_of_ring)

def ChangeFirstRingIndicators(volume, index, rotation):
    volume_multiplier = max(1, min(volume * 100, 1.1))

    for i in range(num_lines):
        angle = math.radians(i * (360 / num_lines) + rotation)
        x1 = center_of_jarvis_x + first_ring_indicator_inner_radius * math.cos(angle)
        y1 = center_of_jarvis_y + first_ring_indicator_inner_radius * math.sin(angle)
        x2 = center_of_jarvis_x + (first_ring_indicator_outer_radius * volume_multiplier) * math.cos(angle)
        y2 = center_of_jarvis_y + (first_ring_indicator_outer_radius * volume_multiplier) * math.sin(angle)

        canvas.coords(first_ring_indicators[i], x1, y1, x2, y2)

def ChangeSecondRing(current_ring_angle, speed_of_ring):
    canvas.itemconfig(second_ring, start=current_ring_angle + speed_of_ring)"""

# ─────────────────────────────────────────────────────────────────────────────
# Command-HANDLER
# ─────────────────────────────────────────────────────────────────────────────
async def get_media():
    sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = sessions.get_current_session()
    
    if session:
        info = await session.try_get_media_properties_async()
        ShowMusicOverlay(info.title, info.artist)
    else:
        print("Nothing playing")

def handle_easter_egg(command):
    print("Alles klar Boss, 5 gegen Willi aktiv!")
    speak_to_me("Alles klar Boss, 5 gegen Willi aktiv! Viel Spaß beim goonen!")
    show_status("5 gegen Willi aktiv!")
    time.sleep(2)
    open_chrome(
        "https://www.google.com/search?sca_esv=c0203a4e5d3b1bdc&sxsrf=ANbL-n5D1Qrd06NH-YyPi_1C-gIJ3n5yug:1777216186505"
        "&udm=2&fbs=ADc_l-YGrpJMQtvjQ6h14rj-dfIrbPkd_Upq68wJVnEIgo2PwwVFCyGcL10_P-T-A7nI0VUQfnO-1zVwcEZUIojnWKF7zO33A_35bxn8s"
        "VeWUslVmy98IimCwcbo-tYS5NGFcHbrwuP4s5Cxp8HZYUest7lxSt9kSq6lrben7gkP3JZLPOBz7MaOd4ZloPchD5sQZKvWrqQo"
        "&q=Ryan+reynolds&sa=X&ved=2ahUKEwjXgvGb5ouUAxWG97sIHQUMHvwQtKgLegQIHhAB&biw=1920&bih=911&dpr=1",
        True,
    )

def handle_search(command):
    search_query = createAnswer(f"""
                                    You are an AI assistant specialized in converting conversational voice-to-text transcripts into clean, optimized web search queries.

                                    Analyze the following spoken transcript and output ONLY the single best search query. Follow these strict rules:
                                    1. Strip out all conversational filler, pleasantries, or meta-commentary (e.g., "Hey Google", "Can you search for", "I want to find", "um", "uh").
                                    2. Correct any obvious phonetic typos or speech-to-text misunderstandings based on the context.
                                    3. Keep the query concise, using only the essential keywords needed for a modern search engine.
                                    4. Output nothing but the final search query text. Do not include quotes, explanations, intro text, or markdown formatting.

                                    Spoken Transcript: "{command}"
                                    Search Query(in the same language as the transcript):
                                """)
    print(f"Suche nach: {search_query}")

    open_chrome(f"https://www.google.com/search?q={search_query.replace(' ', '+')}", False)

def handle_window_commands(command):
    """
    command: 1 = minimieren | 2 = maximieren | 3 = öffnen/fokussieren | 4 = schließen | 5 = move | 6 = change monitor
    """
    global last_title

    cmd_low = command.lower()

    #Check if any of the programmed commands are in the recognized command
    for cmd in programmed_cmds:
        if cmd in cmd_low:
            print(f"Erkannter Befehl: {cmd}")

            if cmd in undo_commands:
                if lastCommand == 1 or lastCommand == 2:
                    handle_window("", last_hwnd, 3)
                elif lastCommand == 3:
                    handle_window("", last_hwnd, 3)
                elif lastCommand == 4:
                    handle_window(last_title, None, 3)
                break

            #Strip out everything but the desired program name
            for word in cmd_low.strip().split():
                if word.lower() in programmed_cmds:
                    cmd_low = cmd_low.replace(word, "")
            best_score = 0
            for word in cmd_low.strip().split():
                hwnd, score = find_best_window(word, True)
                if score > best_score:
                    best_score = score
                    best_hwnd = hwnd
                    best_title = word
            cmd_low = cmd_low.replace(best_title, "")
            print("Bestes Fenster: ", best_title)
            print("Remaninung command: ", cmd_low)

            try:
                if best_score > 50:
                    print(f"Bestes Fenster: {best_hwnd} mit Score {best_score}")

                    if cmd in minimize_cmds:
                        show_status(f"Minimiere: {best_title}")
                        handle_window("", best_hwnd, 1)
                    elif cmd in open_cmds:
                        show_status(f"Öffne: {best_title}")
                        handle_window("", best_hwnd, 3)
                    elif cmd in maximize_cmds:
                        show_status(f"Maximiere: {best_title}")
                        handle_window("", best_hwnd, 2)
                    elif cmd in close_cmds:
                        show_status(f"Schließe: {best_title}")
                        handle_window("", best_hwnd, 4)
                    elif cmd in move_cmds:
                        monitor_to_move = get_desired_monitor(cmd_low)

                        try:
                            handle_window("", str(best_hwnd) + str(monitor_to_move), 5)  # attach desired monitor to hwnd so move function can strip it
                            show_status(f"Verschiebe: {best_title} zu Monitor {monitor_to_move}")
                        except Exception as e:
                            print("Konnte ich nicht verschieben: ", e)
                    elif cmd in switch_cmds:
                        #find second window in name

                        best_score_2 = 0
                        for word in cmd_low.strip().split():
                            hwnd, score = find_best_window(word, True)
                            print("Score win2: ", word, score)
                            if score > best_score_2:
                                best_score_2 = score
                                best_hwnd_2 = hwnd
                                best_title_2 = word
                        print("Bestes Fenster 2: ", best_title_2)
                        
                        combined_hwnd = str(best_hwnd) + "/" + str(best_hwnd_2)

                        handle_window("", combined_hwnd, 6)
                        show_status(f"Tausche: {best_title} mit: {best_title_2}")

                    last_title = best_title
                else:
                    print("Kein passendes Fenster gefunden.")
                    speak_to_me("Ich konnte kein passendes Fenster finden. Soll ich stattdessen versuchen, das Programm zu öffnen?")
                    exit()

                    if cmd in open_cmds:
                        for word in cmd_low.strip().split():
                            if word.lower() in programmed_cmds:
                                cmd_low = cmd_low.replace(word, "")
                        best_score = 0
                        for word in cmd_low.strip().split():
                            path, score = find_best_window(word, False)
                            if score > best_score:
                                best_score = score
                                best_path = path

                        show_status(f"Öffne: {best_path}")
                        handle_window(best_path, None, 3)
            except Exception as e:
                print("Fehler bei der Programmverwaltung:", e)
                speak_to_me("Entschuldigung, ich konnte das Programm nicht finden oder verwalten.")

            return True
    return False

def handle_time(command):
    current_time = time.strftime("%H:%M")
    print(f"Es ist {current_time}.")
    speak_to_me(f"Es ist {current_time}.")
    show_status(f"Es ist {current_time}.")

def handle_youtube(command):
    print("Öffne YouTube...")
    speak_to_me("Öffne YouTube")
    show_status("Öffne YouTube...")
    open_chrome("https://www.youtube.com", False)

def handle_news(command):
    show_status("Lese Nachrichten...")
    buffer     = ""
    last_flush = time.time()

    print("[NEWS] Starte Generator...")
    for token in get_news_command():
        print(token, end="", flush=True)
        buffer += token

        if token.endswith((".", "!", "?")):
            speak_to_me(buffer.strip())
            show_status(buffer.strip())
            buffer     = ""
            last_flush = time.time()

    print(f"[NEWS] Restbuffer: '{buffer.strip()}'")
    if buffer.strip():

        speak_to_me(buffer.strip())
    print("[NEWS] Fertig.")

def handle_media(command):
    cmd_low = command.lower()
    if "nächstes lied" in cmd_low or "nächster track" in cmd_low or "skip" in cmd_low:
        show_status("Nächstes Lied ⏭")
        press_key(VK_MEDIA_NEXT_TRACK)
        time.sleep(0.5)
        asyncio.run(get_media())
        return True
    elif "vorheriges lied" in cmd_low or "vorheriger track" in cmd_low or "back" in cmd_low:
        show_status("Vorheriges Lied ⏮")
        press_key(VK_MEDIA_PREV_TRACK)
        time.sleep(0.5)
        asyncio.run(get_media())
        return True
    elif "pause" in cmd_low or "play" in cmd_low:
        show_status("Play/Pause ⏯")
        press_key(VK_MEDIA_PLAY_PAUSE)
        time.sleep(0.5)
        asyncio.run(get_media())
        return True
    return False

def handle_volume(command):
    cmd_low = command.lower()
    if "lauter" in cmd_low:
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
        show_status("🔊 Lauter")
        return True
    elif "leiser" in cmd_low:
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)
        show_status("🔉 Leiser")
        return True

    if "lautstärke" in cmd_low:
        try:
            desired_volume = None
            for word in cmd_low.split():
                num = text_to_number(word)
                print(num)
                if num is not None:
                    desired_volume = num
            if desired_volume is not None:
                volume.SetMasterVolumeLevelScalar(desired_volume / 100, None)
                show_status(f"🔊 Lautstärke: {desired_volume}%")
        except Exception:
            print("Unklarer Lautstärke-Befehl.")
            speak_to_me("Unklarer Lautstärke-Befehl. Bitte lauter oder leiser sagen.")
        return True
    return False

def handle_modes(command):
    cmd_low = command.lower()

    if ("aktivieren" in cmd_low or "aktiviere" in cmd_low) and "programmier modus" in cmd_low:
        if "letze" in cmd_low or "letzten" in cmd_low or "letzter" in cmd_low:
            print("Letzter Programmier Modus aktiviert!")
            speak_to_me("Letzter Programmier Modus aktiviert! Viel Spaß beim Programmieren!")

            # Song starten (URI)
            devices = sp.devices()
            device_id = devices['devices'][0]['id']

            sp.start_playback(
                device_id=device_id,
                uris=["spotify:track:08mG3Y1vljYA6bvDt4Wqkj"]
            )

            subprocess.Popen("code --new-window", shell=True)
            open_chrome("https://claude.ai", False)
            time.sleep(2)   #wait till window is open

            hwnd, score = find_best_window("Visual Studio Code", True)

            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        else:
            show_status("Programmier Modus aktiviert!")
            speak_to_me("Programmier Modus aktiviert! Viel Spaß beim Programmieren!")

            # Song starten (URI)
            devices = sp.devices()
            device_id = devices['devices'][0]['id']

            sp.start_playback(
                device_id=device_id,
                uris=["spotify:track:08mG3Y1vljYA6bvDt4Wqkj"]
            )

            subprocess.Popen("code", shell=True)
            open_chrome("https://claude.ai", False)
            time.sleep(2)   #wait till window is open

            hwnd, score = find_best_window("Visual Studio Code", True)

            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

        return True
    elif ("deaktivieren" in cmd_low or "deaktiviere" in cmd_low) and "programmier modus" in cmd_low:
        show_status("Programmier Modus deaktiviert!")
        speak_to_me("Programmier Modus deaktiviert! Willkommen zurück im Alltag!")
        return True

    return False

def get_todos():
    all_todos = subprocess.run(
        ["todo", "-list"],
        capture_output=True,
        text=True,
        encoding="cp850"
    )
    UpdateTodoList(all_todos.stdout)

def dispatch_command(command):
    detected_a_cmd = False
    """Verteilt den erkannten Befehl an die passende Handler-Funktion."""
    cmd_low = command.lower()
    last_word = cmd_low.split()[-1] if cmd_low.split() else ""

    if "komplett" in cmd_low and "aus" in cmd_low:
        print("Programm beendet.")
        return False                       # Signalisiert Schleifenende
    
    if last_word in return_cmd:
        print("Ich halte meinen Mund")
        return True
    
    if last_word == "neustart":
        subprocess.Popen('start cmd /k "timeout /t 5 && python "D:\Programmier Projekte\Python Projekte\Jarvis\main.py""', shell=True)
        os.system("taskkill /f /pid " + str(os.getpid()))

    if "fünf gegen willi" in cmd_low or "5 gegen willi" in cmd_low:
        handle_easter_egg(command)
        detected_a_cmd = True

    if cmd_low.startswith("suche nach"):
        handle_search(command)
        detected_a_cmd = True

    detected_a_cmd = detected_a_cmd or handle_window_commands(command)

    if "wie spät ist es" in cmd_low:
        handle_time(command)
        detected_a_cmd = True

    if "youtube schauen" in cmd_low:
        handle_youtube(command)
        detected_a_cmd = True

    if "heute" in cmd_low and "nachrichten" in cmd_low:
        handle_news(command)
        detected_a_cmd = True

    if "toggle" in cmd_low and "mute" in cmd_low and "discord" in cmd_low:
        pyautogui.typewrite('^', interval=0.05)
        detected_a_cmd = True

    if "todo" in cmd_low and "neue" in cmd_low:
        new_todo = createAnswer(f"Extrahiere die Kernaufgabe aus diesem Satz in maximal 3 Wörtern. Antworte NUR mit den Wörtern, kein 'Aufgabe:', keine Erklärung, nichts anderes.: {cmd_low}")
        print(f"[INFO] Erstelle Todo: {new_todo}")
        subprocess.run(
            ["todo", "-create", new_todo]
        )
        
        get_todos()
        detected_a_cmd = True

    if "alle" in cmd_low and "todo" in cmd_low:
        get_todos()

        detected_a_cmd = True

    detected_a_cmd = detected_a_cmd or handle_media(command)
    detected_a_cmd = detected_a_cmd or handle_volume(command)
    detected_a_cmd = detected_a_cmd or handle_modes(command)

    if not detected_a_cmd:
        AskAiForResponse(command)

    #output_text(command)
    return True                             # Weiterlaufen

def clap_detection_loop():
    global last_time_talking_to_jarvis, peak_volume
    s = clap_state

    while True:
        is_loud = peak_volume > 0.06
        peak_volume = 0  # nach jedem Check zurücksetzen

        # Steigende Flanke
        if is_loud and not s["in_peak"]:
            s["in_peak"] = True
            s["peak_start"] = datetime.now()
            print(f"Klang erkannt")

        # Fallende Flanke
        if not is_loud and s["in_peak"]:
            s["in_peak"] = False
            duration = (datetime.now() - s["peak_start"]).total_seconds()
            print(f"Klang ende – Dauer: {duration:.3f}s")

            if duration < 0.15:  # kurzes Geräusch = Klaps
                now = datetime.now()
                if s["count"] == 0:
                    print("Erster Klaps!")
                    s["count"] = 1
                    s["first_clap_time"] = now
                elif s["count"] == 1:
                    gap = (now - s["first_clap_time"]).total_seconds()
                    print(f"Gap: {gap:.3f}s")
                    if 0.1 < gap < 0.8:
                        print("Doppelklatschen erkannt!")
                        last_time_talking_to_jarvis = datetime.now()
                        s["count"] = 0
                        s["first_clap_time"] = None
                    else:
                        s["count"] = 1
                        s["first_clap_time"] = now

        # Timeout
        if s["count"] == 1 and s["first_clap_time"]:
            if (datetime.now() - s["first_clap_time"]).total_seconds() > 1.0:
                print("Timeout")
                s["count"] = 0
                s["first_clap_time"] = None

        time.sleep(0.005)  # 5ms – viel schneller als 30ms

#threading.Thread(target=clap_detection_loop, daemon=True).start()

def AskAiForResponse(command):
    print("I am too stupid, let me ask someone smarter")
    answer = createAnswer(command)
    speak_to_me(answer)

def log(text):
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")
        f.flush()

session = requests.Session()
def AskOllamaWhatToDo(command):
    cmd_low = command.lower()

    raw = createAnswer(command_prompt + command).strip()

    cmd = int(''.join(filter(str.isdigit, raw)))
    if cmd > max_cmds:
        cmd = 0

    print(f"Raw: '{raw}' → cmd: {cmd}")

    if int(cmd) == 1:
        get_todos()

    elif int(cmd) == 2:
        new_todo = createAnswer(f"Extrahiere die Kernaufgabe aus diesem Satz in maximal 3 Wörtern. Antworte NUR mit den Wörtern, kein 'Aufgabe:', keine Erklärung, nichts anderes.: {command}")
        print(f"[INFO] Erstelle Todo: {new_todo}")
        subprocess.run(
            ["todo", "-create", new_todo]
        )
        
        get_todos()

    elif int(cmd) == 3:
        raw = createAnswer("Just return the number in the prompt as a digit. Return nothing else. Prompt:" + cmd_low)

        todo_to_delete = ''.join(filter(str.isdigit, raw))
        print(f"[DEBUG] Deleting todo {todo_to_delete}")

        subprocess.run(
            ["todo", "-delete", todo_to_delete]
        )

        get_todos()

    elif int(cmd) == 4 or int(cmd) == 5:
        press_key(VK_MEDIA_PLAY_PAUSE)
        time.sleep(0.5)
        asyncio.run(get_media())

    elif int(cmd) == 6:
        press_key(VK_MEDIA_NEXT_TRACK)
        time.sleep(0.5)
        asyncio.run(get_media())

    elif int(cmd) == 7:
        press_key(VK_MEDIA_PREV_TRACK)
        time.sleep(0.5)
        asyncio.run(get_media())

    elif int(cmd) == 8:
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)

    elif int(cmd) == 9:
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)

    elif int(cmd) == 10:
        try:
            desired_volume = None
            for word in cmd_low.split():
                num = text_to_number(word)
                print(num)
                if num is not None:
                    desired_volume = num
            if desired_volume is not None:
                volume.SetMasterVolumeLevelScalar(desired_volume / 100, None)
        except Exception:
            print("Unklarer Lautstärke-Befehl.")
            speak_to_me("Unklarer Lautstärke-Befehl. Bitte lauter oder leiser sagen.")

    elif int(cmd) == 11:
        print("Programm beendet.")

    elif int(cmd) == 12:
        subprocess.Popen('start cmd /k "timeout /t 5 && python "D:\Programmier Projekte\Python Projekte\Jarvis\main.py""', shell=True)
        os.system("taskkill /f /pid " + str(os.getpid()))

    elif int(cmd) == 13:
        handle_window_commands(cmd_low)

    elif int(cmd) == 14:
        print("Letzter Programmier Modus aktiviert!")
        speak_to_me("Letzter Programmier Modus aktiviert! Viel Spaß beim Programmieren!")

        # Song starten (URI)
        devices = sp.devices()
        device_id = devices['devices'][0]['id']

        sp.start_playback(
            device_id=device_id,
            uris=["spotify:track:08mG3Y1vljYA6bvDt4Wqkj"]
        )

        subprocess.Popen("code --new-window", shell=True)
        open_chrome("https://claude.ai", False)
        time.sleep(2)   #wait till window is open

        hwnd, score = find_best_window("Visual Studio Code", True)

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        
    elif int(cmd) == 15:
        handle_search(command)

    elif int(cmd) == 16:
        handle_time(command)

    elif int(cmd) == 17:
        handle_news(command)

    gui.current_state = 0

# ─────────────────────────────────────────────────────────────────────────────
# HAUPTSCHLEIFE
# ─────────────────────────────────────────────────────────────────────────────
def main_loop():
    global speed_of_wave, last_time_talking_to_jarvis, last_time_talking_delta, current_jarvis_mode

    CreateBackground(30)
    asyncio.run(get_media())
    ShowSystemInfoGraph()
    StartGUILoop()

    speak_to_me(f"Hallo ich bin {name}, dein persönlicher Assistent. Sage {name} um ihn zu aktivieren.")

    lastSongCheck = time.time()
    while True:
        if time.time() - lastSongCheck > 5:
            asyncio.run(get_media())
            lastSongCheck = time.time()

        text = record_text()

        isAwakening, position = is_wake_word(text)

        if isAwakening:
            print("[DEBUG] Wake word erkannt!")
            gui.current_state = 1
            last_time_talking_to_jarvis = datetime.now()
            if current_jarvis_mode != "sleeping":
                command = " ".join(text.strip().split()[position + 1:])
                print("Command:", command)

                running = True
                AskOllamaWhatToDo(command)

                #running = dispatch_command(command)
                if not running:
                    break

# Thread starten
threading.Thread(target=main_loop, daemon=True).start()
root.mainloop()