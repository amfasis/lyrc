#!/usr/bin/env python3

import asyncio
from concurrent.futures import ThreadPoolExecutor
import responses
import configparser
import logging

from command import CommandItem
from ir_thread import irsend_thread


######### Config variables
config = configparser.RawConfigParser(allow_no_value=True)
config.read("config.ini")

listen_address = config.get('server', 'listen_address', fallback='0.0.0.0')
listen_port = int(config.get('server', 'listen_port', fallback='7059'))

gpio_pin = int(config.get('pigpio', 'gpio_pin', fallback=22))
start_pigpio = bool(config.get('pigpio', 'start_pigpio', fallback=False))
keep_alive = int(config.get('pigpio', 'keep_alive', fallback=300))

config_path = config.get('remotes', 'path', fallback='/etc/lirc')

verbose = bool(config.get('logging', 'verbose', fallback=False))


######## Working state variables
queue = asyncio.Queue()
client_count = 0



########### Working logic
async def handle_client(reader, writer):
    logging.info("New client: {}".format(reader._transport._extra['peername']))
    request = None
    global loop

    global client_count
    if not client_count:
        loop.create_task(irsend_thread(queue, loop, config_path, gpio_pin, start_pigpio, verbose))

    client_count += 1

    while True:
        request = (await reader.read(255)).decode('utf8').rstrip()
        if not request:
            break

        logging.info(request)

        parts = request.split(" ")

        command = CommandItem(
            directive=parts[0], 
            remote=parts[1] if len(parts) > 1 else "",
            key_code=parts[2] if len(parts) > 2 else "",
            future=loop.create_future())

        await queue.put(command)
        
        try:
            result = await asyncio.wait_for(command.future, timeout=60)

            if isinstance(result, bool) and bool(result):
                response = responses.success(request)
            elif isinstance(result, list):
                response = responses.data(request, result)
            elif isinstance(result, str):
                response = responses.error(request, str(result))
            else:
                response = responses.error(request, "unknown error")

        except Exception as e:
            logging.exception("Exception in ir_thread", e, stack_info=True)
            response = responses.error(request, str(e))
            pass

        writer.write((response+"\n").encode('utf8'))

    logging.info("client done")
    writer.close()
    
    if keep_alive > 0:
        logging.info("Keep-alive sleep for {}s".format(keep_alive))
        try:
            await asyncio.sleep(keep_alive)
        except asyncio.CancelledError:
            pass
        
    client_count -= 1
    logging.info("Clients left: {}".format(client_count))
    if not client_count:
        logging.info("sending stop to irsend_thread")
        await queue.put("stop")




logging.basicConfig(level=logging.INFO)
logging.info("Starting LYRC")
loop = asyncio.get_event_loop()
server_coro = asyncio.start_server(handle_client, listen_address, listen_port)
server = loop.run_until_complete(server_coro) 
logging.info("Started LYRC, listening on {}:{}, blasting on GPIO-{}".format(listen_address, listen_port, gpio_pin))

try:
    loop.run_forever()
except KeyboardInterrupt:  # CTRL+C pressed
    pass

logging.info('Shutting down LYRC')
server.close()
loop.run_until_complete(server.wait_closed())
loop.close() 



