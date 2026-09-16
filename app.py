import os
from authlib.integrations.flask_client import OAuth
from flask import Flask, session, redirect, url_for, render_template
import requests
import markdown

from auth import *

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

oauth = OAuth(app)
discord = oauth.register(
    name='discord',
    client_id=os.environ["DISCORD_CLIENT_ID"],
    client_secret=os.environ["DISCORD_CLIENT_SECRET"],
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    api_base_url='https://discord.com/api/',
    client_kwargs={'scope': 'identify guilds'},
)

@app.route('/login')
def login():
    redirect_uri = os.environ["DISCORD_REDIRECT_URI"]
    return discord.authorize_redirect(redirect_uri, prompt='none')

@app.route('/auth/callback')
def auth_callback():
    token = discord.authorize_access_token()
    access_token = token['access_token']

    headers = {'Authorization': f'Bearer {access_token}'}

    user_resp = requests.get('https://discord.com/api/users/@me', headers=headers)
    user_info = user_resp.json()

    guilds_resp = requests.get('https://discord.com/api/users/@me/guilds', headers=headers)
    guilds = guilds_resp.json()

    if isinstance(guilds, dict):
        print("Discord guilds error:", guilds)
        is_member = False
    else:
        YOUR_SERVER_ID = os.environ["SERVER_ID"]
        is_member = any(g['id'] == YOUR_SERVER_ID for g in guilds)

    user_info['is_member'] = is_member
    session['user'] = user_info
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/')
def index():
    user = session.get('user')
    username = user['username'] if user else 'Guest'
    logged_in = is_authenticated()
    return render_template('index.html', user=user, username=username, logged_in=logged_in)

@app.route('/todo')
def todo():
    if is_authenticated():
        with open('notes.md', 'r') as f:
            content = f.read()
        html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('markdown_page.html', content=html)
    else:
        return render_template('unauthorized.html', logged_in=False)