import os

LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'ERROR')

API_URL_MANUAL = os.getenv('API_URL_MANUAL', "http://localhost:8003/freq/manual")
API_URL_SETTINGS = os.getenv('API_URL_SETTINGS', "http://localhost:8003/freq/settings")
SETTINGS_FILE = os.getenv('SETTINGS_FILE', 'etc/settings.json')