import asyncio
import json
from logging import getLogger

import websockets

from signalrca.ws_transport_params import WebSocketParameters

logger = getLogger()


class SignalRAsyncClient:
    def __init__(self, url, hub):
        self.url = url
        self.hubs = {}
        self._invokes_counter = -1
        self.hub_name = hub
        self.received = EventHook()
        self.received.add_hooks(self.handle_hub_message, self.handle_error)
        self.error = EventHook()
        self.exception = EventHook()
        self._hub_handlers = {}
        self.started = False
        self.invokes_data = {}
        self._ws_params = None
        self.ws_loop = None
        self._set_loop_and_queue()

    async def handle_hub_message(self, **kwargs):
        messages = kwargs['M'] if 'M' in kwargs and len(kwargs['M']) > 0 else {}
        for inner_data in messages:
            method = inner_data['M']
            if method in self._hub_handlers:
                arguments = inner_data['A']
                await self._hub_handlers[method].async_trigger_hooks(*arguments)

    async def handle_error(self, **data):
        if 'E' in data:
            invoke_index = int(data.get('I', -1))
            await self.error.async_trigger_hooks({'error': data['E'],
                                            'call_arguments': self.invokes_data.get(invoke_index)})

    def start(self):
        self._ws_params = WebSocketParameters(self.url, self.hub_name)
        self._connect()

    def invoke(self, method, *data):
        self._invokes_counter += 1
        self.put_items_into_queue({'H': self.hub_name, 'M': method, 'A': data,
                                   'I': self._invokes_counter})
        self.invokes_data[self._invokes_counter] = {'hub_name': self.hub_name, 'method': method,
                                                    'data': data}

    def close(self):
        asyncio.Task(self.invoke_queue.put(('close', )), loop=self.ws_loop)

    def subscribe_to_event(self, event_id, handler):
        if event_id not in self._hub_handlers:
            self._hub_handlers[event_id] = EventHook()
        self._hub_handlers[event_id].add_hooks(handler)

    def put_items_into_queue(self, message):
        asyncio.Task(self.invoke_queue.put(('invoke', message)), loop=self.ws_loop)

    def _set_loop_and_queue(self):
        try:
            self.ws_loop = asyncio.get_event_loop()
        except RuntimeError:
            self.ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.ws_loop)
        self.invoke_queue = asyncio.Queue(loop=self.ws_loop)

    def _connect(self):
        self._conn_handler = asyncio.ensure_future(self._socket(self.ws_loop), loop=self.ws_loop)

    async def _socket(self, loop):
        async with websockets.connect(self._ws_params.socket_url,
                                      extra_headers=self._ws_params.headers, loop=loop) as self.ws:
            self.started = True
            await self._master_handler(self.ws)

    async def _master_handler(self, ws):
        consumer_task = asyncio.ensure_future(self.handle_exception(self._consumer_handler(ws)), loop=self.ws_loop)
        producer_task = asyncio.ensure_future(self.handle_exception(self._producer_handler(ws)), loop=self.ws_loop)
        done, pending = await asyncio.wait([consumer_task, producer_task],
                                           loop=self.ws_loop, return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()

    async def _consumer_handler(self, ws):
        while True:
            message = await ws.recv()
            if len(message) > 0:
                data = json.loads(message)
                await self.received.async_trigger_hooks(**data)

    async def _producer_handler(self, ws):
        while True:
            event = await self.invoke_queue.get()
            if event is not None:
                if event[0] == 'invoke':
                    await ws.send(json.dumps(event[1]))
                elif event[0] == 'close':
                    logger.info('close signal received')
                    await ws.close()
                    while ws.open is True:
                        await asyncio.sleep(0.1)
                    else:
                        self.started = False
                        break
                else:
                    raise Exception('Invalid event type: %s', event[0])
            else:
                break
            self.invoke_queue.task_done()

    def run_forever(self):
        if not self.ws_loop.is_running():
            self.ws_loop.run_forever()

    async def handle_exception(self, coroutine):
        try:
            await coroutine
        except Exception as error:
            logger.exception('Caught exception')
            logger.error('exception occurred in the loop: %s, with details: %s', self.ws_loop,
                         error)
            self.ws_loop.stop()
            self.exception.trigger_hooks(error)


class EventHook:
    def __init__(self):
        self._handlers = []

    def add_hooks(self, *handlers):
        self._handlers.extend(handlers)
        return self

    async def async_trigger_hooks(self, *args, **kwargs):
        for handler in self._handlers:
            await handler(*args, **kwargs)

    def trigger_hooks(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)


