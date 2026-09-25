import os
from authlib.integrations.flask_client import OAuth
from flask import Flask, session, redirect, url_for, render_template, request, flash, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import requests
import markdown
from urllib.parse import urlparse, urljoin
from werkzeug.security import generate_password_hash, check_password_hash

from auth import *
from config import get_config, load_dev_auth_level
from database import init_db
from forms import *
from models import User

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


def auth_rate_limit_key():
    username = request.form.get("username", "").strip().casefold()
    return f"{get_remote_address()}:{username}"


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    if not app.config["DEBUG"] and not app.config.get("RATELIMIT_STORAGE_URI"):
        raise RuntimeError("RATELIMIT_STORAGE_URI is required in production")
    csrf.init_app(app)
    limiter.init_app(app)
    app.config["DEV_AUTH_LEVEL"] = load_dev_auth_level()
    if app.config["DEV_AUTH_LEVEL"] is not None:
        app.logger.warning("DEV AUTH OVERRIDE ACTIVE: all clients are level %s",
                           app.config["DEV_AUTH_LEVEL"])
    app.config["AUTH_OVERRIDE_ACTIVE"] = app.config["DEV_AUTH_LEVEL"] is not None
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

## this is a temporary testing variable. mid-level regions will be pulled from the database eventually, once it exists.
LOCATIONS=["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New-Hampshire", "New-Jersey", "New-Mexico", "New-York", "North-Carolina", "North-Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode-Island", "South-Carolina", "South-Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West-Virginia", "Wisconsin", "Wyoming"]


@app.context_processor
def inject_user():
    user = current_user()
    return {
        "logged_in": is_authenticated(),
        "display_name": user.display_name if user else None,
        "user": user,
        "site_name": "Site Name"
    }

@app.context_processor
def inject_dev_flag():
    return {"auth_override_active": app.config["AUTH_OVERRIDE_ACTIVE"]}


@app.route('/')
def index():
    user = current_user()
    display_name = user.display_name if user else 'Guest'
    logged_in = is_authenticated()
    permissions = user.permission_level if logged_in else 0
    return render_template(
        'index.html',
        user=user,
        display_name=display_name,
        is_member=session.get('is_member', False),
        logged_in=logged_in,
        user_permissions=permissions,
    )

@app.route('/login')
def login():
    session["next_url"] = request.args.get("next", "/")
    return render_template("login.html")


@app.route('/login/discord')
def login_discord():
    redirect_uri = os.environ.get('DISCORD_REDIRECT_URI')
    session["next_url"] = request.args.get("next", session.get("next_url", "/"))
    return discord.authorize_redirect(redirect_uri)


@app.route('/login/password', methods=['POST'])
@limiter.limit("60 per minute")
@limiter.limit("10 per minute", key_func=auth_rate_limit_key)
def login_password():
    username = request.form['username']
    password = request.form['password']

    user = get_user_by_displayname(username)

    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        flash('Invalid credentials')
        return redirect(url_for('login'))

    next_url = session.pop("next_url", None)
    establish_authenticated_session(user.id)
    if not is_safe_url(next_url):
        next_url = url_for("index")
    return redirect(next_url)


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

    discord_id = user_info['id']
    display_name = user_info['username']

    user = discord_user_login(discord_id, display_name)
    next_url = session.pop("next_url", None)
    establish_authenticated_session(user.id)

    if not is_safe_url(next_url):
        next_url = url_for("index")
    return redirect(next_url)


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('is_member', None)
    return redirect('/')


@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("3 per hour", methods=["POST"])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')

    if not username or not password:
        flash('Username and password are required.')
        return redirect(url_for('signup'))

    if password != confirm:
        flash('Passwords do not match.')
        return redirect(url_for('signup'))

    if len(password) < 8:
        flash('Password must be at least 8 characters.')
        return redirect(url_for('signup'))

    existing = get_user_by_displayname(username)
    if existing is not None:
        flash('That username is already taken.')
        return redirect(url_for('signup'))

    user = User(
        display_name=username,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    establish_authenticated_session(user.id, is_member=False)

    return redirect(url_for('index'))


@app.route('/todo')
@require_level(1)
def todo():
    if is_authenticated():
        with open('notes.md', 'r') as f:
            content = f.read()
        html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('markdown_page.html', content=html)
    else:
        return render_template('unauthorized.html')

@app.route('/a/users')
@require_level(3)
def users():
    return render_template('admin_users.html', users=User.query.all())

@app.route('/a/users/edit/<int:id>', methods=['GET', 'POST'])
@require_level(3)
def edit_user(id):
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        form = AdminEditUser(request.form)
        if form.validate():
            user.display_name = form.display_name.data
            user.email = form.email.data or None
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


## This is temporary just for testing
## It needs to be updated to use the proper location designations (likely LEVEL2_LOCATION) rather than just location since we'll have formatted hierarchical categories.
@app.route("/<location>")
def location_page(location):
    logged_in = is_authenticated()
    location=location.title()
    if location not in LOCATIONS:
        abort(404)
    location = location.replace("-", " ")
    return render_template("location.html", location=location)
