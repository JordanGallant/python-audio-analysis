from fastapi import FastAPI
import httpx
import tempfile
import os
import essentia
import essentia.standard as es
import numpy as np
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
import redis
import json
from dotenv import load_dotenv


load_dotenv()


redis_uri = os.environ.get('REDIS_URI')
redis_password = os.environ.get('REDIS_PASSWORD') 

r = redis.Redis(
    host=redis_uri,
    port=16786,
    decode_responses=True,
    username="default",
    password=redis_password,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Allow requests from any origin (you can restrict this to specific domains)
    allow_origins=["*"],
    # Allow all common HTTP methods
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # Allow standard headers
    allow_headers=["*"],
    # Allow credentials such as cookies
    allow_credentials=True,
)


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
    all_songs = songs_data["songs"]
    print(f"Fetched {len(all_songs)} songs. Starting analysis...\n")

    analysis_results = []
    #loops through songs to process audio
    for idx, song in enumerate(all_songs, start=1):
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
            tmp_file.flush()
            os.fsync(tmp_file.fileno())  # Ensures data is written to disk
            tmp_path = tmp_file.name
        print(f"[{idx}] Temporary file saved at: {tmp_path}")

        try:
            #converts to mono
            loader = es.MonoLoader(filename=tmp_path)
            audio = loader() #actual audio
            print(f"[{idx}] Audio loaded. {len(audio)} samples")

            #frame generator
            frame_generator = es.FrameGenerator(audio, frameSize=2048, hopSize=1024, startFromZero=True)
            windowing = es.Windowing(type='hann')
            spectrum = es.Spectrum(size=2048) #create spectrum to be analyzed
            centroid = es.Centroid() #create centroid

            #MFCC
            mfcc = es.MFCC(highFrequencyBound=18000, inputSize=1025)
            melbands = es.MelBands(numberBands=40)

            #Flux
            flux = es.Flux()
            prev_spectrum = None


            flux_values = []
            centroids = []
            mfccs = []



            for frame in frame_generator:
                win = windowing(frame)
                spec = spectrum(win)
                #append centroids
                c = centroid(spec)
                centroids.append(c)
                #append mfccs
                mfcc_bands, mfcc_coeffs = mfcc(spec)
                mfccs.append(mfcc_coeffs)

                #flux
                if prev_spectrum is not None:
                    flux_val = flux(spec - prev_spectrum)
                    flux_values.append(flux_val)
                prev_spectrum = spec

            #BPM
            rhythm_extractor = es.RhythmExtractor2013()
            rhythm_features = rhythm_extractor(audio)
            bpm = rhythm_features[0]   #gets average over whole track

            #Danceability
            danceability_extractor = es.Danceability()
            all_danceability = danceability_extractor(audio) 
            danceability = all_danceability[0] #gets average over whole track

            #Energy
            energy_extractor = es.Energy()
            energy = energy_extractor(audio)

            #Key
            key_extractor = es.KeyExtractor(profileType="edma") #uses profile adapted to Electronic dance music
            key, scale, strength = key_extractor(audio)

            #Loudness
            loudness = es.Loudness()(audio)

            #spectral centroid
            spectral_centroid = np.mean(centroids) # value 0-1 -> lower number = lower frequnecies

            #mfccs
            mfccs_np = np.array(mfccs)
            mean_mfcc = np.mean(mfccs_np, axis=0).tolist() #coefinents to represent tonal frequencies- tone/timbre

            #flux
            avg_flux = np.mean(flux_values) if flux_values else 0.0


            print(f"Flux: {avg_flux}")
            print(f"MFCC: {mean_mfcc}")
            print(f"Centroid: {spectral_centroid}")
            print(f"Loudness: {loudness}")
            print(f"Key: {key} {scale} (strength: {strength:.2f})")
            print(f"Energy: {energy}")
            print(f"Danceability: {danceability}")
            print(f"BPM: {bpm}")


            #create new object
            analysis_results.append({
                "Track": idx,
                "title": song["title"],
                "url": song["url"],
                "danceability": round(danceability, 2),
                "BPM": round(bpm, 2),
                "energy": round(energy, 2),
                "key": f"{key} {scale} {round(strength,2)}",
                "loudess": f"{round(loudness,2)}",
                "spectral-centroid": f"{round(spectral_centroid,2)}",
                "mfcc": [round(coeff, 3) for coeff in mean_mfcc],
                "flux": round(avg_flux, 4)
                
            })

        finally:#checks if file is already deleted -> handles error
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"[{idx}] Temp file deleted.\n")
            else:
                print(f"[{idx}] Temp file already deleted or not found.\n")

    results_key = "analysis_results"
    r.set(results_key, json.dumps(analysis_results))

    print("All songs processed. Returning results.\n")
    return analysis_results
