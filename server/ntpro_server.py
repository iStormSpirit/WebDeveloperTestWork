import asyncio
import json
import uuid
from typing import List

import fastapi
import pydantic
import starlette.datastructures
from bidict import bidict

from server.enums import Instrument
from server.message_processors import gen_quote
from server.models import base, client_messages, server_messages

TIMEOUT = 10


class NTProServer:
    def __init__(self):
        self.connections: dict[starlette.datastructures.Address, fastapi.WebSocket] = {}
        self.subscribes: dict[starlette.datastructures.Address, bidict] = {}
        self.orders: dict[starlette.datastructures.Address, dict[uuid.UUID, base.OrderIn]] = {}
        self.quotes: dict[Instrument, List[base.Quote]] = dict(zip(Instrument, [[] for _ in range(len(Instrument))]))

    async def connect(self, websocket: fastapi.WebSocket):
        await websocket.accept()
        self.connections[websocket.client] = websocket
        self.subscribes[websocket.client] = bidict()
        self.orders[websocket.client] = {}

    async def disconnect(self, websocket: fastapi.WebSocket):
        self.connections.pop(websocket.client)
        self.subscribes.pop(websocket.client)
        self.orders.pop(websocket.client)

    async def serve(self, websocket: fastapi.WebSocket):
        while True:
            try:
                raw_envelope = await asyncio.wait_for(websocket.receive_json(), timeout=10)
                envelope = client_messages.ClientEnvelope.parse_obj(raw_envelope)
                message = envelope.get_parsed_message()
                response = await message.process(self, websocket)
                await self.send(response, websocket)
            except asyncio.TimeoutError:
                await gen_quote(self)
                await websocket.send_text(str(websocket.client))
            except pydantic.ValidationError as ex:
                await self.send(server_messages.ErrorInfo(reason=str(ex)), websocket)
            except json.decoder.JSONDecodeError:
                await self.send(server_messages.ErrorInfo(
                    reason='The message is not a valid JSON'), websocket)
            except Exception as ex:
                await self.send(server_messages.ErrorInfo(reason=str(ex)), websocket)
                continue

    @staticmethod
    async def send(message: base.MessageT, websocket: fastapi.WebSocket):
        await websocket.send_text(
            server_messages.ServerEnvelope(message_type=message.get_type(),
                                           message=message.dict(by_alias=True)
                                           ).json(by_alias=True)
        )
