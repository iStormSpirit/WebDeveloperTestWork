import os
from functools import partial

import databases
import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.types import DECIMAL

from server.enums import Instrument, OrderSide, OrderStatus

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "test")
PS_USER = os.getenv("PS_USER", "user")
PS_PASS = os.getenv("PS_PASS", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{PS_USER}:{PS_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
database = databases.Database(SQLALCHEMY_DATABASE_URL)

ReqColumn = partial(Column, nullable=False)
metadata = sqlalchemy.MetaData()

orders_table = sqlalchemy.Table(
    'orders',
    metadata,
    ReqColumn('uuid', UUID(as_uuid=True), primary_key=True),
    ReqColumn('instrument', ENUM(Instrument)),
    ReqColumn('side', ENUM(OrderSide)),
    ReqColumn('status', ENUM(OrderStatus)),
    ReqColumn('amount', Integer),
    ReqColumn('price', DECIMAL),
    ReqColumn('address', String),
    ReqColumn('creation_time', DateTime()),
    ReqColumn('change_time', DateTime()),
)
