import json
from base64 import b64decode
from zlib import MAX_WBITS, decompress

from signalrca import SignalRAsyncClient


async def process_message(message):
    deflated_msg = decompress(b64decode(message), -MAX_WBITS)
    return json.loads(deflated_msg.decode())


async def on_debug(msg):
    if 'R' in msg and type(msg['R']) is not bool:
        decoded_msg = await process_message(msg['R'])
        print(decoded_msg)


async def on_error(msg):
    print(msg)


async def on_message(msg):
    decoded_msg = await process_message(msg)
    print(decoded_msg)


signalr_client = SignalRAsyncClient('https://socket.bittrex.com/signalr', hub='c2')

signalr_client.start()

signalr_client.received.add_hooks(on_debug)
signalr_client.error.add_hooks(on_error)

signalr_client.subscribe_to_event('uE', on_message)

signalr_client.invoke('queryExchangeState', 'BTC-ETH')
signalr_client.invoke('SubscribeToExchangeDeltas', 'BTC-ETH')

signalr_client.run_forever()
