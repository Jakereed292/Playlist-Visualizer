import requests
import urllib.parse

from datetime import datetime
from flask import Flask, jsonify, redirect, render_template, request, session

app = Flask(__name__)
app.secret_key = "12135744328"

CLIENT_ID = 'fc787b4e7c4b4b159d5f2b68d962ea46'
CLIENT_SECRET = '0d1bc7338b82416b97837b7ca998ef0b'
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login')
def login():
    scope = 'playlist-read-private user-read-email user-read-private'
    
    params = {
        'client_id' : CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    return redirect(auth_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code' : request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        
        return redirect('/form')

@app.route('/form')
def form():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']: 
        return redirect('/refresh-token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL+"me/playlists?limit=50", headers=headers)
    data = response.json()
    
    user_playlists = []
    playlist_images = []
    
    name_response = requests.get(API_BASE_URL+"me", headers=headers)
    name_data = name_response.json()
    user_name = name_data["display_name"]
    playlist_name = ''
    
    for i in data['items']:
        if (i["owner"]["display_name"] == user_name):
            playlist_name = i['name']
            user_playlists.append(playlist_name)
            playlist_images.append([i['images'][0]['url']])
    
    return_playlist_images = []
    
    for x in range(len(playlist_images)):
        return_playlist_images.append((playlist_images[x][0]))
        
    playlist_len = len(return_playlist_images)
    
    return render_template("form.html", playlist_len=playlist_len, user_lists=user_playlists, playlist_images=return_playlist_images)

def get_tracks_info(ids_in):
    id_url = "audio-features?ids="
            
    for i in range(len(ids_in)):
        if(i == 0):
            id_url = id_url +  ids_in[i]
        else:
            id_url = id_url + "%2C" + ids_in[i]
            
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
        
    response = requests.get(API_BASE_URL + id_url, headers=headers)
    data = response.json()
    
    print(data)
    return data


def get_playlist_tracks(playlist_in):
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    response = requests.get(playlist_in, headers=headers)
    data = response.json()
    
    track_ids = []
    tracks_with_ids = {}
    
    acousticness = []
    danceability = []
    energy = []
    liveness = []
    speechiness = []
    valence = []
    
    for i in data['items']:
        for x in i['track']['album']['artists']:
            artist_name = x['name']
        track_name = i['track']['name']
        track = track_name+", "+artist_name
        tracks_with_ids[track] = i['track']['id']
        track_ids.append(i['track']['id'])
    
    audio_features = get_tracks_info(track_ids)

    try:
        for x in range(len(audio_features["audio_features"])):
            acousticness.append((audio_features["audio_features"][x]["acousticness"], list(tracks_with_ids.keys())[list(tracks_with_ids.values()).index(audio_features["audio_features"][x]["id"])]))
            danceability.append((audio_features["audio_features"][x]["danceability"], list(tracks_with_ids.keys())[list(tracks_with_ids.values()).index(audio_features["audio_features"][x]["id"])]))
            energy.append((audio_features["audio_features"][x]["energy"], list(tracks_with_ids.keys())[list(tracks_with_ids.values()).index(audio_features["audio_features"][x]["id"])]))
            liveness.append((audio_features["audio_features"][x]["liveness"], list(tracks_with_ids.keys())[list(tracks_with_ids.values()).index(audio_features["audio_features"][x]["id"])]))
            speechiness.append((audio_features["audio_features"][x]["speechiness"], list(tracks_with_ids.keys())[list(tracks_with_ids.values()).index(audio_features["audio_features"][x]["id"])]))
            valence.append((audio_features["audio_features"][x]["valence"], list(tracks_with_ids.keys())[list(tracks_with_ids.values()).index(audio_features["audio_features"][x]["id"])])) 
    except ValueError:
        return render_template("error.html")

    return render_template("data.html", acousticness=acousticness, danceability=danceability, energy=energy, liveness=liveness, speechiness=speechiness, valence=valence)
    
@app.route('/playlists', methods=['POST', 'GET'])
def get_playlists():
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    if request.method == "POST":
        form_data = request.form
        
    response = requests.get(API_BASE_URL+"me/playlists?limit=50", headers=headers)
    data = response.json()
    
    playlist_dict = {}
    
    name_response = requests.get(API_BASE_URL+"me", headers=headers)
    name_data = name_response.json()
    user_name = name_data["display_name"]
    
    for i in data['items']:
        if (i["owner"]["display_name"] == user_name):
            playlist_dict[i["name"]] = (i["tracks"])
    
    playlist_choice = list(form_data.values())[0]
    
    tracks = get_playlist_tracks(list(playlist_dict.values())[list(playlist_dict.keys()).index(playlist_choice)]["href"])
    
    return tracks

@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']: 
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }
        
        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()
        
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
        
        return redirect('/form')
    
if __name__== '__main__':
    app.run(host = '0.0.0.0', debug=True)