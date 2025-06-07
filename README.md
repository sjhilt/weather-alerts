# Weather Alert Dashboard

This project monitors real-time weather alerts from [weather.gov](https://www.weather.gov) and announces them using Sonos or Google Cast (Chromecast) speakers. It includes a Flask-based web dashboard for managing settings and viewing current conditions.

---

## Features

- Weather alerts from weather.gov (NWS)
- Full alert description read aloud via text-to-speech (gTTS)
- Sonos and Chromecast speaker support
- Automatic volume adjustment (set to 75%, restore after alert)
- Temperature unit toggle (Fahrenheit / Celsius)
- Web dashboard for device selection, zone settings, and testing
- Test mode announces current weather if no alerts are active

---

## Requirements

Install Python dependencies:

```bash
pip3 install -r requirements.txt
```

Contents of requirements.txt:
```
flask
gtts
soco
pychromecast
requests
```


### Setup
1.	Clone or download the project files
2.	Install dependencies:
```
pip3 install -r requirements.txt
```

3.	Run the Flask app:
```
python3 -m app
```

4.	Open the dashboard in your browser:
```
http://localhost:8000
```

Or use your device’s IP address if running remotely.



## NWS Zone

You must enter your local NWS Zone ID in the dashboard. Example: TNCO65.

To find your zone ID, visit: [NWS](https://alerts.weather.gov/?reset=true) 


File Structure
```
.
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Web UI
├── alert.mp3           # Generated audio file
├── seen_alerts.json    # Tracks previously spoken alerts
├── requirements.txt    # Dependencies
```


Notes
- The application polls for new alerts every 5 minutes
- If no alerts are active, the “Test Alert” button will announce the current weather
- Alerts are only announced once and tracked using their ID
- Sonos and Chromecast devices are auto-discovered each time the page loads


