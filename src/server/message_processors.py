from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from bidict import ValueDuplicationError

from server.enums import OrderStatus
from server.models import server_messages
from server.models.base import OrderIn, OrderOut
from server.utils import create_order, update_order

if TYPE_CHECKING:
    import fastapi

    from src.server.models import client_messages
    from src.server.ntpro_server import NTProServer


async def subscribe_market_data_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.SubscribeMarketData,
):
    instrument = message.dict().get('instrument')
    uuid = uuid4()
    try:
        server.subscribes[websocket.client].update({uuid: instrument})
    except ValueDuplicationError:
        return server_messages.ErrorInfo(reason='The subscribe already exists')
    return server_messages.SuccessInfo(subscription_id=uuid)


async def unsubscribe_market_data_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.UnsubscribeMarketData,
):
    uuid = message.dict().get('subscription_id')
    try:
        server.subscribes[websocket.client].pop(uuid)
    except KeyError:
        return server_messages.ErrorInfo(reason='The subscribe does not exist')
    return server_messages.SuccessInfo(subscription_id=uuid)


async def place_order_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.PlaceOrder,
):
    new_order = OrderIn(**message.dict())
    uuid = uuid4()
    server.orders[websocket.client][uuid] = new_order
    uuid_from_db = await create_order(websocket, uuid, new_order)
    return server_messages.ExecutionReport(order_id=uuid_from_db, order_status=new_order.status)


async def cancel_order_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.PlaceOrder,
):
    uuid = message.dict().get('order_id')
    try:
        order = server.orders[websocket.client].get(uuid)
        if order.status == OrderStatus.active:
            order.status = OrderStatus.cancelled
            order.change_time = datetime.now()
            uuid_from_db = await update_order(uuid, order)
        else:
            return server_messages.ErrorInfo(
                reason=f'The order is {order.status.name}')
        return server_messages.ExecutionReport(
            order_id=uuid_from_db, order_status=order.status)
    except AttributeError:
        return server_messages.ErrorInfo(reason='The order does not exist')


async def get_orders_processor(
        server: NTProServer,
        websocket: fastapi.WebSocket,
        message: client_messages.PlaceOrder
):
    orders_list = [
        OrderOut(uuid=uuid, **values.dict()) for uuid, values in server.orders[websocket.client].items()
    ]
    return server_messages.OrdersList(orders=orders_list)
