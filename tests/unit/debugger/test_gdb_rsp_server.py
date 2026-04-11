from ghidra_assistant.utils.debugger.gdb_rsp.protocol import StopReply
from ghidra_assistant.utils.debugger.gdb_rsp.server import GDBRemoteServer


class _Target:
    def __init__(self) -> None:
        self.registers = "1122"
        self.memory = {0x1000: b"\xAA\xBB"}
        self.xml = "<target/>"
        self.written_registers: list[str] = []
        self.written_memory: list[tuple[int, bytes]] = []
        self.continues: list[int | None] = []
        self.steps: list[int | None] = []
        self.inserted_breakpoints: list[tuple[int, int]] = []
        self.removed_breakpoints: list[tuple[int, int]] = []

    def stop_reply(self) -> StopReply:
        return StopReply(signal=5)

    def target_xml(self) -> str:
        return self.xml

    def read_all_registers(self) -> str:
        return self.registers

    def write_all_registers(self, data: str) -> None:
        self.written_registers.append(data)

    def read_register(self, index: int) -> str:
        return f"reg{index}"

    def write_register(self, index: int, data: str) -> None:
        self.written_registers.append(f"{index}:{data}")

    def read_memory(self, address: int, length: int) -> bytes:
        return self.memory.get(address, b"\x00" * length)

    def write_memory(self, address: int, data: bytes) -> None:
        self.written_memory.append((address, data))

    def continue_execution(self, address: int | None = None) -> StopReply:
        self.continues.append(address)
        return StopReply(signal=5)

    def step_instruction(self, address: int | None = None) -> StopReply:
        self.steps.append(address)
        return StopReply(signal=5)

    def insert_software_breakpoint(self, address: int, kind: int = 4) -> None:
        self.inserted_breakpoints.append((address, kind))

    def remove_software_breakpoint(self, address: int, kind: int = 4) -> None:
        self.removed_breakpoints.append((address, kind))

    def supports_execution_control(self) -> bool:
        return True

    def supports_software_breakpoints(self) -> bool:
        return True


def test_server_handles_core_query_packets() -> None:
    server = GDBRemoteServer(_Target(), packet_size=0x1234)

    assert server.handle_packet("?") == "S05"
    assert server.handle_packet("qAttached") == "1"
    assert server.handle_packet("qC") == "QC1"

    supported = server.handle_packet("qSupported:multiprocess+")
    assert "PacketSize=1234" in supported
    assert "qXfer:features:read+" in supported
    assert "QStartNoAckMode+" in supported
    assert "swbreak+" in supported


def test_server_serves_target_xml_in_chunks() -> None:
    target = _Target()
    target.xml = "abcdef"
    server = GDBRemoteServer(target)

    assert server.handle_packet("qXfer:features:read:target.xml:0,4") == "mabcd"
    assert server.handle_packet("qXfer:features:read:target.xml:4,4") == "lef"


def test_server_handles_register_and_memory_packets() -> None:
    target = _Target()
    server = GDBRemoteServer(target)

    assert server.handle_packet("g") == "1122"
    assert server.handle_packet("p1") == "reg1"
    assert server.handle_packet("m1000,2") == "aabb"

    assert server.handle_packet("Gdeadbeef") == "OK"
    assert target.written_registers[-1] == "deadbeef"

    assert server.handle_packet("P1=beef") == "OK"
    assert target.written_registers[-1] == "1:beef"

    assert server.handle_packet("M1000,2:0102") == "OK"
    assert target.written_memory[-1] == (0x1000, b"\x01\x02")


def test_server_handles_continue_and_single_step_packets() -> None:
    server = GDBRemoteServer(_Target())

    assert server.handle_packet("c") == "S05"
    assert server.handle_packet("c4000") == "S05"
    assert server.handle_packet("s") == "S05"
    assert server.handle_packet("s8000") == "S05"


def test_server_parses_resume_addresses_for_execution_packets() -> None:
    target = _Target()
    server = GDBRemoteServer(target)

    server.handle_packet("c1234")
    server.handle_packet("s5678")

    assert target.continues[-1] == 0x1234
    assert target.steps[-1] == 0x5678


def test_server_handles_software_breakpoint_packets() -> None:
    target = _Target()
    server = GDBRemoteServer(target)

    assert server.handle_packet("Z0,1000,4") == "OK"
    assert server.handle_packet("z0,1000,4") == "OK"
    assert target.inserted_breakpoints[-1] == (0x1000, 0x4)
    assert target.removed_breakpoints[-1] == (0x1000, 0x4)


def test_server_only_uses_swbreak_stop_reply_when_client_advertised_support() -> None:
    class _SwbreakTarget(_Target):
        def continue_execution(self, address: int | None = None) -> StopReply:
            self.continues.append(address)
            return StopReply(signal=5, reason="swbreak")

    target = _SwbreakTarget()
    server = GDBRemoteServer(target)

    assert server.handle_packet("qSupported:multiprocess+") == "PacketSize=4000;QStartNoAckMode+;qXfer:features:read+;swbreak+"
    assert server.handle_packet("c") == "S05"

    server.handle_packet("qSupported:multiprocess+;swbreak+")
    assert server.handle_packet("c") == "T05swbreak:;"


def test_serve_connection_treats_disconnect_as_normal_end_of_session() -> None:
    class _DisconnectingServer(GDBRemoteServer):
        def _read_packet(self, conn):
            raise ConnectionError("gdb client disconnected")

    server = _DisconnectingServer(_Target())
    server.no_ack_mode = True
    server._client_features = {"swbreak"}

    server.serve_connection(object())

    assert server.no_ack_mode is False
    assert server._client_features == set()
