# Revival Records Audio Features API

This Python-based API extracts audio features from tracks associated with Revival Records using the Spotify Web API. It uses self-authentication via the Client Credentials Flow.

## Features

- 🎧 Extracts detailed audio features (e.g., tempo, energy, danceability, etc.) - Essentia
- 🎧 Extracts genre and artist name from metadata
- ⚙️ Runs as a lightweight REST API
- 🐍 Built in Python with Fast API

## Requirements

- Python 3.7+
- A Spotify Developer account
- Spotify API credentials (Client ID and Client Secret)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/revival-audio-features-api.git
cd revival-audio-features-api
```
### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Run 
```bash
uvicorn --reload
```

