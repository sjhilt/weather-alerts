import os
import json
import requests
from gtts import gTTS
import soco

AUDIO_FILE = "alert.mp3"
SEEN_FILE = "seen_alerts.json"

def fetch_alerts(zone_id, user_agent):
    url = f"https://api.weather.gov/alerts/active?zone={zone_id}"
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("features", [])

def get_new_alerts(alerts, seen_ids):
    return [a for a in alerts if a["id"] not in seen_ids]

def text_to_speech(text):
    tts = gTTS(text)
    tts.save(AUDIO_FILE)

def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_ids(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

def get_speaker(name=None, ip=None):
    if ip:
        return soco.SoCo(ip)
    if name:
        speakers = soco.discover()
        for s in speakers or []:
            if s.player_name.lower() == name.lower():
                return s
    return soco.discovery.any_soco()

def play_alert_on_sonos(text, speaker_name=None, speaker_ip=None):
    text_to_speech(text)
    speaker = get_speaker(name=speaker_name, ip=speaker_ip)
    if speaker:
        local_ip = get_local_ip()
        url = f"http://{local_ip}:8000/alert.mp3"
        speaker.volume = 50
        speaker.play_uri(url)
        return True
    return False

def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()