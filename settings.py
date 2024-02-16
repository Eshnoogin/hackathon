from dotenv import load_dotenv

from pathlib import Path
import os

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

openrouteservice_key = os.getenv("openrouteservice_key")
geocoding_key = os.getenv("geocoding_key")
