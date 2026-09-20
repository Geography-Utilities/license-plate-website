import os
from authlib.integrations.flask_client import OAuth
from flask import Flask, session, redirect, url_for, render_template, request, flash
import requests
import markdown
from urllib.parse import urlparse, urljoin

from auth import *
from config import get_config
from database import init_db
from forms import *

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    init_db(app)
    import models  # noqa: F401
    return app

app = create_app()

oauth = OAuth(app)
discord = oauth.register(
    name='discord',
    client_id=os.environ.get("DISCORD_CLIENT_ID"),
    client_secret=os.environ.get("DISCORD_CLIENT_SECRET"),
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    api_base_url='https://discord.com/api/',
    client_kwargs={'scope': 'identify guilds'},
)

def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

@app.route('/login')
def login():
    redirect_uri = os.environ["DISCORD_REDIRECT_URI"]
    session["next_url"] = request.args.get("next", "/")
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

    discord_id = user_info['id']
    discord_username = user_info['username']

    user = discord_user_login(discord_id, discord_username)

    user_info['is_member'] = is_member
    user_info['permission_level'] = user.permission_level
    session['user'] = user_info
    next_url = session.pop("next_url", None)

    if not is_safe_url(next_url):
        next_url = url_for("index")
    return redirect(next_url)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/')
def index():
    user = session.get('user')
    username = user['username'] if user else 'Guest'
    logged_in = is_authenticated()
    permissions = user['permission_level'] if logged_in else 0
    return render_template('index.html', user=user, username=username, logged_in=logged_in, user_permissions=permissions)

@app.route('/todo')
def todo():
    if is_authenticated():
        with open('notes.md', 'r') as f:
            content = f.read()
        html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('markdown_page.html', content=html)
    else:
        return render_template('unauthorized.html', logged_in=False)

@app.route('/a/users')
def users():
    user_list = User.query.all()
    if is_authenticated():
        return render_template('users.html', users=user_list)
    else:
        return render_template('unauthorized.html', logged_in=False)

@app.route('/a/users/edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if not is_authenticated():
        return render_template('unauthorized.html', logged_in=False)

    user = session.get('user')
    if user["permission_level"] < 3:
        return render_template('unauthorized.html', logged_in=False)

    user = User.query.get_or_404(id)

    if request.method == 'POST':
        form = AdminEditUser(request.form)
        if form.validate():
            user.display_name = form.display_name.data
            user.email = form.email.data
            user.alpca = form.alpca.data
            user.home_state = form.home_state.data
            user.home_country = form.home_country.data
            user.permission_level = form.permission_level.data
            db.session.commit()
            flash('User updated.', 'success')
        else:
            flash('Please correct the errors below.', 'error')
    else:
        form = AdminEditUser(obj=user)

    return render_template('admin_edit_user.html', user=user, form=form)