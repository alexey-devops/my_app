import time
import os

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

print("Worker started. Listening for tasks...")
db_url = get_database_url()
print(f"Worker using DB URL (example, not used for connection yet): {db_url}")

# This is a placeholder for actual worker logic.
# In a real application, this would connect to a message queue (e.g., Redis, RabbitMQ)
# and process tasks.

while True:
    print("Worker is active, performing dummy task...")
    time.sleep(5) # Simulate work
