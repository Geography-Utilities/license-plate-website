import os
from collections import defaultdict
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
from config import get_config
from database import init_db
from forms import *
from models import User, Location, Plates, Submissions

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)


def _serial_sort_key(serial):
    try:
        return (1, int(serial))
    except (TypeError, ValueError):
        return (0, serial or "")


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

@app.route('/auth/login')
def login():
    session["next_url"] = request.args.get("next", "/")
    return render_template("login.html")


@app.route('/auth/login/discord')
def login_discord():
    redirect_uri = os.environ.get('DISCORD_REDIRECT_URI')
    session["next_url"] = request.args.get("next", session.get("next_url", "/"))
    return discord.authorize_redirect(redirect_uri)


@app.route('/auth/login/password', methods=['POST'])
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


@app.route('/auth/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('is_member', None)
    return redirect(url_for('index'))


@app.route('/auth/signup', methods=['GET', 'POST'])
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


@app.route('/todos')
@require_level(1)
def todo():
    if is_authenticated():
        with open('notes.md', 'r') as f:
            content = f.read()
        html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('markdown_page.html', content=html)
    else:
        return render_template('unauthorized.html')

@app.route('/admin/users')
@require_level(3)
def users():
    return render_template('admin_users.html', users=User.query.all())

@app.route('/admin/users/<int:id>/edit', methods=['GET', 'POST'])
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


@app.route('/locations')
def locations():
    user_perms = get_permission_level() or 0 # grab user permissions to determine whether to display "add location" button
    locations = Location.query.order_by(Location.name).filter_by(level=3).all()  # Only fetch level 3 locations (regions). this is temporary while US is the only supported country
    return render_template(
        'locations.html',
        locations=locations,
        location_hierarchy=None,
        user_permissions=user_perms
    )


## This is temporary just for testing
## It needs to be updated to use the proper location designations (likely LEVEL2_LOCATION) rather than just location since we'll have formatted hierarchical categories.
@app.route("/locations/<code>")
def location_page(code):
    location = Location.query.filter_by(code=code).first_or_404()
    plates_by_category = defaultdict(list)
    plates = Plates.query.filter_by(region=location.id).order_by(
        Plates.category,
        Plates.name,
    ).all()
    for plate in plates:
        plates_by_category[plate.category].append(plate)

    submissions = Submissions.query.filter(
        Submissions.plate_id.in_([plate.id for plate in plates])
    ).all()
    high_submissions = {}
    for submission in submissions:
        current_high = high_submissions.get(submission.plate_id)
        if current_high is None or _serial_sort_key(submission.serial) > _serial_sort_key(current_high.serial):
            high_submissions[submission.plate_id] = submission

    submitter_ids = {
        submission.submitter_id
        for submission in high_submissions.values()
    }
    submitter_names = {
        user.id: user.display_name
        for user in User.query.filter(User.id.in_(submitter_ids)).all()
    }

    return render_template(
        "location.html",
        location=location,
        plates_by_category=dict(plates_by_category),
        high_submissions=high_submissions,
        submitter_names=submitter_names,
    )




@app.route("/moderate")
@require_level(2) # allow moderator and admin access to moderation function pages
def moderator_dashboard():
    level = get_permission_level()  # grab user permissions for admin vs moderator
    return render_template("moderator.html", level=level)


@app.route("/moderator/locations/add", methods=["GET", "POST"])
@require_level(3) # admin level access temporarily while US is the only supported country.
def add_location():
    form = AddLocationForm()
    locations = Location.query.order_by(Location.name).all()
    
    form.parent_id.choices = [("", "No parent")] + [
        (str(location.id), location.name) for location in locations
    ]

    if form.validate_on_submit():
        new_location = Location(
            name=form.name.data,
            parent_id=form.parent_id.data,
            code=form.code.data or None,
            level=form.level.data
        )
        db.session.add(new_location)
        db.session.commit()
        flash(f"Location {form.name.data} added successfully.", "success")
        #return redirect(url_for("locations"))
    
    elif request.method == "POST":
        flash("Please correct the errors below.", "error")

    return render_template("add_location.html", form=form)


@app.route("/plate")
def plate_page():
    id = request.args.get("id")
    if id is None:
        abort(404)

    plate = db.get_or_404(Plates, id)
    submissions = Submissions.query.filter_by(plate_id=plate.id).order_by(Submissions.date_submitted.desc()).all()
    submitter_ids = {submission.submitter_id for submission in submissions}
    submitter_names = {
        user.id: user.display_name
        for user in User.query.filter(User.id.in_(submitter_ids)).all()
    }

    return render_template(
        "plate.html",
        plate=plate,
        submissions=submissions,
        submitter_names=submitter_names,
    )

@app.route("/plate/submit", methods=["GET", "POST"])
@require_level(1) # allow submitter, moderator, and admin access to submission function pages
def submit_plate():
    id = request.args.get("id")
    if id is None:
        abort(404)
    plate = db.get_or_404(Plates, id)

    if request.method == "POST":
        form = PlateSubmissionForm(request.form)
        if form.validate():
            submission = Submissions(
                serial=form.plate.data,
                plate_id=plate.id,
                date_submitted=date.today(),
                date_seen=form.date.data,
                type=form.type.data or None,
                location=form.location.data or None,
                expiration_date=form.expiration_date.data or None,
                notes=form.notes.data or None,
                submitter_id=session.get("user_id")
            )
            db.session.add(submission)
            db.session.commit()
            flash("Plate submission successful.", "success")
            return redirect(url_for("index"))
        else:
            flash("Please correct the errors below.", "error")
    else:
        form = PlateSubmissionForm()

    return render_template("submit_plate.html", plate=plate, form=form)


# legacy routes from previous paths. these will eventually be removed.
@app.route('/login')
def legacy_login():
    return redirect(url_for('login', **request.args), code=308)


@app.route('/login/discord')
def legacy_login_discord():
    return redirect(url_for('login_discord', **request.args), code=308)


@app.route('/login/password', methods=['POST'])
def legacy_login_password():
    return redirect(url_for('login_password'), code=308)


@app.route('/logout', methods=['POST'])
def legacy_logout():
    return redirect(url_for('logout'), code=308)


@app.route('/signup', methods=['GET', 'POST'])
def legacy_signup():
    return redirect(url_for('signup', **request.args), code=308)


@app.route('/todo')
def legacy_todo():
    return redirect(url_for('todo'), code=308)


@app.route('/a/users')
def legacy_users():
    return redirect(url_for('users'), code=308)


@app.route('/a/users/edit/<int:id>', methods=['GET', 'POST'])
def legacy_edit_user(id):
    return redirect(url_for('edit_user', id=id), code=308)


@app.route('/<location>')
def legacy_location(location):
    location = Location.query.filter(
        db.func.lower(Location.name) == location.replace("-", " ").casefold()
    ).first_or_404()
    return redirect(url_for('location_page', code=location.code), code=308)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404