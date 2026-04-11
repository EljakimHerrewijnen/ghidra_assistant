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
import re
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urljoin, quote

try:
	import requests  # type: ignore
except Exception:  # pragma: no cover
	requests = None  # type: ignore

from .ghidra_backend import GhidraBackend, GhidraFunction, GhidraFunctionBasic, GhidraFunctionArgument, Mem

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
	v = os.environ.get(name)
	return v if v not in (None, "") else default


_HEX_ADDRESS_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]+$")
_ADDRESS_KEY_SET = {
	"address",
	"addresses",
	"addr",
	"entry",
	"entrypoint",
	"entry_address",
	"from_addr",
	"to_addr",
	"call_site",
	"root_address",
	"imagebase",
	"start",
	"end",
	"start_address",
	"end_address",
	"stop",
}


def _is_address_key(key: str) -> bool:
	k = key.lower()
	return k in _ADDRESS_KEY_SET or k.endswith("_address") or k.endswith("_addr")


def _sanitize_address_value(value: str) -> str:
	if not isinstance(value, str) or ":" not in value:
		return value
	# Keep behavior simple and fast: only strip prefixes from namespace-like address
	# strings such as "ram:000c2404" or "stack:0x401000".
	candidate = value.rsplit(":", 1)[-1].strip()
	if _HEX_ADDRESS_RE.fullmatch(candidate):
		return candidate
	return value


def _sanitize_addresses_in_payload(payload: Any, parent_key: Optional[str] = None) -> Any:
	if isinstance(payload, dict):
		for k, v in payload.items():
			if isinstance(v, str) and _is_address_key(str(k)):
				payload[k] = _sanitize_address_value(v)
			else:
				payload[k] = _sanitize_addresses_in_payload(v, parent_key=str(k))
		return payload

	if isinstance(payload, list):
		for idx, item in enumerate(payload):
			payload[idx] = _sanitize_addresses_in_payload(item, parent_key=parent_key)
		return payload

	if isinstance(payload, str) and parent_key and _is_address_key(parent_key):
		return _sanitize_address_value(payload)

	return payload


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
		_sanitize_addresses_in_payload(data)
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
	def __init__(self, host: Optional[str] = None, port: Optional[int] = None,
				 project_name: Optional[str] = None, file_name: Optional[str] = None) -> None:
		"""Hydra backend with instance auto-selection.

		Selection logic:
		1. Query /instances on the initial host:port (defaults from env if not supplied).
		2. If project_name and/or file_name are provided, filter instances matching those fields.
		3. If exactly one instance remains, connect to its url (host:that_port).
		4. If no filters provided and exactly one instance exists, use it.
		5. Otherwise raise a ValueError requiring disambiguation.

		Args:
			host: Controller host exposing /instances (default env GHIDRA_HYDRA_HOST or 127.0.0.1)
			port: Controller port (default env GHIDRA_HYDRA_PORT or 8192)
			project_name: Optional project name to select instance
			file_name: Optional loaded file/program name to select instance
		"""
		super().__init__()
		root_host = host or _env("GHIDRA_HYDRA_HOST", "127.0.0.1")
		root_port = port or int(_env("GHIDRA_HYDRA_PORT", "8192"))
		self.controller_base = f"http://{root_host}:{root_port}/"
		self.http = _HydraClient(self.controller_base)
		self.current_instance_info: Optional[Dict[str, Any]] = None

		instances = self._fetch_instances()
		if not instances:
			raise ValueError("No Hydra instances available (GET /instances failed or returned empty). Launch a Ghidra session and enable ghydraMCP in configure inside the tool!")
		chosen = self._select_instance(instances, project_name, file_name)
		if chosen is None:
			raise ValueError(self._build_instance_error(instances, project_name, file_name))

		# Re-point client to chosen instance if different port
		inst_url = chosen.get("url") or chosen.get("instance") or chosen.get("_url")
		if not inst_url:
			# Compose from port if missing url
			inst_port = chosen.get("port")
			if inst_port is None:
				raise ValueError("Chosen instance missing 'url' and 'port' fields")
			inst_url = f"http://{root_host}:{inst_port}"
		if not inst_url.endswith('/'):
			inst_url += '/'
		self.base_url = inst_url
		self.http = _HydraClient(self.base_url)
		self.current_instance_info = chosen

		# Provide Mem-compatible callable for reads after final base_url chosen
		def _read_memory(addr: int | str, size: int) -> bytes:
			if isinstance(addr, int):
				address = hex(addr)
			else:
				address = addr
			params = {"address": address, "length": size, "format": "hex"}
			r = self.http.get("memory", params=params)
			if not _result_ok(r):
				logger.debug("memory read failed: %s", r)
				return b""
			res = r["result"]
			hex_bytes: str | None = res.get("hexBytes") if isinstance(res, dict) else None
			if hex_bytes:
				try:
					hb = hex_bytes.replace("0x", "").replace(" ", "")
					return bytes.fromhex(hb)
				except ValueError:
					pass
			if isinstance(res, list) and all(isinstance(x, str) for x in res):
				try:
					return bytes(int(x, 16) for x in res if x.startswith("0x"))
				except Exception:
					return b""
			return b""

		self.mem = Mem(_read_memory)

	def _fetch_instances(self) -> List[Dict[str, Any]]:
		"""Retrieve available instances from controller.

		Returns empty list if endpoint not available or failure.
		"""
		resp = self.http.get("instances")
		if _result_ok(resp) and isinstance(resp.get("result"), list):
			return resp["result"]
		return []

	def _select_instance(self, instances: List[Dict[str, Any]], project_name: Optional[str], file_name: Optional[str]) -> Optional[Dict[str, Any]]:
		if not instances:
			return None
		candidates = instances
		if project_name:
			candidates = [i for i in candidates if str(i.get("project")) == project_name]
		if file_name:
			candidates = [i for i in candidates if str(i.get("file")) == file_name]
		# If filters applied and one candidate -> pick it
		if candidates and (project_name or file_name):
			if len(candidates) == 1:
				return candidates[0]
			return None  # ambiguous
		# No filters: only auto-pick if exactly one instance total
		if not project_name and not file_name and len(instances) == 1:
			return instances[0]
		return None

	def _build_instance_error(self, instances: List[Dict[str, Any]], project_name: Optional[str], file_name: Optional[str]) -> str:
		if not instances:
			return "No Hydra instances available (GET /instances returned empty). Launch a Ghidra session."
		lines = ["Unable to select a unique Hydra instance."]
		if project_name or file_name:
			lines.append(f"Filters project={project_name!r} file={file_name!r} yielded multiple or zero matches.")
		else:
			lines.append("Multiple instances present; specify project_name and/or file_name.")
		lines.append("Available instances:")
		for inst in instances:
			lines.append(f"  - project={inst.get('project')} file={inst.get('file')} port={inst.get('port')} type={inst.get('type')}")
		return "\n".join(lines)

	def list_instances(self) -> List[Dict[str, Any]]:
		"""Public helper to list controller instances (same as initial query)."""
		return self._fetch_instances()

	@property
	def selected_instance(self) -> Optional[Dict[str, Any]]:
		"""Return the metadata dict for the chosen instance."""
		return self.current_instance_info

	# -------- meta + context endpoints --------

	def get_plugin_version_info(self) -> Optional[Dict[str, Any]]:
		"""Return plugin/api version metadata (GET /plugin-version)."""
		r = self.http.get("plugin-version")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def get_instance_info(self) -> Optional[Dict[str, Any]]:
		"""Return detailed info about the current plugin instance (GET /info)."""
		r = self.http.get("info")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def get_project_info(self) -> Optional[Dict[str, Any]]:
		"""Return information about the current Ghidra project (GET /project)."""
		r = self.http.get("project")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def get_program_info(self) -> Optional[Dict[str, Any]]:
		"""Return metadata for the active program/binary (GET /program)."""
		r = self.http.get("program")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

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
		items = self._list_functions(offset=0, limit=100_000)
		for item in items:
			if not isinstance(item, dict):
				continue
			name = _get_first(item, "name", "function_name", default="<unnamed>")
			if "ram_" in name: # Hack to remove verbose "ram_" prefix from function names
				name = name.replace("ram_", "")
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
			if isinstance(address, str):
				address = _sanitize_address_value(address)
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

		dec_r = self.http.get(f"functions/{address}/decompile", params={"syntax_tree": "false", "style": "normalize"})
		decompiled_code = None
		if _result_ok(dec_r) and isinstance(dec_r["result"], dict):
			decompiled_code = _get_first(dec_r["result"], "decompiled", "ccode", "decompiled_text", default="") or None

		# Bytes: try to derive size from disassembly span; otherwise default
		raw_bytes = self.mem[int(address, 16): int(address, 16) + 0x100]  # up to 256 bytes
		size = len(raw_bytes)

		# Arguments
		vars_r = self.http.get(f"functions/{address}/variables")
		vars: List[GhidraFunctionArgument] = []
		if _result_ok(vars_r) and isinstance(vars_r["result"], dict):
			for v in vars_r["result"].get("variables", []) or []:
				if isinstance(v, dict):
					if v.get("isParameter") is True:
						var_name = str(v.get("name", ""))
						var_type = str(v.get("type", ""))
						var_storage = str(v.get("storage", ""))
						vars.append(GhidraFunctionArgument(var_name, var_type, var_storage))

		# Xrefs in/out
		incoming = self.get_xrefs_to(address)
		outgoing = self.get_xrefs_from(address)

		return GhidraFunction(
			address,
			basicFunction.name,
			vars,
			None,
			raw_bytes,
			size,
			disassembly,
			decompiled_code=decompiled_code,
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

	def write_mem(self, address: int | str, data: bytes, force=True) -> bool:
		'''
		Write memory to the specified address. Max block size to write is 0x80 bytes. Chunk if needed. Return True on success, else False.
		'''
		if len(data) > 0x80:
			chunk_size = 0x80
			for i in range(0, len(data), chunk_size):
				chunk = data[i:i + chunk_size]
				addr = address + i if isinstance(address, int) else f"{address}+{i}"
				if not self.write_mem(addr, chunk):
					return False
			return True
		# Single chunk write
		addr = hex(address) if isinstance(address, int) else address
		hexstr = data.hex()
		# curl -X PATCH 'http://localhost:8192/memory?address=0xCE00BC82' \
		# -H 'Content-Type: application/json' \
		# -d '{"format":"hex","bytes":"90 90 90 90","force":true}'
		r = self.http.patch(f"memory?address={addr}", json={"bytes": hexstr, "format": "hex", "force": str(force)})
		if not r['success']:
			logger.error(r['error'])
			return False
		return True

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

	def _normalize_hex_address(self, address: str) -> str:
		addr = _sanitize_address_value(address).lower().strip()
		if addr.startswith("0x"):
			addr = addr[2:]
		if len(addr) % 2 == 1:
			addr = "0" + addr
		return addr

	def xrefs_query(self, *, to_addr: Optional[str] = None, from_addr: Optional[str] = None,
					 ref_type: Optional[str] = None, offset: int = 0, limit: int = 100) -> Dict[str, Any]:
		if not to_addr and not from_addr:
			raise ValueError("xrefs_query requires at least one of to_addr/from_addr")
		params: Dict[str, Any] = {"offset": offset, "limit": limit}
		if to_addr:
			params["to_addr"] = self._normalize_hex_address(to_addr)
		if from_addr:
			params["from_addr"] = self._normalize_hex_address(from_addr)
		if ref_type:
			params["type"] = ref_type
		result: Dict[str, Any] = {"references": [], "offset": offset, "limit": limit, "size": None}
		r = self.http.get("xrefs", params=params)
		if _result_ok(r) and isinstance(r["result"], dict):
			payload = r["result"]
			references = payload.get("references") or payload.get("result") or []
			if isinstance(references, list):
				result["references"] = references
			for key in ("size", "offset", "limit"):
				if key in payload:
					result[key] = payload[key]
		return result

	def get_xrefs_to(self, address: str, offset: int = 0, limit: int = 100,
					 ref_type: Optional[str] = None, include_metadata: bool = False) -> Any:
		res = self.xrefs_query(to_addr=address, offset=offset, limit=limit, ref_type=ref_type)
		return res if include_metadata else res["references"]

	def get_xrefs_from(self, address: str, offset: int = 0, limit: int = 100,
					 ref_type: Optional[str] = None, include_metadata: bool = False) -> Any:
		res = self.xrefs_query(from_addr=address, offset=offset, limit=limit, ref_type=ref_type)
		return res if include_metadata else res["references"]

	def get_function_xrefs(self, address: str, *, direction: str = "both",
						 offset: int = 0, limit: int = 100) -> Dict[str, Any]:
		params: Dict[str, Any] = {"offset": offset, "limit": limit, "direction": direction}
		r = self.http.get(f"functions/{address}/xrefs", params=params)
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return {"incoming": [], "outgoing": [], "offset": offset, "limit": limit}

	# /functions/{address} endpoint
	def get_function_at(self, address: int | str) -> GhidraFunctionBasic | None:
		"""Return the function starting at or containing the given address.

		Tries both path and query forms:
		- GET /functions/at/{addr}
		- GET /functions/at?address={addr}

		Returns the function info dict on success, else None.
		"""
		addr = hex(address) if isinstance(address, int) else str(address)
		# Prefer path variant
		r = self.http.get(f"functions/at/{addr}")
		if _result_ok(r) and isinstance(r["result"], dict):
			if not isinstance(r["result"].get("address"), str):
				r["result"]["address"] = hex(r["result"]["address"])

			r["result"]["address"] = _sanitize_address_value(r["result"]["address"])

			return GhidraFunctionBasic(
				address=r["result"]["address"],
				name=r["result"]["name"],
				args=r['result']['parameters'],
				return_type=r['result']['returnType'],
			)
		return None

	def get_function_info(self, address: str) -> Optional[Dict[str, Any]]:
		r = self.http.get(f"functions/{address}")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def list_strings(self, offset: int = 0, limit: int = 2000, filter: Optional[str] = None,
					 name_contains: Optional[str] = None) -> List[Dict[str, Any]]:
		params: Dict[str, Any] = {"offset": offset, "limit": limit}
		if filter:
			params["filter"] = filter
		if name_contains:
			params["name_contains"] = name_contains
		r = self.http.get("strings", params=params)
		if _result_ok(r) and isinstance(r["result"], list):
			return r["result"]
		return []

	# -------- Symbols API --------

	def symbols_list(self, offset: int = 0, limit: int = 200, *, addr: Optional[str] = None,
					 symbol_type: Optional[str] = None, name: Optional[str] = None,
					 name_contains: Optional[str] = None, name_regex: Optional[str] = None) -> List[Dict[str, Any]]:
		params: Dict[str, Any] = {"offset": offset, "limit": limit}
		if addr:
			params["addr"] = addr
		if symbol_type:
			params["type"] = symbol_type
		if name:
			params["name"] = name
		if name_contains:
			params["name_contains"] = name_contains
		if name_regex:
			params["name_matches_regex"] = name_regex
		r = self.http.get("symbols", params=params)
		if _result_ok(r) and isinstance(r["result"], list):
			return r["result"]
		return []

	def symbols_get(self, address: str) -> Optional[Dict[str, Any]]:
		r = self.http.get(f"symbols/{address}")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def symbols_create(self, address: str, name: str, *, symbol_type: Optional[str] = None,
					  namespace: Optional[str] = None, primary: Optional[bool] = None) -> bool:
		payload: Dict[str, Any] = {"address": address, "name": name}
		if symbol_type:
			payload["type"] = symbol_type
		if namespace:
			payload["namespace"] = namespace
		if primary is not None:
			payload["primary"] = primary
		r = self.http.post("symbols", json=payload)
		return bool(r.get("success"))

	def symbols_update(self, address: str, *, name: Optional[str] = None,
					  namespace: Optional[str] = None, symbol_type: Optional[str] = None,
					  primary: Optional[bool] = None) -> bool:
		payload: Dict[str, Any] = {}
		if name is not None:
			payload["name"] = name
		if namespace is not None:
			payload["namespace"] = namespace
		if symbol_type is not None:
			payload["type"] = symbol_type
		if primary is not None:
			payload["primary"] = primary
		if not payload:
			return True
		r = self.http.patch(f"symbols/{address}", json=payload)
		return bool(r.get("success"))

	def symbols_delete(self, address: str) -> bool:
		r = self.http.delete(f"symbols/{address}")
		return bool(r.get("success"))

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

	def data_get(self, address: str) -> Optional[Dict[str, Any]]:
		r = self.http.get(f"data/{address}")
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def data_create(self, address: str, data_type: str, size: Optional[int] = None) -> bool:
		payload: Dict[str, Any] = {"address": address, "type": data_type}
		if size is not None:
			payload["size"] = size
		r = self.http.post("data", json=payload)
		return bool(r.get("success"))

	def data_rename(self, address: str, new_name: str) -> bool:
		return self.data_update(address, name=new_name)

	def data_delete(self, address: str) -> bool:
		r = self.http.delete(f"data/{address}")
		if r.get("success"):
			return True
		# Fallback for older plugins
		r2 = self.http.post("data/delete", json={"address": address, "action": "delete"})
		return bool(r2.get("success"))

	def data_set_type(self, address: str, data_type: str) -> bool:
		return self.data_update(address, data_type=data_type)

	def data_update(self, address: str, *, name: Optional[str] = None,
				  data_type: Optional[str] = None, comment: Optional[str] = None,
				  size: Optional[int] = None) -> bool:
		payload: Dict[str, Any] = {}
		if name is not None:
			payload["name"] = name
		if data_type is not None:
			payload["type"] = data_type
		if comment is not None:
			payload["comment"] = comment
		if size is not None:
			payload["size"] = size
		if not payload:
			return True
		r = self.http.patch(f"data/{address}", json=payload)
		return bool(r.get("success"))

	# -------- Structs API --------

	def structs_list(self, offset: int = 0, limit: int = 100, category: Optional[str] = None,
					 name_contains: Optional[str] = None) -> List[Dict[str, Any]]:
		"""List struct definitions with optional pagination/filtering."""
		params: Dict[str, Any] = {"offset": offset, "limit": limit}
		if category:
			params["category"] = category
		if name_contains:
			params["name_contains"] = name_contains
		r = self.http.get("structs", params=params)
		if _result_ok(r) and isinstance(r["result"], list):
			return r["result"]
		return []

	def structs_get(self, name: str) -> Optional[Dict[str, Any]]:
		"""Retrieve a single struct definition including fields."""
		r = self.http.get("structs", params={"name": name})
		if _result_ok(r) and isinstance(r["result"], dict):
			return r["result"]
		return None

	def structs_create(self, name: str, *, category: Optional[str] = None,
					  description: Optional[str] = None) -> bool:
		payload: Dict[str, Any] = {"name": name}
		if category:
			payload["category"] = category
		if description:
			payload["description"] = description
		r = self.http.post("structs/create", json=payload)
		return bool(r.get("success"))

	def structs_add_field(self, struct_name: str, field_name: str, field_type: str,
						   *, offset: Optional[int] = None, comment: Optional[str] = None) -> bool:
		payload: Dict[str, Any] = {
			"struct": struct_name,
			"fieldName": field_name,
			"fieldType": field_type,
		}
		if offset is not None:
			payload["offset"] = offset
		if comment:
			payload["comment"] = comment
		r = self.http.post("structs/addfield", json=payload)
		return bool(r.get("success"))

	def structs_update_field(self, struct_name: str, *, field_name: Optional[str] = None,
							  field_offset: Optional[int] = None,
							  new_name: Optional[str] = None,
							  new_type: Optional[str] = None,
							  new_comment: Optional[str] = None) -> bool:
		if field_name is None and field_offset is None:
			raise ValueError("Must provide field_name or field_offset to identify struct field")
		if not any([new_name, new_type, new_comment]):
			raise ValueError("Must supply at least one of new_name/new_type/new_comment")
		payload: Dict[str, Any] = {"struct": struct_name}
		if field_name is not None:
			payload["fieldName"] = field_name
		if field_offset is not None:
			payload["fieldOffset"] = field_offset
		if new_name is not None:
			payload["newName"] = new_name
		if new_type is not None:
			payload["newType"] = new_type
		if new_comment is not None:
			payload["newComment"] = new_comment
		r = self.http.post("structs/updatefield", json=payload)
		return bool(r.get("success"))

	def structs_delete(self, name: str) -> bool:
		r = self.http.post("structs/delete", json={"name": name})
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
	def _normalize_background_color(self, color: str) -> str:
		"""Normalize accepted color names for the Hydra API."""
		prefix = "java.awt.Color."
		if isinstance(color, str) and color.startswith(prefix):
			# API supports constants and fully-qualified constants.
			# Convert to constant for consistency.
			return color[len(prefix):]
		return color

	def set_background_colors(self, addresses: Sequence[int | str], color: str = "java.awt.Color.YELLOW") -> None:
		"""Set the same background color for multiple addresses.

		Uses:
		- POST /memory/background-colors
		- PATCH /memory/background-colors (fallback)
		- Per-address fallback for older plugin variants
		"""
		if not addresses:
			return

		color_value = self._normalize_background_color(color)
		normalized_addresses: List[str] = []
		for a in addresses:
			if isinstance(a, int):
				normalized_addresses.append(hex(a))
			else:
				normalized_addresses.append(str(a))

		payload = {"addresses": normalized_addresses, "color": color_value}
		r = self.http.post("memory/background-colors", json=payload)
		if r.get("success"):
			return

		r2 = self.http.patch("memory/background-colors", json=payload)
		if r2.get("success"):
			return

		# Backward-compatible fallback: set one-by-one.
		failed = 0
		for addr in normalized_addresses:
			r3 = self.http.post(f"memory/{addr}/background-color", json={"color": color_value})
			if r3.get("success"):
				continue
			r4 = self.http.patch(f"memory/{addr}/background-color", json={"color": color_value})
			if not r4.get("success"):
				failed += 1
		if failed:
			logger.warning("set_background_colors failed for %d/%d addresses", failed, len(normalized_addresses))

	def set_background_color(self, addresses: List[int], color: str = "java.awt.Color.YELLOW") -> None:
		"""Backward-compatible alias for bulk background coloring."""
		self.set_background_colors(addresses, color=color)

	def clear_background_color(self) -> None:
		"""Clear all background colors in the current program."""
		r = self.http.delete("memory/background-colors")
		if not r.get("success"):
			logger.warning("clear_background_color failed: %s", r.get("error", "unknown error"))

	def get_ghidra_memory_maps(self) -> List[Any]:
		# Try via documented segments endpoint if available
		segs = self.memory_list_segments()
		if segs:
			return segs
		logger.info("get_ghidra_memory_maps not available via HATEOAS API; returning empty list")
		return []

	def mmap_region(self, addr: int, name: str, size: int, read: bool = True, write: bool = True, execute: bool = False) -> None:
		self.memory_create_segment(name, addr, size, read=read, write=write, execute=execute)

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

