import socket, time, struct, atexit
from .utils import *
from .definitions import *

import typing
if typing.TYPE_CHECKING:
    from ghidra_assistant import GhidraAssistant

class GA_Client():
    def __init__(self, type : ConnectionType) -> None:
        self.connection_type = type
        self.conn = socket.socket()
        self.conn.settimeout(.1)
        atexit.register(self.close_connection)
        self.command_helper = GA_Server_Packet()
        try:
            self.conn.connect((GA_SERVER_HOST, GA_SERVER_PORT))
            ok(f"Connected to {GA_SERVER_HOST}:{GA_SERVER_PORT}")
        except socket.error as e:
            error(str(e))
            exit(1)

    def close_connection(self):
        self.conn.send(self.command_helper.create_packet(Commands.CLIENT_SEND_DISCONNECT))

    def handle_recv(self):
        data = b""
        try:
            while True:
                data += self.conn.recv(GA_SERVER_BLOCKSIZE)
                if data == b'':
                    return data
        except Exception as e:
            if type(e) == socket.timeout:
                return data

    def recv_wait_unconditionally(self):
        while True:
            dat = self.handle_recv()
            if dat is not None and len(dat) > 0:
                break
        return dat

    def recv_amount(self, amount):
        dat = b""
        while True:
            try:
                dat += self.conn.recv(0x1000)
            except:
                time.sleep(.001)
            if len(dat) == amount:
                break
        return dat

    def hello_reply(self):
        self.conn.send(self.command_helper.create_packet(Commands.CLIENT_HELLO, struct.pack("<I", self.connection_type.value)))
        #Wait for reply
        dat = self.recv_wait_unconditionally()
        cmd, data = self.command_helper.parse_packet(dat)
        if cmd != Commands.SERVER_HELLO:
            error("Server did not respond with valid response!")
        else:
            ok("Server responed to hello request!")

    def request_properties(self):
        pass
