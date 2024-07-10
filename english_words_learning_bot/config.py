import os
from dotenv import load_dotenv

load_dotenv()


# Load environment variables
def load_config():
    return {
        'API_TOKEN': os.getenv('API_TOKEN'),
        'ADMIN_ID': int(os.getenv('ADMIN_ID')),
        'POSTGRES_USER': os.getenv('POSTGRES_USER'),
        'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'POSTGRES_DB': os.getenv('POSTGRES_DB'),
        'DB_HOST': os.getenv('DB_HOST'),
        'DB_PORT': os.getenv('DB_PORT'),
    }
