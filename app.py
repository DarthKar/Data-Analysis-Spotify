from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json
import requests
import datetime
from flask import Flask, redirect, request, jsonify, session, render_template
import urllib


# Establecer variables de app flask
app = Flask(__name__)
app.secret_key = '9df31cad3eb2f66386575da6dd6641ae'

# Variables de entorno de la API
load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = 'http://localhost:5000/callback'
auth_url = 'https://accounts.spotify.com/authorize'
api_base_url = 'https://api.spotify.com/v1'
token_url = "https://accounts.spotify.com/api/token"


def get_token():
    cadena_auto = client_id + ":" + client_secret
    bytes_auto = cadena_auto.encode("utf-8")
    base64_auto = str(base64.b64encode(bytes_auto), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    encab = {
        "Authorization": "Basic " + base64_auto,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=encab, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token


# Token para consultas
token = get_token()


def see_top_songs_artist(token, artist):
    result = search_for_artist(token, artist)
    artist_id = result["id"]
    songs = search_top_songs(token, artist_id)
    print(f"Artista: {result['name']} \n Canciones Top")
    for idx, song in enumerate(songs):
        print(f"{idx + 1}: {song['name']}")


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={artist_name}&type=artist&limit=1"

    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]

    if len(json_result) == 0:
        print("No encontrado")
        return None
    return json_result[0]


def search_top_songs(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=CO"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    json_result = json.loads(result.content)["tracks"]
    return json_result


# Lógica para la página

@app.route('/')
def index():
    return "Pruebas <a href='/login'>Conectarse a Spotify</a>"


@app.route('/login')
def login():
    scope = 'user-read-private user-read-email playlist-read-private playlist-read-collaborative'
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': redirect_uri,
        'show_dialog': True
    }

    auth = f"{auth_url}?{urllib.parse.urlencode(params)}"

    return redirect(auth)


@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({'error': request.args['error']})

    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }
        response = requests.post(token_url, data=req_body)
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.datetime.now().timestamp() + token_info['expires_in']

        return redirect('/playlists')


@app.route('/playlists')
def get_playlist():
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(api_base_url + '/me/playlists?limit=20', headers=headers)
    playlists = response.json()

    # Imprimir la respuesta para depuración
    print(playlists)

    if 'error' in playlists:
        return jsonify({'error': playlists['error']['message']})

    # Accede a la propiedad 'items' y maneja el caso donde no hay playlists
    items = playlists.get('items', [])

    # Verifica si hay playlists y renderiza
    if not items:
        return render_template('playlists.html', playlists=[], message="No hay playlists disponibles.")
    
    return render_template('playlists.html', playlists=items)


@app.route('/refresh-token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': client_id,
            'client_secret': client_secret
        }

        response = requests.post(token_url, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/playlists')


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
