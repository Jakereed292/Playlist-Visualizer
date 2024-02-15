import requests
import urllib.parse

from datetime import datetime
from flask import Flask, jsonify, redirect, render_template, request, session

app = Flask(__name__)
app.secret_key = "12135744328"

CLIENT_ID = '161d6adcd8e14ce3947052003dee3d34'
CLIENT_SECRET = '2195bc23706244d58adfe05fc7f8e98b'
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

@app.route('/')
def index():
    return "Welcome to my spotify app! <a href='/login'>Click here</a>"

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
        
        return redirect('/playlists')

def get_playlist_tracks(playlist_in):
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    response = requests.get(playlist_in, headers=headers)
    data = response.json()
    
    track_name = ''
    artist_name = ''
    track_id = ''
    
    playlist_tracks = []
    
    for i in data['items']:
        for x in i['track']['album']['artists']:
            artist_name = x['name']
        track_name = i['track']['name']
        track_id = i['track']['id']
        
        playlist_tracks.append(track_name+', '+artist_name+': '+track_id) 
    
    return playlist_tracks

@app.route('/playlists')
def get_playlists():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']: 
        return redirect('/refresh-token')
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    response = requests.get(API_BASE_URL+"me/playlists", headers=headers)
    data = response.json()
    
    playlist_tracks = []
    
    name_response = requests.get(API_BASE_URL+"me", headers=headers)
    name_data = name_response.json()
    user_name = name_data["display_name"]
    
    for i in data['items']:
        if (i["owner"]["display_name"] == user_name):
            playlist_tracks.append(i["name"])
            playlist_tracks.append(i["tracks"])
    
    return get_playlist_tracks(playlist_tracks[1]["href"])

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
        
        return redirect('/playlists')
    
if __name__== '__main__':
    app.run(host = '0.0.0.0', debug=True)