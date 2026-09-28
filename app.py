import os
from authlib.integrations.flask_client import OAuth
from flask import Flask, session, redirect, url_for, render_template, request, flash, abort
import requests
import markdown
from urllib.parse import urlparse, urljoin
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
load_dotenv()
from auth import *
from config import get_config, load_dev_auth_level
from database import db, init_db
from forms import *
from models import Continent, Country, Plates, Region, SubRegion

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
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

@app.route('/login')
def login():
    redirect_uri = os.environ["DISCORD_REDIRECT_URI"]
    session["next_url"] = request.args.get("next", "/")
    return discord.authorize_redirect(redirect_uri, prompt='consent')

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
    display_name = user_info['username']

    user = discord_user_login(discord_id, display_name)
    session["user_id"] = user.id
    session["is_member"] = is_member
    next_url = session.pop("next_url", None)

    if not is_safe_url(next_url):
        next_url = url_for("index")
    return redirect(next_url)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('is_member', None)
    return redirect('/')

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


@app.route("/locations")
def locations():
    continents = Continent.query.order_by(Continent.name).all()
    location_groups = []
    for continent in continents:
        continent.countries.sort(key=lambda country: country.name.lower())
        countries = []
        for country in continent.countries:
            country.regions.sort(key=lambda region: region.name.lower())
            countries.append({
                "name": country.name,
                "regions": [
                    {
                        "name": region.name,
                        "url": url_for(
                            "location_page",
                            country=country.name,
                            region=region.name,
                        ),
                    }
                    for region in country.regions
                ],
            })
        location_groups.append({"name": continent.name, "countries": countries})
    return render_template("list_locations.html", continents=location_groups)


@app.route("/locations/<country>/<region>")
def location_page(country, region):
    country_name = country.replace("-", " ")
    region_name = region.replace("-", " ")
    location = (Region.query.join(Country)
        .filter(
            func.lower(Country.name) == country_name.lower(),
            func.lower(Region.name) == region_name.lower(),
        )
        .first_or_404()
    )
    plates_by_category = {}
    plates = (Plates.query.filter_by(region=location.id)
        .order_by(Plates.category, Plates.name)
        .all()
    )
    for plate in plates:
        plates_by_category.setdefault(plate.category, []).append(plate)

    return render_template("location.html", location=location.name, country=location.country.name, plates_by_category=plates_by_category)


@app.route("/plates/<id>/submit", methods=['GET', 'POST'])
@require_level(1)
def submit_to_location(id):
    if request.method == 'POST':
        # Handle the form submission
        pass

    # temporarily only use standard permanent form
    form = SubmitPermanent()
    
    return render_template("submit_to_location.html", id=id, form=form)


@app.route("/plates/type/add", methods=['GET', 'POST'])
@require_level(2)
def add_plate():
    form = PlateForm()

    # Choices are loaded per request, so every node sees the current DB state
    form.region.choices = [
        (r.id, f"{r.country.name} - {r.name}")
        for r in Region.query.join(Country).order_by(Country.name, Region.name)
    ]

    if form.validate_on_submit():
        plate = Plates(
            name=form.name.data.strip(),
            region=form.region.data,
            category=form.category.data.strip(),
            notes=(form.notes.data or "").strip() or None,
        )
        db.session.add(plate)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("This plate already exists for that region and category.")
        else:
            flash(f"Added plate “{plate.name}”.", "success")
            return redirect(url_for("add_plate"))

    return render_template("add_plate.html", form=form)

@app.route("/locations/<location_type>/add", methods=['GET', 'POST'])
@require_level(2)
def add_location(location_type):
    form_classes = {
        "continent": (ContinentForm, Continent, None, "continent"),
        "country": (CountryForm, Country, "continent", "country"),
        "region": (RegionForm, Region, "country", "region"),
        "subregion": (SubRegionForm, SubRegion, "region", "subregion"),
    }

    if location_type not in form_classes:
        abort(404)

    form_class, model_class, parent_name, display_name = form_classes[location_type]
    form = form_class()
    parent_field = getattr(form, parent_name) if parent_name else None

    if location_type == "country":
        parent_field.choices = [
            (continent.id, continent.name)
            for continent in Continent.query.order_by(Continent.name)
        ]
    elif location_type == "region":
        parent_field.choices = [
            (country.id, country.name)
            for country in Country.query.order_by(Country.name)
        ]
    elif location_type == "subregion":
        parent_field.choices = [
            (region.id, f"{region.country.name} - {region.name}")
            for region in Region.query.join(Country).order_by(Country.name, Region.name)
        ]

    if form.validate_on_submit():
        values = {"name": form.name.data.strip()}
        if parent_name:
            values[f"{parent_name}_id"] = parent_field.data

        location = model_class(**values)
        db.session.add(location)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append(
                f"This {display_name} already exists for the selected parent."
                if parent_name
                else f"This {display_name} already exists."
            )
        else:
            flash(f"Added {display_name} “{location.name}”.", "success")
            return redirect(url_for("add_location", location_type=location_type))

    return render_template(
        "add_location.html",
        form=form,
        location_type=display_name,
        parent_field=parent_field,
    )