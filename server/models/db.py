import os
from functools import partial

import databases
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import DECIMAL

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "testdev")
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = (f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
database = databases.Database(SQLALCHEMY_DATABASE_URL)

Base = declarative_base()

ReqColumn = partial(Column, nullable=False)


class Instrument(Base):
    __tablename__ = 'instruments'
    id = Column(Integer, primary_key=True, index=True)
    name = ReqColumn(String(100), unique=True)
