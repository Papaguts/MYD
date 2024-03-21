import tkinter as tk
import os
from tkinter import messagebox
from tkinter import ttk
import musicbrainzngs
from pytube import YouTube
from youtubesearchpython import VideosSearch
import math
from pydub import AudioSegment
import threading  # Für den Thread

# Setzen Sie den relativen Pfad zum VLC-Installationsverzeichnis (zum Beispiel im Projektordner)
dirname = os.path.dirname(__file__)
#with that I made the relative path into an absolute path
vlc_path = os.path.join(dirname,'vlc')

# Setzen Sie die Umgebungsvariable VLC_PLUGIN_PATH
os.environ['PATH'] += ';' + vlc_path
import vlc

# Setze den Server auf die Testumgebung, um die Anfragen zu minimieren
musicbrainzngs.set_useragent("MichasYoutubeDownloader", "0.1", "http://example.com")
musicbrainzngs.set_hostname("test.musicbrainz.org")

# VLC Player initialisieren
instance = vlc.Instance()
player = instance.media_player_new()

# Globale Variable für den Timer
search_timer = None

# Globale Variable für den Thread
search_thread = None

# Globale Variable für die Ergebnisse der Suche
result = None
current_stream = None

def convert_to_mp3(input_file, output_file):
    # AudioSegment-Objekt erstellen
    audio = AudioSegment.from_file(input_file)

    # In MP3 umwandeln
    audio.export(output_file, format="mp3")


def search_songs_in_thread_delayed():
    # Überprüfen, ob bereits ein Thread läuft
    global search_thread
    if search_thread and search_thread.is_alive():
        messagebox.showwarning("Warning", "A search is already in progress.")
    else:
        # Suche in einem separaten Thread ausführen
        search_thread = threading.Thread(target=search_songs)
        search_thread.start()

def search_songs_delayed(event=None):
    # Wenn bereits ein Timer läuft, stoppen Sie ihn
    global search_timer
    if search_timer and search_timer.is_alive():
        search_timer.cancel()
    # Starten Sie einen neuen Timer mit einer Verzögerung von 0.5 Sekunden
    search_timer = threading.Timer(1.5, search_songs_in_thread_delayed)
    search_timer.start()

def search_songs():
    global result
    artist = artist_entry.get()
    song = song_entry.get()
    result = musicbrainzngs.search_recordings(artist=artist, recording=song)
    
    song_tree.delete(*song_tree.get_children())
    for recording in result['recording-list']:
        title = recording['title']
        artist = recording['artist-credit'][0]['artist']['name']
        album = recording['release-list'][0]['title'] if 'release-list' in recording and recording['release-list'] else 'N/A'
        duration_seconds = int(recording['length']) / 1000 if 'length' in recording else 0
        minutes = math.floor(duration_seconds / 60)
        seconds = math.floor(duration_seconds % 60)
        song_tree.insert("", tk.END, values=(artist, title, album, f"{minutes}:{seconds:02}", duration_seconds))
    global search_thread
    search_thread = None

def show_song_info(event):
    global current_stream
    selection = song_tree.selection()
    if selection:
        index = selection[0]
        item = song_tree.item(index)
        artist = item['values'][0]
        title = item['values'][1]
        album = item['values'][2]
        duration = item['values'][3]
        duration_seconds = float(item['values'][4])  # Hier hinzugefügt
        print(duration_seconds)
        song_info_text.config(state=tk.NORMAL)
        song_info_text.delete(1.0, tk.END)
        song_info_text.insert(tk.END, f"Artist: {artist}\nTitle: {title}\nAlbum: {album}\nDuration: {duration}")
        song_info_text.config(state=tk.DISABLED)
        
        # Suche nach dem ausgewählten Song bei YouTube
        query = f'"{artist}" "{title}"'
        print("Ich suche nach : ", query)
        try:
            search_results = VideosSearch(query, limit=10).result()
            if search_results["result"]:
                best_match = []
                for video in search_results["result"]:
                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                    video_duration = video['duration'].split(":")
                    video_views = video['viewCount']['text']
                    views_count_str = video_views.split()[0]  # Teile die Zeichenfolge am Leerzeichen und nimm den ersten Teil
                    views_count_int = int(views_count_str.replace(",", ""))
                    video_duration_in_seconds=(int(video_duration[0])*60)+int(video_duration[1])
                    duration_difference = abs(video_duration_in_seconds - duration_seconds)
                    print(video_url, video_duration_in_seconds, views_count_int)
                    if duration_difference <= 5:
                        best_match.append([video_url,views_count_int])
                if (best_match):
                    sorted_data = sorted(best_match, key=lambda x: x[1], reverse=True)
                    best_match = sorted_data[:5]
                else:
                    messagebox.showerror("Error", "Sorry nix gefunden als Tipp suche mal nach den konkreten Song vielleicht ist eine andere version verfügbar")
                streamlist=[]
                for stream in best_match:
                    yt_video = YouTube(stream[0])
                    m4a_streams = yt_video.streams.filter(only_audio=True, file_extension="mp4")
                    best_stream = None
                    best_abr = 0

                    for stream in m4a_streams:
                        bitrate_str = stream.abr[:-4]  # Entfernt "kbps" von der Bitrate-Zeichenfolge
                        bitrate_int = int(bitrate_str)
                        if bitrate_int  > best_abr:
                            best_stream = stream
                            best_abr = bitrate_int 
                
                    streamlist.append([best_stream, best_abr])
                streamlist = sorted(streamlist, key=lambda x: x[1], reverse=True)
                print(streamlist)
                audio_stream=streamlist[0][0]
                
                if audio_stream:
                    player.audio_set_volume(100)
                    player.set_mrl(audio_stream.url)
                    current_stream= audio_stream
                else:
                    messagebox.showerror("Error", "Sorry nix gefunden als Tipp suche mal nach den konkreten Song vielleicht ist eine andere version verfügbar")
            else:
                messagebox.showerror("Error", "No YouTube search results found.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

def play_song():
    player.play()
def stop_song():
    player.stop()
def download_song():
    global current_stream
    if (current_stream):
        current_stream.download(filename="temp.mp4")
        convert_to_mp3("temp.mp4",current_stream.title+".mp3")
        messagebox.showinfo("Download", "Alles geklappt")
    else:
        messagebox.showerror("Error", "Upsi download nicht geklappt")

# GUI erstellen
root = tk.Tk()
root.title("MusicBrainz Song Search")

artist_label = tk.Label(root, text="Artist:",width=3)
artist_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
artist_entry = tk.Entry(root)
artist_entry.grid(row=0, column=1, padx=10, pady=5,sticky="w")
artist_entry.bind("<KeyRelease>", search_songs_delayed)  # Binden Sie das KeyRelease-Ereignis an die search_songs-Funktion

song_label = tk.Label(root, text="Song:",width=3)
song_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
song_entry = tk.Entry(root)
song_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
song_entry.bind("<KeyRelease>", search_songs_delayed)  # Binden Sie das KeyRelease-Ereignis an die search_songs-Funktion
columns = ("Artist", "Title", "Album", "Duration")
song_tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    song_tree.heading(col, text=col)
song_tree.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

song_scrollbar = ttk.Scrollbar(root, orient="horizontal", command=song_tree.xview)
song_scrollbar.grid(row=4, column=0, columnspan=3, sticky="ew")
# Treeview für die Anzeige der Suchergebnisse


# Bildlaufleiste für die Treeview
song_tree.configure(xscrollcommand=song_scrollbar.set)

# Doppelklick auf einen Eintrag, um Song-Informationen anzuzeigen
song_tree.bind("<Double-1>", show_song_info)

# Textfeld für die Anzeige der Song-Informationen
song_info_text = tk.Text(root, width=40, height=10, state=tk.DISABLED)
song_info_text.grid(row=5, column=0, columnspan=2, padx=10, pady=5)

# Play und Download Buttons
play_button = tk.Button(root, text="Play", command=play_song)
play_button.grid(row=6, column=0, padx=10, pady=5)

stop_button = tk.Button(root, text="Stop", command=stop_song)
stop_button.grid(row=6, column=1, padx=10, pady=5)

download_button = tk.Button(root, text="Download", command=download_song)
download_button.grid(row=6, column=2, padx=10, pady=5)

# Starten der Hauptereignisschleife
root.mainloop()