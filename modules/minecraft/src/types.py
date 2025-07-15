from typing import TypedDict


class MojangApiResponse(TypedDict):
    id: str
    name: str


class _MinetoolsApiErrorResponse(TypedDict):
    error: str

class _MinetoolsApiResponePlayer(TypedDict):
    id: str
    name: str

class _MinetoolsApiResponePlayers(TypedDict):
    max: int
    online: int
    sample: list[_MinetoolsApiResponePlayer]

class _MinetoolsApiResponeVersion(TypedDict):
    name: str
    protocol: int

class _MinetoolsApiResponse(TypedDict):
    description: str
    favicon: str | None
    latency: float
    players: _MinetoolsApiResponePlayers
    version: _MinetoolsApiResponeVersion

MinetoolsApiResponse = _MinetoolsApiResponse | _MinetoolsApiErrorResponse

class _McSrvStatDebugResponse(TypedDict):
    ping: bool
    query: bool
    bedrock: bool
    srv: bool

class _McSrvStatPlayersResponse(TypedDict):
    online: int
    max: int
    list: list[str] | None
    uuid: dict[str, str]

class _McSrvStatMotdResponse(TypedDict):
    raw: list[str]
    clean: list[str]
    html: list[str]

class McSrvStatResponse(TypedDict):
    ip: str
    port: int
    debug: _McSrvStatDebugResponse
    motd: _McSrvStatMotdResponse
    players: _McSrvStatPlayersResponse
    version: str
    software: str | None
    icon: str | None
