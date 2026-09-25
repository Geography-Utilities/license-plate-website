# License Plate Tracker

## Development Setup
### Prerequisites
Install Python 3.11 or greater and Docker with Docker Compose.

### Create the virtual environment
```bash
python -m venv .venv
```

Activate it before running the remaining commands.

Linux:
```bash
source .venv/bin/activate
```

Windows:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Install dependencies
```bash
python -m pip install -r requirements.txt
```

### Configure the environment
Copy the example environment file:

Linux:
```bash
cp .env.example .env
```

Windows:
```powershell
Copy-Item .env.example .env
```

Set `FLASK_SECRET_KEY` in `.env`. Discord variables can remain empty unless you
want to test login.

### Start PostgreSQL
From the project root, run:

```bash
docker compose -f development/docker-compose.yml up -d
```

The development database is available at
`postgresql://plates_dev:devpassword@localhost:5432/plates_dev`.

### Apply database migrations
```bash
flask db upgrade
```

For future model changes, generate and apply a migration with:

```bash
flask db migrate -m "describe the change"
flask db upgrade
```

### Run the application
```bash
flask run
```

Open <http://127.0.0.1:5000> in a browser.

To stop PostgreSQL when finished:

```bash
docker compose -f development/docker-compose.yml down
```

The database data is kept in the `plates_dev_data` Docker volume.
