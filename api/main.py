from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

def get_database_url():
    user = os.environ.get("POSTGRES_USER", "user")
    db_name = os.environ.get("POSTGRES_DB", "tasks_db")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")

    password = None
    # Check for password file first (Docker Secrets)
    password_file_path = os.environ.get("POSTGRES_PASSWORD_FILE")
    if password_file_path and os.path.exists(password_file_path):
        with open(password_file_path, "r") as f:
            password = f.read().strip()
    else:
        # Fallback to environment variable (for local dev without secrets or if not using _FILE)
        password = os.environ.get("POSTGRES_PASSWORD", "password")

    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

@app.get("/")
async def read_root():
    db_url = get_database_url() # Example usage
    return HTMLResponse(f"<h1>Welcome to the API!</h1><p>DB URL (example, not used for connection yet): {db_url}</p>")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Placeholder for database interaction or other API logic
# When connecting to the DB, you would use get_database_url()
# Example: engine = create_engine(get_database_url())
