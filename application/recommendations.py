"""Recommendation Generator"""
import re
import os
import json
import requests

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from gensim.models.doc2vec import Doc2Vec
from nltk.tokenize import word_tokenize
from markupsafe import Markup

from flask import render_template, flash, redirect
from application import app
from application.forms import LoginForm

class Recommendation:
    """Recommendation object for input song"""
    # pylint: disable=too-many-instance-attributes
    # Eight is reasonable in this case.
    def __init__(self, artist, title):
        self.artist = artist
        self.title = title
        self.track_id = None
        self.lyrics = None
        self.album_image_url = None
        self.preview_url = None
        self.recommendations = None
        self.spotify_url = None

    def get_musixmatch_api_url(self, url):
        """Retrieve URL for song on Musixmatch"""
        return 'http://api.musixmatch.com/ws/1.1/{}&format=json&apikey={}'.format(
            url, os.getenv("MUSIX_API_KEY"))


    def find_track_info(self):
        """Retrieve song info from Musixmatch and Spotify"""
        url = 'matcher.track.get?q_track={}&q_artist={}'.format(
            self.get_song_title(), self.get_artist())
        matched_res = requests.get(self.get_musixmatch_api_url(url))
        matched_data = json.loads(matched_res.text)

        if matched_data["message"]["header"]["status_code"] == 200:
            #Get initial Musixmatch information
            self.artist = matched_data["message"]["body"]["track"]["artist_name"]
            self.title = matched_data["message"]["body"]["track"]["track_name"]
            self.track_id = matched_data["message"]["body"]["track"]["track_id"]

            #Make another API call for the lyrics
            url = 'track.lyrics.get?track_id={}'.format(self.get_track_id())
            lyrical_res = requests.get(self.get_musixmatch_api_url(url))
            lyrical_data = json.loads(lyrical_res.text)
            self.lyrics = lyrical_data["message"]["body"]["lyrics"]["lyrics_body"].split("...")[0]

            #Access Spotify API
            client_credentials_manager = SpotifyClientCredentials(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"), client_secret=os.getenv(
                    "SPOTIFY_CLIENT_SECRET"))
            spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

            #Get album art and a preview url from Spotify
            results = spotify.search(
                q='track:' + self.get_song_title() + ' artist:' + self.get_artist(), type='track')
            track = results['tracks']['items'][0]
            self.album_image_url = track["album"]["images"][1]["url"]
            self.preview_url = track["preview_url"]
            self.spotify_url = track['external_urls']['spotify']

            return True

        else:
            print('Track not found.')
            return False


    def load_recommendations(self):
        """Determine song recommendations using model"""
        #Clean lyrics for analysis
        lyrics = self.get_lyrics().strip().replace('\n', ' ').lower()
        lyrics = re.sub("[\(\[].*?[\)\]]", "", lyrics)

        #Get most similar lysics
        model = Doc2Vec.load("data/d2v.model") #load model
        test_data = word_tokenize(lyrics)
        v_1 = model.infer_vector(doc_words=test_data, alpha=0.025, min_alpha=0.001, steps=55)

        #First element of the tuple its index in the song_data list
        list_of_tuples = model.docvecs.most_similar(positive=[v_1], topn=20)
        recommendations = []

        #Store generated song recommendations from model
        with open('data/song_data.json') as json_file:
            song_data = json.load(json_file)
            for ranking_tuple in list_of_tuples:
                song = song_data[int(ranking_tuple[0])]
                song['genres'] = [g.title() for g in song['genres']]
                if song['name'] != self.get_song_title():
                    recommendations.append(song)

        self.recommendations = recommendations
        return True


    def get_artist(self):
        """Return artist"""
        return self.artist

    def get_song_title(self):
        """Return song title"""
        return self.title

    def get_track_id(self):
        """Return track ID"""
        return self.track_id

    def get_lyrics(self):
        """Return song lyrics"""
        return self.lyrics

    def get_album_image_url(self):
        """Return song album art URL"""
        return self.album_image_url

    def get_preview_url(self):
        """Return song preview URL"""
        return self.preview_url

    def get_spotify_url(self):
        """Return Spotify song url"""
        return self.spotify_url

    def get_recommendations(self):
        """Return song recommendations"""
        return self.recommendations
