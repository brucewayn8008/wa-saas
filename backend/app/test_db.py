import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

from sqlalchemy import create_engine

print("Connecting...")
try:
    engine = create_engine("postgresql+psycopg://postgres:postgres@localhost/wa_mark2", pool_pre_ping=True)
    with engine.connect() as conn:
        print("Connected successfully.")
except Exception as e:
    print(f"Error: {e}")
