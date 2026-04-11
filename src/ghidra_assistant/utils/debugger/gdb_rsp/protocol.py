from __future__ import annotations

from dataclasses import dataclass


class GDBRemoteError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True, frozen=True)
class StopReply:
    signal: int = 5
    reason: str | None = None

    def to_payload(self, *, include_stop_reason: bool = True) -> str:
        if include_stop_reason and self.reason == "swbreak":
            return f"T{self.signal:02x}swbreak:;"
        return f"S{self.signal:02x}"


def rsp_checksum(payload: str | bytes) -> str:
    data = payload.encode("ascii") if isinstance(payload, str) else payload
    return f"{sum(data) % 256:02x}"


def encode_packet(payload: str | bytes) -> bytes:
    data = payload.encode("ascii") if isinstance(payload, str) else payload
    checksum = rsp_checksum(data).encode("ascii")
    return b"$" + data + b"#" + checksum


def decode_packet(packet: bytes | str) -> str:
    data = packet.encode("ascii") if isinstance(packet, str) else packet
    if len(data) < 4 or not data.startswith(b"$"):
        raise ValueError("packet must start with '$' and include checksum")

    marker = data.rfind(b"#")
    if marker == -1 or marker + 3 != len(data):
        raise ValueError("packet must terminate with '#xx'")

    payload = data[1:marker]
    checksum = data[marker + 1 : marker + 3].decode("ascii")
    if rsp_checksum(payload) != checksum.lower():
        raise ValueError("packet checksum mismatch")
    return payload.decode("ascii")


def encode_hex(data: bytes) -> str:
    return data.hex()


def decode_hex(data: str) -> bytes:
    return bytes.fromhex(data)


def parse_hex_uint(value: str) -> int:
    return int(value, 16)


def encode_uint_le(value: int, width: int) -> str:
    return int(value).to_bytes(width, "little", signed=False).hex()


def decode_uint_le(data: str) -> int:
    return int.from_bytes(bytes.fromhex(data), "little", signed=False)


def encode_unavailable(width: int) -> str:
    return "x" * (width * 2)
