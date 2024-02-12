from enum import Enum
import socket, time, struct, typing
from .utils import *
from multiprocessing import Process

if typing.TYPE_CHECKING:
    from ..ghidra_assistant import GhidraAssistant

GA_SERVER_HOST          = "localhost"
GA_SERVER_PORT          = 9998
GA_SERVER_BLOCKSIZE     = 0x1000
GA_SERVER_TEST_PING     = 1000

class ConnectionType(Enum):
    Unknown = 0
    Emulator = 1
    Concrete_Target = 2

class Commands(Enum):
    CLIENT_HELLO                = 0 #client to server
    SERVER_HELLO                = 1 #Server to client
    REQUEST_SNAPSHOT            = 2 #Client requests snapshot
    RECEIVE_SNAPSHOT            = 3 #Server responds with snapshot data
    CLIENT_READY                = 4
    SERVER_READY                = 5
    CLIENT_REQUEST_PROPERTIES   = 6
    SERVER_REQUEST_PROPERTIES   = 7
    CLIENT_SEND_DISCONNECT      = 8
    SERVER_DISCONNECT_RESERVED  = 9
    CLIENT_PING_SERVER          = 10 #Client pings server
    SERVER_PING_CLIENT          = 11 #Server pings client
    INVALID_CMD =               0xff

class GA_Server_Packet():
    def __init__(self) -> None:
        pass

    def content_fill(self, packet, fill = GA_SERVER_BLOCKSIZE):
        if len(packet) > fill:
            raise "Packet overflows fill alignment"
        return packet + b"\x00" * (fill - len(packet))

    def create_packet(self, command : Commands, data = b""):
        if len(data) > (GA_SERVER_BLOCKSIZE - 4):
            raise "Not allowed to send so much data in a single packet"
        packet = struct.pack("<I", command.value) + data
        return self.content_fill(packet, GA_SERVER_BLOCKSIZE)

    def parse_packet(self, data):
        if len(data) != GA_SERVER_BLOCKSIZE:
            warn("Invalid packet received! Dropping")
            return Commands.INVALID_CMD, None
        cmd = Commands(struct.unpack("<I", data[:4])[0])
        return cmd, data[4:]

class GA_Server_Client():
    def __init__(self, conn : socket.socket, address, ga : "GhidraAssistant") -> None:
        self.address = address
        self.conn : socket.socket = conn
        self.conn.settimeout(.1)
        self.ga = ga
        self.command_helper = GA_Server_Packet()
        self.connection_type = ConnectionType.Unknown
        self.test_ping = 0
        self.testing_connection = False

    def run_threaded(self):
        self.threaded_server = Process(target=self.client_main)
        self.threaded_server.start()

    def handle_recv(self):
        data = b""
        try:
            while True:
                data += self.conn.recv(0x1000)
                if data == b'':
                    return data
        except Exception as e:
            if type(e) == socket.timeout:
                return data
            else:
                error(str(e))

    def handle_request_properties(self):
        pass

    def client_main(self):
        while True:
            dat = self.handle_recv()
            if dat is not None and len(dat) > 0:
                cmd, data = self.command_helper.parse_packet(dat)
                if cmd == Commands.INVALID_CMD:
                    continue
                elif cmd == Commands.CLIENT_HELLO:
                    self.connection_type = ConnectionType(struct.unpack("<I", data[:4])[0])
                    #Respond with SERVER_HELLO
                    self.conn.send(self.command_helper.create_packet(Commands.SERVER_HELLO))
                elif cmd == Commands.CLIENT_REQUEST_PROPERTIES:
                    self.handle_request_properties()
                elif cmd == Commands.CLIENT_SEND_DISCONNECT:
                    info(f"Closing connection from {self.address}")
                    return
                elif cmd == Commands.CLIENT_PING_SERVER:
                    self.test_ping = 0
                    if self.testing_connection:
                        self.testing_connection = False
                    else:
                        #Reply to ping
                        self.conn.send(self.command_helper.create_packet(Commands.SERVER_PING_CLIENT))

                else:
                    self.conn.send(self.command_helper.create_packet(Commands.INVALID_CMD))
            else:
                time.sleep(.1)

class GA_Server():
    def __init__(self, ghidra_assistent : "GhidraAssistant", host=GA_SERVER_HOST, port=GA_SERVER_PORT) -> None:
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        self.ga = ghidra_assistent
        self.clients = {}

    def run_threaded(self):
        self.threaded_client = Process(target=self.server_main)
        self.threaded_client.start()

    def server_main(self):
        ok("GA_server is now ready to receive connections!")
        while True:
            conn, c_addr = self.server.accept()
            info(f"Received connection from : {c_addr}")
            self.clients[c_addr] = GA_Server_Client(conn, c_addr, self.ga)
            self.clients[c_addr].run_threaded()