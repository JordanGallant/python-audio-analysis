from fastapi import FastAPI
import httpx
import tempfile
import os
import essentia
import essentia.standard as es

app = FastAPI()

@app.get("/")
def read_root():
    return {"endpoints": ["/songs"]}

#endpoint to process songs
@app.get("/songs")
async def get_songs():
    print("Fetching song list from remote API...")
    url = "https://revival-records.vercel.app/api/songs"
    #fetch all songs from server component
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        songs_data = response.json()
    #limit 2 -> while testing
    first_two_songs = songs_data["songs"][:2]
    print(f"Fetched {len(first_two_songs)} songs. Starting analysis...\n")

    analysis_results = []
    #loops through songs to process audio
    for idx, song in enumerate(first_two_songs, start=1):
        print(f"[{idx}] Downloading: {song['title']}")

        mp3_url = song["url"]
        #donwloads acutal song
        async with httpx.AsyncClient() as client:
            mp3_response = await client.get(mp3_url)
            mp3_data = mp3_response.content
        print(f"[{idx}] Download complete. Size: {len(mp3_data)} bytes")
        #creates temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(mp3_data)
            tmp_path = tmp_file.name
        print(f"[{idx}] Temporary file saved at: {tmp_path}")

        try:
            #converts to mono
            loader = es.MonoLoader(filename=tmp_path)
            audio = loader() #actual audio
            print(f"[{idx}] Audio loaded. {len(audio)} samples")

            #processing will happen here
            rhythm_extractor = es.RhythmExtractor2013()
            rhythm_features = rhythm_extractor(audio)
            bpm = rhythm_features[0]   

            danceability_extractor = es.Danceability()
            all_danceability = danceability_extractor(audio) 
            danceability = all_danceability[0]

            print(f"Danceability: {danceability}")
            print(f"BPM: {bpm}")


            #create new object
            analysis_results.append({
                "count": idx,
                "title": song["title"],
                "url": song["url"],
                "duration_sec": round(duration, 2),
                "loudness_lufs": round(loudness, 2)
            })

        finally:#remove temp file
            os.remove(tmp_path)
            print(f"[{idx}] Temp file deleted.\n")

    print("All songs processed. Returning results.\n")
    return analysis_results
