from __future__ import annotations

from decimal import Decimal
from random import choice, uniform
from typing import TYPE_CHECKING
from uuid import uuid4

from server.enums import Instrument, OrderStatus
from server.models import server_messages
from server.models.base import OrderIn, OrderOut, Quote
from server.models.db import database, orders_table

if TYPE_CHECKING:
    import fastapi

    from server.models import client_messages
    from server.ntpro_server import NTProServer


async def subscribe_market_data_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.SubscribeMarketData,
):
    instrument = message.dict().get('instrument')
    uuid = uuid4()
    server.subscribes[websocket.client].update({uuid: instrument})
    return server_messages.SuccessInfo(subscription_id=uuid)


async def unsubscribe_market_data_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.UnsubscribeMarketData,
):
    uuid = message.dict().get('subscription_id')
    server.subscribes[websocket.client].pop(uuid)
    return server_messages.SuccessInfo(subscription_id=uuid)


async def place_order_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.PlaceOrder,
):
    new_order = OrderIn(**message.dict())
    uuid = uuid4()
    server.orders[websocket.client][uuid] = new_order
    return server_messages.SuccessInfo(subscription_id=uuid)


async def cancel_order_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.PlaceOrder,
):
    uuid = message.dict().get('order_id')
    order = server.orders[websocket.client].get(uuid)
    if order.status == OrderStatus.active:
        order.status = OrderStatus.cancelled
    return server_messages.ExecutionReport(order_id=uuid, order_status=order.status)


async def get_orders_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.PlaceOrder
):
    orders_list = [
        OrderOut(uuid=uuid, **values.dict()) for uuid, values in server.orders[websocket.client].items()
    ]
    return server_messages.OrdersList(orders=orders_list)


async def save_order_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.SaveOrder
):
    uuid = message.dict().get('order_id')
    order = server.orders[websocket.client].get(uuid)
    order_query = orders_table.insert().values(
        uuid=uuid, address=str(websocket.client), **order.dict()).returning(orders_table.c.uuid)
    await database.connect()
    record = await database.fetch_one(order_query)
    uuid_from_db = dict(zip(record, record.values())).get('uuid')
    await database.disconnect()
    return server_messages.OrderSaved(order_id=uuid_from_db)


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
