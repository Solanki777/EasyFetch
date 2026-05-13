from backend.config import settings
import os

print(f"CWD: {os.getcwd()}")
print(f"GROQ_API_KEY from env: {os.getenv('GROQ_API_KEY')}")
print(f"settings.groq_api_key: {settings.groq_api_key}")
print(f"GOOGLE_SERVICE_ACCOUNT_JSON: {os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')}")
