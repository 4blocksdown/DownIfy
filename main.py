import os
import re
import sys
import requests
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import APIC

# ====== 🎵 ASCII Banner ======
print(r"""
________                      .___  _____       
\______ \   ______  _  ______ |   |/ ____\__.__.
 |    |  \ /  _ \ \/ \/ /    \|   \   __<   |  |
 |    `   (  <_> )     /   |  \   ||  |  \___  |
/_______  /\____/ \/\_/|___|  /___||__|  / ____|
        \/                  \/           \/      
               🎶 Spotify ➜ MP3 Downloader
                     by DownIfy
""")
# ==============================

# ====== 🔧 CONFIG ======
SPOTIFY_CLIENT_ID = 'd12a4642612b4d26b4ba4625fb6cbf5f'
SPOTIFY_CLIENT_SECRET = 'ab62a4e4f88d492e9298dd85ae5d567b'
FFMPEG_PATH = r'C:\ffmpeg\bin'  # Change this if ffmpeg is installed elsewhere
# ========================

# Setup Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

# Ask for output directory
output_dir = input("💾 Enter output folder (leave blank for current directory): ").strip()
if not output_dir:
    output_dir = os.getcwd()
else:
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

# Progress hook for yt-dlp
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '').strip()
        speed = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        sys.stdout.write(f"\r📥 Downloading: {percent} at {speed} (ETA: {eta})")
        sys.stdout.flush()
    elif d['status'] == 'finished':
        print("\n✅ Download complete, processing audio...\n")

def download_audio(query, filepath_no_ext):
    options = {
        'format': 'bestaudio/best',
        'outtmpl': filepath_no_ext + '.%(ext)s',
        'ffmpeg_location': FFMPEG_PATH,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'progress_hooks': [progress_hook],
    }

    with YoutubeDL(options) as ydl:
        try:
            ydl.download([f"ytsearch1:{query}"])
        except DownloadError as e:
            print(f"\n❌ Download failed: {e}")
            return False
    return True

def embed_metadata(mp3_path, metadata):
    audio = MP3(mp3_path, ID3=EasyID3)
    audio['title'] = metadata['title']
    audio['artist'] = metadata['artist']
    audio['album'] = metadata['album']
    audio.save()

    # Add cover image
    cover_data = requests.get(metadata['cover_url']).content
    audio = MP3(mp3_path)
    audio.tags.add(
        APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=cover_data
        )
    )
    audio.save()

def process_track(track):
    title = track['name']
    artist = track['artists'][0]['name']
    album = track['album']['name']
    cover_url = track['album']['images'][0]['url']

    filename = sanitize_filename(title)
    full_path_no_ext = os.path.join(output_dir, filename)
    
    # Use improved search query to get official versions
    search_query = f"{artist} - {title} official audio"

    print(f"\n🎵 Downloading: {title} by {artist}")
    success = download_audio(search_query, full_path_no_ext)
    if not success:
        print(f"❌ Skipped: {title}")
        return

    mp3_path = full_path_no_ext + '.mp3'
    metadata = {'title': title, 'artist': artist, 'album': album, 'cover_url': cover_url}
    embed_metadata(mp3_path, metadata)
    print(f"✅ Saved: {mp3_path}")

def process_spotify_url(url):
    if 'track' in url:
        track = sp.track(url)
        process_track(track)
    elif 'playlist' in url:
        results = sp.playlist_tracks(url)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])

        print(f"\n📃 Total Tracks Found: {len(tracks)}\n")
        for item in tracks:
            track = item['track']
            process_track(track)
    else:
        print("❌ Unsupported Spotify URL. Please use a track or playlist link.")

if __name__ == "__main__":
    spotify_url = input("🎧 Enter Spotify track or playlist URL: ").strip()
    process_spotify_url(spotify_url)
