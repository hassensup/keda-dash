from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Your existing middleware setup code goes here

# Add StaticFiles for serving frontend static files
app.mount("/static", StaticFiles(directory="path_to_static_files"), name="static")

# Function to get JWT secret with default value
def get_jwt_secret():
    return "default_jwt_secret"
