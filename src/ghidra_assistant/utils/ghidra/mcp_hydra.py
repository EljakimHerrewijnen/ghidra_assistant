"""
MCP Hydra backend: client for the HATEOAS-style Ghidra HTTP plugin

This backend mirrors the simple interface used by MCPBackend while using the
new endpoints described in `bridge_mcp_hydra.py`.

Key capabilities implemented:
- List functions and basic info
- Fetch function details and disassembly
- Read memory efficiently
- Query current UI address and function

Notes:
- Defaults to host from env GHIDRA_HYDRA_HOST (or 127.0.0.1) and port 8192.
- API responses are expected to be JSON objects with a `result` field as
  described by the HATEOAS bridge. We simplify and handle minor variations.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, quote

try:
	import requests  # type: ignore
except Exception:  # pragma: no cover
	requests = None  # type: ignore

from .ghidra_backend import GhidraBackend, GhidraFunction, GhidraFunctionBasic, Mem

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
	v = os.environ.get(name)
	return v if v not in (None, "") else default


class _HydraClient:
	"""Minimal HTTP client for the Ghidra HATEOAS plugin.

	Shapes responses to a simplified dictionary when possible.
	"""

	def __init__(self, base_url: str) -> None:
		# Ensure trailing slash behavior is consistent
		if not base_url.endswith("/"):
			base_url += "/"
		self.base_url = base_url

	def _request(self, method: str, endpoint: str, *, params: Dict[str, Any] | None = None,
				 json: Dict[str, Any] | None = None, timeout: int = 10) -> Dict[str, Any]:
		url = urljoin(self.base_url, endpoint)
		try:
			if requests is None:
				return {"success": False, "error": "requests not installed", "status_code": None}
			resp = requests.request(method, url, params=params, json=json, timeout=timeout)
		except Exception as e:
			return {"success": False, "error": str(e), "status_code": None}

		try:
			data = resp.json()
		except ValueError:
			return {
				"success": False,
				"error": f"Non-JSON response (status={resp.status_code})",
				"status_code": resp.status_code,
				"text": resp.text[:500],
			}

		# Normalize minimal contract
		if not isinstance(data, dict):
			data = {"success": bool(resp.ok), "result": data}
		if "success" not in data:
			data["success"] = bool(resp.ok)
		if "status_code" not in data:
			data["status_code"] = resp.status_code
		return data

	def get(self, endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
		return self._request("GET", endpoint, params=params)

	def post(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
		return self._request("POST", endpoint, json=json)

	def patch(self, endpoint: str, json: Dict[str, Any]) -> Dict[str, Any]:
		return self._request("PATCH", endpoint, json=json)

	def delete(self, endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
		return self._request("DELETE", endpoint, params=params)


def _result_ok(data: Dict[str, Any]) -> bool:
	return isinstance(data, dict) and data.get("success") is True and "result" in data


def _get_first(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
	for k in keys:
		if k in d and d[k] not in (None, ""):
			return d[k]
	return default


class MCPHydraBackend(GhidraBackend):
	def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
		super().__init__()
		host = host or _env("GHIDRA_HYDRA_HOST", "127.0.0.1")
		port = port or int(_env("GHIDRA_HYDRA_PORT", "8192"))
		self.base_url = f"http://{host}:{port}/"
		self.http = _HydraClient(self.base_url)

		# Provide Mem-compatible callable for reads
		def _read_memory(addr: int | str, size: int) -> bytes:
			if isinstance(addr, int):
				address = hex(addr)
			else:
				address = addr
			params = {"address": address, "length": size, "format": "hex"}
			r = self.http.get("memory", params=params)
			if not _result_ok(r):
				# Return empty rather than throwing to keep parity with mcp_backend
				logger.debug("memory read failed: %s", r)
				return b""
			res = r["result"]
			# Prefer explicit hexBytes if present
			hex_bytes: str | None = res.get("hexBytes") if isinstance(res, dict) else None
			if hex_bytes:
				try:
					# Accept formats with/without 0x
					hb = hex_bytes.replace("0x", "").replace(" ", "")
					return bytes.fromhex(hb)
				except ValueError:
					pass
			# Fallback if server returns list of 0x??
			if isinstance(res, list) and all(isinstance(x, str) for x in res):
				try:
					return bytes(int(x, 16) for x in res if x.startswith("0x"))
				except Exception:
					return b""
			# Final fallback: rawBytes base64 is not decoded here to avoid extra deps
			return b""

		self.mem = Mem(_read_memory)

	# -------- convenience API used by the app --------

	def _list_functions(self, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
		r = self.http.get("functions", params={"offset": offset, "limit": limit})
		if not _result_ok(r):
			return []
		res = r["result"]
		return res if isinstance(res, list) else []

	@property
	def functions(self) -> Iterable[GhidraFunctionBasic]:
		"""Yield basic function objects using HATEOAS functions list."""
		# Fetch in pages to avoid huge loads; simple single page for now
		items = self._list_functions(offset=0, limit=1000)
		for item in items:
			if not isinstance(item, dict):
				continue
			name = _get_first(item, "name", "function_name", default="<unnamed>")
			# Common address field variants
			address = _get_first(
				item,
				"entry",
				"address",
				"entryPoint",
				"entry_address",
				default=None,
			)
			if isinstance(address, int):
				address = hex(address)
			if not isinstance(address, str):
				# Try from links if present
				address = item.get("id") or item.get("start") or "0x0"
			yield GhidraFunctionBasic(address, name)

	def get_function(self, basicFunction: GhidraFunctionBasic) -> GhidraFunction:
		"""Fetch detailed info, disassembly and bytes for a function."""
		address = basicFunction.address

		# Disassembly
		dis_r = self.http.get(f"functions/{address}/disassembly")
		disassembly: List[str] = []
		if _result_ok(dis_r) and isinstance(dis_r["result"], dict):
			ins = dis_r["result"].get("instructions", [])
			if isinstance(ins, list):
				for i in ins:
					if isinstance(i, dict):
						a = str(i.get("address", ""))
						b = str(i.get("bytes", ""))
						m = str(i.get("mnemonic", ""))
						o = str(i.get("operands", ""))
						disassembly.append(f"{a}: {b}  {m} {o}".rstrip())


		# Bytes: try to derive size from disassembly span; otherwise default
		raw_bytes = self.mem[int(address, 16): int(address, 16) + 0x100]  # up to 256 bytes
		size = len(raw_bytes)

		# Xrefs in/out
		incoming = self.get_xrefs_to(address)
		outgoing = self.get_xrefs_from(address)

		return GhidraFunction(
			address,
			basicFunction.name,
			[],
			None,
			raw_bytes,
			size,
			disassembly,
			decompiled_code=None,
			incoming_refs=incoming,
			outgoing_refs=outgoing,
		)

	def get_all_functions(self) -> List[GhidraFunction]:
		return [self.get_function(f) for f in self.functions]

	@property
	def cursor(self) -> int:
		r = self.http.get("address")
		if _result_ok(r):
			res = r["result"]
			addr = None
			if isinstance(res, dict):
				addr = _get_first(res, "address", "current", "value")
			if isinstance(addr, str):
				try:
					return int(addr, 16)
				except ValueError:
					pass
			if isinstance(addr, int):
				return addr
		return 0

	# Optional helpers, not required but handy
	def decompile_function_by_address(self, address: str) -> str:
		r = self.http.get(f"functions/{address}/decompile", params={"syntax_tree": "false", "style": "normalize"})
		if _result_ok(r) and isinstance(r["result"], dict):
			return _get_first(r["result"], "decompiled", "ccode", "decompiled_text", default="") or ""
		return ""

	def get_current_function(self) -> Optional[Dict[str, Any]]:
		r = self.http.get("function")
		return r.get("result") if _result_ok(r) else None

	# -------- extended features via HATEOAS tools --------

	def read_memory(self, address: int | str, length: int) -> bytes:
		if isinstance(address, int):
			address = hex(address)
		params = {"address": address, "length": length, "format": "hex"}
		r = self.http.get("memory", params=params)
		if not _result_ok(r):
			return b""
		res = r["result"]
		hex_bytes: str | None = res.get("hexBytes") if isinstance(res, dict) else None
		if hex_bytes:
			try:
				hb = hex_bytes.replace("0x", "").replace(" ", "")
				return bytes.fromhex(hb)
			except ValueError:
				return b""
		if isinstance(res, list) and all(isinstance(x, str) for x in res):
			try:
				return bytes(int(x, 16) for x in res if x.startswith("0x"))
			except Exception:
				return b""
		return b""

	def write_mem(self, address: int | str, data: bytes) -> bool:
		addr = hex(address) if isinstance(address, int) else address
		hexstr = data.hex()
		r = self.http.patch(f"memory/{addr}", json={"bytes": hexstr, "format": "hex"})
		return bool(r.get("success"))

	def disassemble_function(self, address: str) -> List[str]:
		r = self.http.get(f"functions/{address}/disassembly")
		out: List[str] = []
		if _result_ok(r) and isinstance(r["result"], dict):
			for i in r["result"].get("instructions", []) or []:
				if isinstance(i, dict):
					a = str(i.get("address", ""))
					b = str(i.get("bytes", ""))
					m = str(i.get("mnemonic", ""))
					o = str(i.get("operands", ""))
					out.append(f"{a}: {b}  {m} {o}".rstrip())
		return out

	def decompile_function_by_name(self, name: str) -> str:
		r = self.http.get(f"functions/by-name/{quote(name)}/decompile", params={"syntax_tree": "false", "style": "normalize"})
		if _result_ok(r) and isinstance(r["result"], dict):
			return _get_first(r["result"], "decompiled", "ccode", "decompiled_text", default="") or ""
		return ""

	def rename_function_by_address(self, function_address: str, new_name: str) -> bool:
		r = self.http.patch(f"functions/{function_address}", json={"name": new_name})
		return bool(r.get("success"))

	def rename_function(self, old_name: str, new_name: str) -> bool:
		r = self.http.patch(f"functions/by-name/{quote(old_name)}", json={"name": new_name})
		return bool(r.get("success"))

	def set_function_prototype(self, function_address: str, signature: str) -> bool:
		r = self.http.patch(f"functions/{function_address}", json={"signature": signature})
		return bool(r.get("success"))

	def set_function_comment(self, address: str, comment: str) -> bool:
		# Try function-level comment first (PATCH)
		r = self.http.patch(f"functions/{address}", json={"comment": comment})
		if r.get("success"):
			return True
		# Fallback to pre-comment at address
		r2 = self.http.post(f"memory/{address}/comments/pre", json={"comment": comment})
		return bool(r2.get("success"))

	def get_xrefs_to(self, address: str, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
		# Normalize address (API expects plain hex without 0x, often zero-padded)
		addr = address.lower().strip()
		if addr.startswith("0x"):
			addr = addr[2:]
		# Left-pad to even length (avoid odd-length hex)
		if len(addr) % 2 == 1:
			addr = "0" + addr
		r = self.http.get("xrefs", params={"to_addr": addr, "offset": offset, "limit": limit})
		if _result_ok(r):
			return [f['from_addr'] for f in r["result"]["references"]]
		return []

	def get_xrefs_from(self, address: str, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
		addr = address.lower().strip()
		if addr.startswith("0x"):
			addr = addr[2:]
		if len(addr) % 2 == 1:
			addr = "0" + addr
		r = self.http.get("xrefs", params={"from_addr": addr, "offset": offset, "limit": limit})
		if _result_ok(r):
			return [f['to_addr'] for f in r["result"]["references"]]
		return []

	# /functions/{address} endpoint
	def get_function_info(self, address: str) -> Optional[Dict[str, Any]]:
		r = self.http.get(f"functions/{address}")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def list_strings(self, offset: int = 0, limit: int = 2000, filter: Optional[str] = None) -> List[Dict[str, Any]]:
		params: Dict[str, Any] = {"offset": offset, "limit": limit}
		if filter:
			params["filter"] = filter
		r = self.http.get("strings", params=params)
		if _result_ok(r) and isinstance(r["result"], list):
			return r["result"]
		return []

	def list_data(self, offset: int = 0, limit: int = 100, addr: Optional[str] = None,
				  name: Optional[str] = None, name_contains: Optional[str] = None,
				  dtype: Optional[str] = None) -> List[Dict[str, Any]]:
		params: Dict[str, Any] = {"offset": offset, "limit": limit}
		if addr:
			params["addr"] = addr
		if name:
			params["name"] = name
		if name_contains:
			params["name_contains"] = name_contains
		if dtype:
			params["type"] = dtype
		r = self.http.get("data", params=params)
		if _result_ok(r) and isinstance(r["result"], list):
			return r["result"]
		return []

	def data_create(self, address: str, data_type: str, size: Optional[int] = None) -> bool:
		payload: Dict[str, Any] = {"address": address, "type": data_type}
		if size is not None:
			payload["size"] = size
		r = self.http.post("data", json=payload)
		return bool(r.get("success"))

	def data_rename(self, address: str, new_name: str) -> bool:
		r = self.http.post("data", json={"address": address, "newName": new_name})
		return bool(r.get("success"))

	def data_delete(self, address: str) -> bool:
		r = self.http.post("data/delete", json={"address": address, "action": "delete"})
		return bool(r.get("success"))

	def data_set_type(self, address: str, data_type: str) -> bool:
		r = self.http.post("data/type", json={"address": address, "type": data_type})
		return bool(r.get("success"))

	def functions_create(self, address: str) -> bool:
		r = self.http.post("functions", json={"address": address})
		return bool(r.get("success"))

	def functions_get_variables(self, address: Optional[str] = None, name: Optional[str] = None) -> List[Dict[str, Any]]:
		if address:
			r = self.http.get(f"functions/{address}/variables")
		elif name:
			r = self.http.get(f"functions/by-name/{quote(name)}/variables")
		else:
			return []
		if _result_ok(r) and isinstance(r["result"], list):
			return r["result"]
		return []

	# UI helpers
	def get_current_address(self) -> int:
		return self.cursor

	def get_current_function_address(self) -> Optional[str]:
		r = self.http.get("function")
		if _result_ok(r) and isinstance(r["result"], dict):
			addr = _get_first(r["result"], "entry", "address", "entryPoint")
			if isinstance(addr, int):
				return hex(addr)
			if isinstance(addr, str):
				return addr
		return None

	# Features not supported by HATEOAS plugin; implement as no-ops to preserve API
	def set_background_color(self, addresses: List[int], color: str = "java.awt.Color.YELLOW") -> None:
		logger.info("set_background_color is not supported by MCP Hydra backend; ignoring (%d addresses)", len(addresses))

	def clear_background_color(self) -> None:
		logger.info("clear_background_color is not supported by MCP Hydra backend; ignoring")

	def get_ghidra_memory_maps(self) -> List[Any]:
		# Try via documented segments endpoint if available
		segs = self.memory_list_segments()
		if segs:
			return segs
		logger.info("get_ghidra_memory_maps not available via HATEOAS API; returning empty list")
		return []

	def mmap_region(self, addr: int, name: str, size: int, read: bool = True, write: bool = True, execute: bool = False) -> None:
		raise NotImplementedError("Memory mapping is not supported by the HATEOAS API")

	# -------- Memory segments (best-effort based on API doc) --------

	def memory_list_segments(self) -> List[Dict[str, Any]]:
		"""List memory segments/blocks if the endpoint is available."""
		for ep in ("memory/segments", "segments"):
			r = self.http.get(ep)
			if _result_ok(r) and isinstance(r["result"], list):
				return r["result"]
		return []

	def memory_find_segment_containing(self, address: int | str) -> Optional[Dict[str, Any]]:
		addr = int(address, 16) if isinstance(address, str) else address
		for seg in self.memory_list_segments():
			try:
				start = seg.get("start") or seg.get("start_address") or seg.get("address")
				end = seg.get("end") or seg.get("end_address") or seg.get("stop")
				if start is None or end is None:
					continue
				start_v = int(start, 16) if isinstance(start, str) else int(start)
				end_v = int(end, 16) if isinstance(end, str) else int(end)
				if start_v <= addr <= end_v:
					return seg
			except Exception:
				continue
		return None

	def memory_create_segment(self, name: str, address: int | str, size: int,
							   read: bool = True, write: bool = True, execute: bool = False,
							   overlay: bool = False, initialized: bool = True, fill: int = 0) -> bool:
		addr = hex(address) if isinstance(address, int) else address
		payload = {
			"name": name,
			"address": addr,
			"size": size,
			"permissions": {"read": read, "write": write, "execute": execute},
			"overlay": overlay,
			"initialized": initialized,
			"fill": fill,
		}
		for ep in ("memory/segments", "segments"):
			r = self.http.post(ep, json=payload)
			if r.get("success"):
				return True
		return False

	def memory_delete_segment(self, name_or_id: str) -> bool:
		for ep in (f"memory/segments/{name_or_id}", f"segments/{name_or_id}"):
			r = self.http.delete(ep)
			if r.get("success"):
				return True
		return False

	def memory_update_segment_permissions(self, name_or_id: str, *, read: Optional[bool] = None,
										  write: Optional[bool] = None, execute: Optional[bool] = None) -> bool:
		perms: Dict[str, Any] = {}
		if read is not None:
			perms["read"] = read
		if write is not None:
			perms["write"] = write
		if execute is not None:
			perms["execute"] = execute
		if not perms:
			return True  # nothing to change
		payload = {"permissions": perms}
		for ep in (f"memory/segments/{name_or_id}", f"segments/{name_or_id}"):
			r = self.http.patch(ep, json=payload)
			if r.get("success"):
				return True
		return False

	# -------- Analysis helpers --------

	def analysis_run(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		r = self.http.post("analysis", json=options or {})
		return r

	def analysis_callgraph(self, name: Optional[str] = None, address: Optional[str] = None, max_depth: int = 3) -> Dict[str, Any]:
		params: Dict[str, Any] = {"max_depth": max_depth}
		if address:
			params["address"] = address
		if name:
			params["name"] = name
		r = self.http.get("analysis/callgraph", params=params)
		return r

	def analysis_dataflow(self, address: str, direction: str = "forward", max_steps: int = 50) -> Dict[str, Any]:
		params = {"address": address, "direction": direction, "max_steps": max_steps}
		r = self.http.get("analysis/dataflow", params=params)
		return r

