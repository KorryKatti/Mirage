import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set default SECRET_KEY if not provided
if not os.getenv("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "mirage_development_secret_key"
    print("WARNING: Using default SECRET_KEY. For production, set a secure SECRET_KEY in .env file.")

if __name__ == "__main__":
    print("Starting Mirage application...")
    uvicorn.run("mirage.main:app", host="0.0.0.0", port=8000, reload=True) 