# backend/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# This is the connection URL for our PostgreSQL database running in Docker.
# It uses the credentials we defined in docker-compose.yml.
SQLALCHEMY_DATABASE_URL = "postgresql://myuser:mypassword@localhost/price_tracker_db"

# The 'engine' is the main entry point for SQLAlchemy to talk to the database.
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Each instance of SessionLocal will be a database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# We will inherit from this class to create each of the database models (tables).
Base = declarative_base()