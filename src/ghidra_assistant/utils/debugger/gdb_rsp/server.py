from __future__ import annotations

import socket
from contextlib import closing
from typing import Protocol

from .protocol import GDBRemoteError, StopReply, decode_hex, decode_packet, encode_hex, encode_packet, parse_hex_uint


class GDBTarget(Protocol):
    def stop_reply(self) -> StopReply: ...
    def target_xml(self) -> str: ...
    def read_all_registers(self) -> str: ...
    def write_all_registers(self, data: str) -> None: ...
    def read_register(self, index: int) -> str: ...
    def write_register(self, index: int, data: str) -> None: ...
    def read_memory(self, address: int, length: int) -> bytes: ...
    def write_memory(self, address: int, data: bytes) -> None: ...
    def insert_software_breakpoint(self, address: int, kind: int = 4) -> None: ...
    def remove_software_breakpoint(self, address: int, kind: int = 4) -> None: ...
    def continue_execution(self, address: int | None = None) -> StopReply: ...
    def step_instruction(self, address: int | None = None) -> StopReply: ...
    def supports_execution_control(self) -> bool: ...
    def supports_software_breakpoints(self) -> bool: ...


class GDBRemoteServer:
    def __init__(self, target: GDBTarget, packet_size: int = 0x4000) -> None:
        self.target = target
        self.packet_size = packet_size
        self.no_ack_mode = False
        self._connected = True
        self._client_features: set[str] = set()

    def serve_forever(self, host: str = "127.0.0.1", port: int = 9000) -> None:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(1)
            while self._connected:
                conn, _ = server.accept()
                with closing(conn):
                    self._reset_connection_state()
                    self.serve_connection(conn)

    def serve_connection(self, conn: socket.socket) -> None:
        self._reset_connection_state()
        while self._connected:
            try:
                payload = self._read_packet(conn)
                if payload is None:
                    continue
                response = self.handle_packet(payload)
                conn.sendall(encode_packet(response))
            except (BrokenPipeError, ConnectionError, ConnectionResetError, OSError):
                return

    def handle_packet(self, payload: str) -> str:
        try:
            if payload == "?":
                return self.target.stop_reply().to_payload(include_stop_reason=self._supports_stop_reason("swbreak"))
            if payload == "qAttached":
                return "1"
            if payload == "qC":
                return "QC1"
            if payload == "qfThreadInfo" or payload == "qsThreadInfo":
                return "l"
            if payload == "vMustReplyEmpty":
                return ""
            if payload == "QStartNoAckMode":
                self.no_ack_mode = True
                return "OK"
            if payload.startswith("qSupported"):
                return self._handle_q_supported(payload)
            if payload.startswith("qXfer:features:read:target.xml:"):
                return self._handle_target_xml(payload)
            if payload == "g":
                return self.target.read_all_registers()
            if payload.startswith("G"):
                self.target.write_all_registers(payload[1:])
                return "OK"
            if payload.startswith("p"):
                return self.target.read_register(parse_hex_uint(payload[1:]))
            if payload.startswith("P"):
                register, value = payload[1:].split("=", 1)
                self.target.write_register(parse_hex_uint(register), value)
                return "OK"
            if payload.startswith("m"):
                address, length = self._parse_addr_len(payload[1:])
                return encode_hex(self.target.read_memory(address, length))
            if payload.startswith("M"):
                addr_len, encoded = payload[1:].split(":", 1)
                address, length = self._parse_addr_len(addr_len)
                data = decode_hex(encoded)
                if len(data) != length:
                    raise GDBRemoteError("E01", "memory write length mismatch")
                self.target.write_memory(address, data)
                return "OK"
            if payload.startswith("c"):
                if not self.target.supports_execution_control():
                    raise GDBRemoteError("E01", "execution control is not implemented yet")
                return self.target.continue_execution(self._parse_resume_addr(payload)).to_payload(
                    include_stop_reason=self._supports_stop_reason("swbreak")
                )
            if payload.startswith("s"):
                if not self.target.supports_execution_control():
                    raise GDBRemoteError("E01", "execution control is not implemented yet")
                return self.target.step_instruction(self._parse_resume_addr(payload)).to_payload(
                    include_stop_reason=self._supports_stop_reason("swbreak")
                )
            if payload.startswith("Z0"):
                if not self.target.supports_software_breakpoints():
                    raise GDBRemoteError("E01", "software breakpoints are not implemented yet")
                address, kind = self._parse_breakpoint(payload[3:])
                self.target.insert_software_breakpoint(address, kind)
                return "OK"
            if payload.startswith("z0"):
                if not self.target.supports_software_breakpoints():
                    raise GDBRemoteError("E01", "software breakpoints are not implemented yet")
                address, kind = self._parse_breakpoint(payload[3:])
                self.target.remove_software_breakpoint(address, kind)
                return "OK"
            if payload == "D":
                self._connected = False
                return "OK"
            if payload == "k":
                self._connected = False
                return "OK"
            return ""
        except GDBRemoteError as exc:
            return exc.code
        except Exception:
            return "E01"

    def _handle_q_supported(self, payload: str) -> str:
        self._client_features = self._parse_q_supported_features(payload)
        features = [
            f"PacketSize={self.packet_size:x}",
            "QStartNoAckMode+",
            "qXfer:features:read+",
        ]
        if self.target.supports_software_breakpoints():
            features.append("swbreak+")
        return ";".join(features)

    def _handle_target_xml(self, payload: str) -> str:
        _, offset_len = payload.rsplit(":", 1)
        offset_raw, length_raw = offset_len.split(",", 1)
        offset = parse_hex_uint(offset_raw)
        length = parse_hex_uint(length_raw)
        xml = self.target.target_xml().encode("utf-8")
        chunk = xml[offset : offset + length]
        prefix = "l" if offset + length >= len(xml) else "m"
        return prefix + chunk.decode("utf-8")

    def _parse_addr_len(self, payload: str) -> tuple[int, int]:
        address_raw, length_raw = payload.split(",", 1)
        return parse_hex_uint(address_raw), parse_hex_uint(length_raw)

    def _parse_resume_addr(self, payload: str) -> int | None:
        if len(payload) == 1:
            return None
        return parse_hex_uint(payload[1:])

    def _parse_breakpoint(self, payload: str) -> tuple[int, int]:
        address_raw, kind_raw = payload.split(",", 1)
        return parse_hex_uint(address_raw), parse_hex_uint(kind_raw)

    def _parse_q_supported_features(self, payload: str) -> set[str]:
        _, _, raw_features = payload.partition(":")
        if not raw_features:
            return set()

        features: set[str] = set()
        for feature in raw_features.split(";"):
            if not feature:
                continue
            if feature[-1] in "+-?":
                name = feature[:-1]
            elif "=" in feature:
                name = feature.split("=", 1)[0]
            else:
                name = feature
            if name:
                features.add(name)
        return features

    def _supports_stop_reason(self, reason: str) -> bool:
        return reason in self._client_features

    def _reset_connection_state(self) -> None:
        self.no_ack_mode = False
        self._client_features.clear()

    def _read_packet(self, conn: socket.socket) -> str | None:
        while True:
            marker = conn.recv(1)
            if marker == b"":
                raise ConnectionError("gdb client disconnected")
            if marker in {b"+", b"-"}:
                continue
            if marker == b"\x03":
                return None
            if marker != b"$":
                continue

            payload = bytearray()
            while True:
                byte = conn.recv(1)
                if byte == b"#":
                    break
                if byte == b"":
                    raise ConnectionError("gdb client disconnected while sending packet")
                payload.extend(byte)

            checksum = conn.recv(2)
            packet = b"$" + bytes(payload) + b"#" + checksum
            decoded = decode_packet(packet)
            if not self.no_ack_mode:
                conn.sendall(b"+")
            return decoded