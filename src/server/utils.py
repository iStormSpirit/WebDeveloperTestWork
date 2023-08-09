from decimal import Decimal
from random import choice, uniform

import fastapi

from server.enums import Instrument, OrderStatus
from server.models import server_messages
from server.models.base import Quote
from server.models.db import database, orders_table
from server.ntpro_server import NTProServer


async def create_order(websocket, uuid, new_order):
    create_query = orders_table.insert().values(
        uuid=uuid, address=str(websocket.client),
        **new_order.dict()).returning(
        orders_table.c.uuid
    )
    await database.connect()
    record = await database.fetch_one(create_query)

    await database.disconnect()
    uuid_from_db = dict(zip(record, record._mapping.values())).get('uuid')

    return uuid_from_db


async def update_order(uuid, order):
    update_query = orders_table.update().where(
        orders_table.c.uuid == uuid).values(
        status=order.dict().get('status'),
        change_time=order.dict().get('change_time')).returning(
        orders_table.c.uuid
    )
    await database.connect()
    record = await database.execute(update_query)
    await database.disconnect()

    return record


async def gen_order(server: NTProServer, websocket: fastapi.WebSocket):
    orders = server.orders[websocket.client]
    active_orders_keys = [key for key, value in orders.items() if value.status == OrderStatus.active]
    if not active_orders_keys:
        return

    key_change = choice(active_orders_keys)
    order_change = orders[key_change]
    order_change.status = choice([OrderStatus.filled, OrderStatus.rejected])
    await server.send(server_messages.ExecutionReport(
        order_id=key_change,
        order_status=order_change.status),
        websocket
    )


async def gen_quote(server: NTProServer):
    instrument = choice(list(Instrument))
    quote_values = sorted([uniform(30, 40) for _ in range(4)])
    server.quotes[instrument].append(Quote(
        bid=Decimal.from_float(quote_values[1]),
        offer=Decimal.from_float(quote_values[2]),
        min_amount=Decimal.from_float(quote_values[0]),
        max_amount=Decimal.from_float(quote_values[3])))

    for client, client_subscribes in server.subscribes.items():
        if instrument in client_subscribes.values():
            websocket = server.connections.get(client)
            await server.send(
                server_messages.MarketDataUpdate(
                    subscription_id=client_subscribes.inverse.get(instrument),
                    instrument=instrument,
                    quotes=server.quotes[instrument]),
                websocket
            )
