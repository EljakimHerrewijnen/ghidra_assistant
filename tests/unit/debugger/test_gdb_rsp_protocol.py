from ghidra_assistant.utils.debugger.gdb_rsp.protocol import StopReply, decode_packet, encode_packet, rsp_checksum


def test_rsp_checksum_uses_modulo_256_sum() -> None:
    assert rsp_checksum("qSupported") == "37"


def test_encode_and_decode_round_trip() -> None:
    packet = encode_packet("g")

    assert packet == b"$g#67"
    assert decode_packet(packet) == "g"


def test_decode_rejects_invalid_checksum() -> None:
    try:
        decode_packet(b"$m1000,10#00")
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("expected checksum validation to fail")


def test_stop_reply_encodes_swbreak_reason() -> None:
    assert StopReply(signal=5, reason="swbreak").to_payload() == "T05swbreak:;"


def test_stop_reply_falls_back_to_plain_signal_when_reason_not_negotiated() -> None:
    assert StopReply(signal=5, reason="swbreak").to_payload(include_stop_reason=False) == "S05"
