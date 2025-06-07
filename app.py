import os
import json
import threading
import time
import socket
import requests
import pychromecast
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from gtts import gTTS
import soco

# ===== Configuration =====
AUDIO_FILE = "alert.mp3"
SEEN_FILE = "seen_alerts.json"
DEFAULT_ZONE = "TNC065"  # Your NWS alert zone
DEFAULT_USER_AGENT = "you@youremail.com"
AUDIO_PORT = 8000
CHECK_INTERVAL = 300  # Poll every 5 minutes
WEATHER_STATION_ID = "KCHA"
# ==========================

app = Flask(__name__)
alerts_cache = []
zone_id = DEFAULT_ZONE
user_agent = DEFAULT_USER_AGENT
selected_speaker_name = None
selected_device_type = "sonos"
temperature_unit = "F"

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

def fetch_alerts(zone_id, user_agent):
    url = f"https://api.weather.gov/alerts/active?zone={zone_id}"
    headers = {"User-Agent": user_agent}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("features", [])

def fetch_current_weather(station_id=WEATHER_STATION_ID):
    url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
    headers = {"User-Agent": user_agent}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json().get("properties", {})
        return {
            "temperature": data.get("temperature", {}).get("value"),
            "humidity": data.get("relativeHumidity", {}).get("value"),
            "windSpeed": data.get("windSpeed", {}).get("value"),
            "windDirection": data.get("windDirection", {}).get("value"),
            "text": data.get("textDescription", "N/A"),
            "timestamp": data.get("timestamp", "")
        }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

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

def get_all_audio_devices():
    devices = []
    try:
        sonos_speakers = soco.discover()
        for s in sonos_speakers or []:
            devices.append({"name": s.player_name, "ip": s.ip_address, "type": "sonos"})
    except Exception as e:
        print(f"Sonos discovery failed: {e}")

    try:
        chromecasts, _ = pychromecast.get_chromecasts()
        for c in chromecasts:
            devices.append({
                "name": c.name,
                "ip": getattr(c.socket_client, "host", "unknown"),
                "type": "cast"
            })
    except Exception as e:
        print(f"Chromecast discovery failed: {e}")

    return sorted(devices, key=lambda d: d["name"])

def play_alert_on_device(text, name, device_type):
    if not name or not device_type:
        print("No speaker selected.")
        return False

    text_to_speech(text)
    url = f"http://{get_local_ip()}:{AUDIO_PORT}/alert.mp3"

    if device_type == "sonos":
        speakers = soco.discover()
        for s in speakers or []:
            if s.player_name and s.player_name.lower() == name.lower():
                try:
                    original_volume = s.volume
                    s.volume = 75
                    s.play_uri(url)
                    time.sleep(8)
                    s.volume = original_volume
                    return True
                except Exception as e:
                    print(f"Sonos error: {e}")
        return False

    elif device_type == "cast":
        chromecasts, _ = pychromecast.get_chromecasts()
        cast = next((c for c in chromecasts if c.name == name), None)
        if cast:
            cast.wait()
            original_volume = cast.status.volume_level
            cast.set_volume(0.75)
            cast.media_controller.play_media(url, "audio/mp3")
            cast.media_controller.block_until_active()
            time.sleep(8)
            cast.set_volume(original_volume)
            return True

    print(f"Device not found or unsupported: {name} ({device_type})")
    return False

@app.route("/")
def index():
    weather = fetch_current_weather()
    device_list = get_all_audio_devices()
    return render_template("index.html",
                           alerts=alerts_cache,
                           device_list=device_list,
                           selected_speaker=selected_speaker_name,
                           selected_device_type=selected_device_type,
                           zone=zone_id,
                           unit=temperature_unit,
                           weather=weather)

@app.route("/update", methods=["POST"])
def update_settings():
    global zone_id, selected_speaker_name, selected_device_type, temperature_unit
    zone_id = request.form["zone"]
    selected_speaker_name = request.form["speaker"]
    selected_device_type = request.form["device_type"]
    temperature_unit = request.form["unit"]
    return redirect(url_for("index"))

@app.route("/test")
def test_alert():
    if alerts_cache:
        headline = alerts_cache[0]["properties"]["headline"]
        message = f"This is a test. The current weather alert is: {headline}."
    else:
        weather = fetch_current_weather()
        if weather:
            temp_c = weather["temperature"]
            temp = round(temp_c * 9 / 5 + 32) if temperature_unit == "F" else round(temp_c)
            unit_label = "Fahrenheit" if temperature_unit == "F" else "Celsius"
            humidity = round(weather["humidity"]) if weather["humidity"] is not None else "unknown"
            wind_raw = weather["windSpeed"]
            wind_speed = round(wind_raw * 0.621371) if temperature_unit == "F" and wind_raw else round(wind_raw) if wind_raw else "unknown"
            wind_unit = "miles per hour" if temperature_unit == "F" else "kilometers per hour"

            message = (
                f"This is a test. The current weather is {weather['text']} "
                f"with a temperature of {temp} degrees {unit_label}, "
                f"humidity at {humidity} percent, "
                f"and wind speed of {wind_speed} {wind_unit}."
            )
        else:
            message = "This is a test. Weather data is not currently available."

    play_alert_on_device(message, selected_speaker_name, selected_device_type)
    return redirect(url_for("index"))

@app.route("/alert.mp3")
def serve_audio():
    return send_from_directory('.', AUDIO_FILE)

def background_poll():
    global alerts_cache
    seen = load_seen_ids()
    while True:
        try:
            alerts = fetch_alerts(zone_id, user_agent)
            new_alerts = get_new_alerts(alerts, seen)
            if new_alerts:
                for alert in new_alerts:
                    props = alert["properties"]
                    headline = props.get("headline", "Weather Alert")
                    description = props.get("description", "")
                    print(f"New alert: {headline}")
                    play_alert_on_device(description, selected_speaker_name, selected_device_type)
                    seen.add(alert["id"])
                    save_seen_ids(seen)
            alerts_cache[:] = alerts
        except Exception as e:
            print(f"Error polling alerts: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    threading.Thread(target=background_poll, daemon=True).start()
    app.run(host="0.0.0.0", port=AUDIO_PORT)
