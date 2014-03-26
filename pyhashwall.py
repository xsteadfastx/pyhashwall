import os
import re
import tweepy
import time
import json
import threading
import requests
import sys
from io import open
from urlparse import urlsplit
from flask import Flask, render_template, session, request
from flask_bootstrap import Bootstrap
from flask.ext.socketio import SocketIO, emit


app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = os.urandom(24)
Bootstrap(app)
socketio = SocketIO(app)


def requests_image(file_url):
    try:
        file_url = re.sub(r'normal', 'bigger', file_url)
        file_name = urlsplit(file_url)[2].split('/')[-1]
        file_suffix = file_name.split('.')[1]
        r = requests.get(file_url)
        if r.status_code == requests.codes.ok:
            with open('static/images/' + file_name, 'wb') as f:
                f.write(r.content)
            return 'static/images/' + file_name
        else:
            return False
    except Exception:
        pass


def delete_images():
    for f in os.listdir('static/images/'):
        os.remove('static/images/' + f)
    threading.Timer(120, delete_images).start()


class StListener(tweepy.StreamListener):
    global waiting_line
    waiting_line = []

    def on_status(self, status):
        profile_image = requests_image(status.user.profile_image_url)
        background_image = requests_image(status.user.profile_background_image_url)
        output = json.dumps({'text': status.text,
                             'id': status.id_str,
                             'username': status.user.screen_name,
                             'profile_image': profile_image,
                             'background_color': status.user.profile_background_color,
                             'use_background_image': status.user.profile_use_background_image,
                             'background_image': background_image})
        if output not in waiting_line:
            waiting_line.append(output)

        return True

    def on_error(self, status_code):
        return True

    def on_timeout(self):
        return True


def listen():
    listener = StListener()
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET)

    stream = tweepy.Stream(auth, listener)
    stream.filter(track=HASHTAGS)


def spit_out():
    delete_images()
    while True:
        time.sleep(5)
        if len(waiting_line) == 0:
            pass
        else:
            print waiting_line[-1]
            socketio.emit('my response', waiting_line.pop(),
                          namespace='/hashwall')


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect', namespace='/hashwall')
def hashwall_connect():
    print 'Client connected'
    if len(waiting_line) == 0:
        pass
    else:
        emit('my response', namespace='/hashwall')


@socketio.on('disconnect', namespace='/hashwall')
def hashwall_disconnect():
    print 'Client disconnected'


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print 'USAGE: python pyhashwall.py #foo #bar #blubb'
        sys.exit()

    HASHTAGS = sys.argv[1:]

    config = {}
    execfile('pyhashwall.conf', config)
    CONSUMER_KEY = config['CONSUMER_KEY']
    CONSUMER_SECRET = config['CONSUMER_SECRET']
    ACCESS_TOKEN_KEY = config['ACCESS_TOKEN_KEY']
    ACCESS_TOKEN_SECRET = config['ACCESS_TOKEN_SECRET']

    threading.Thread(target=listen).start()
    threading.Thread(target=spit_out).start()
    socketio.run(app)
