"""Utility registry that maps declarative tool configs to real callables."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path
from typing import Any, Callable, Mapping

from ..schemas import MCPServerConfig, ToolConfig
from .exceptions import MCPConnectionError, ToolRegistryError

try:  # pragma: no cover - optional dependency
    from agno.tools.mcp import MCPTools  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    MCPTools = None  # type: ignore[assignment]

_BUILTIN_TOOLKIT_PATHS: Mapping[str, tuple[str, str]] = {
    "DuckDuckGoTools": ("agno.tools.duckduckgo", "DuckDuckGoTools"),
    "WikipediaTools": ("agno.tools.wikipedia", "WikipediaTools"),
    "GoogleSearchTools": ("agno.tools.google_search", "GoogleSearchTools"),
    "ExaTools": ("agno.tools.exa", "ExaTools"),
    "ArxivTools": ("agno.tools.arxiv", "ArxivTools"),
    "YFinanceTools": ("agno.tools.yfinance", "YFinanceTools"),
    "OpenBBTools": ("agno.tools.openbb", "OpenBBTools"),
    "GmailTools": ("agno.tools.gmail", "GmailTools"),
    "GoogleCalendarTools": ("agno.tools.google_calendar", "GoogleCalendarTools"),
    "SlackTools": ("agno.tools.slack", "SlackTools"),
    "NotionTools": ("agno.tools.notion", "NotionTools"),
    "ShellTools": ("agno.tools.shell", "ShellTools"),
    "PythonTools": ("agno.tools.python", "PythonTools"),
    "FileTools": ("agno.tools.files", "FileTools"),
    "DockerTools": ("agno.tools.docker", "DockerTools"),
    "PostgresTools": ("agno.tools.postgres", "PostgresTools"),
    "SqlTools": ("agno.tools.sql", "SqlTools"),
    "PandasTools": ("agno.tools.pandas", "PandasTools"),
    "DalleTools": ("agno.tools.dalle", "DalleTools"),
    "ElevenLabsTools": ("agno.tools.elevenlabs", "ElevenLabsTools"),
    "YoutubeTools": ("agno.tools.youtube", "YoutubeTools"),
}


def _load_toolkit_class(module_path: str, class_name: str) -> type[Any] | None:
    try:
        module = importlib.import_module(module_path)
    except Exception:  # pragma: no cover - defensive
        return None
    candidate = getattr(module, class_name, None)
    return candidate if isinstance(candidate, type) else None


BUILTIN_TOOLKITS: dict[str, type[Any]] = {
    name: cls
    for name, cls in (
        (alias, _load_toolkit_class(path[0], path[1]))  # type: ignore[index]
        for alias, path in _BUILTIN_TOOLKIT_PATHS.items()
    )
    if cls is not None
}


class ToolRegistry:
    """Resolves tool schemas into live toolkits, MCP connections or functions."""

    BUILTIN_TOOLKITS = BUILTIN_TOOLKITS

    def __init__(self) -> None:
        self._custom_functions: dict[str, Callable[..., Any]] = {}
        self._mcp_connections: dict[str, Any] = {}

    def register_function(self, name: str, func: Callable[..., Any]) -> None:
        """Register a custom function reference by name."""

        if not name:
            raise ValueError("Function name must be provided")
        if not callable(func):
            raise ValueError("Provided object is not callable")
        self._custom_functions[name] = func

    def get_builtin_toolkit(self, name: str, params: Mapping[str, Any] | None = None) -> Any:
        """Instantiate and return one of the builtin Agno toolkits."""

        toolkit_cls = self.BUILTIN_TOOLKITS.get(name)
        if toolkit_cls is None:
            raise ToolRegistryError(f"Toolkit '{name}' is not available")
        kwargs = dict(params or {})
        try:
            return toolkit_cls(**kwargs)
        except Exception as exc:  # pragma: no cover - toolkit specific errors
            raise ToolRegistryError(f"Failed to instantiate toolkit '{name}'") from exc

    async def get_mcp_tools(self, config: MCPServerConfig) -> Any:
        """Return a cached or brand-new MCPTools instance."""

        if MCPTools is None:  # pragma: no cover - optional dependency guard
            raise MCPConnectionError("agno is not installed; MCP tools are unavailable")

        key = self._mcp_cache_key(config)
        cached = self._mcp_connections.get(key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {
            "tool_name_prefix": config.tool_name_prefix,
        }

        if config.env:
            params["env"] = dict(config.env)

        if config.connection_type == "command":
            if not config.command:
                raise MCPConnectionError("command is required for MCP command connections")
            params["command"] = config.command
        elif config.connection_type == "url":
            if not config.url:
                raise MCPConnectionError("url is required for MCP url connections")
            params["url"] = config.url
        else:  # pragma: no cover - schema guarantees Literal
            raise MCPConnectionError(f"Unsupported MCP connection type: {config.connection_type!r}")

        try:
            tools = MCPTools(**params)
        except Exception as exc:  # pragma: no cover - network/exec errors
            raise MCPConnectionError("Unable to establish MCP connection") from exc

        self._mcp_connections[key] = tools
        return tools

    async def resolve_tools(self, tool_configs: list[ToolConfig]) -> list[Any]:
        """Resolve ToolConfig entries to an executable list of tools."""

        resolved: list[Any] = []
        for config in tool_configs or []:
            tool_type = config.type.lower().strip()
            if tool_type == "builtin":
                if not config.toolkit_name:
                    raise ToolRegistryError("toolkit_name is required for builtin tools")
                resolved.append(
                    self.get_builtin_toolkit(config.toolkit_name, config.toolkit_params)
                )
            elif tool_type == "function":
                resolved.append(self._resolve_function(config))
            elif tool_type == "mcp":
                if config.mcp_server is None:
                    raise ToolRegistryError("mcp tool configs require mcp_server definition")
                resolved.append(await self.get_mcp_tools(config.mcp_server))
            else:  # pragma: no cover - schema restricts Literal
                raise ToolRegistryError(f"Unsupported tool type: {config.type}")
        return resolved

    def _resolve_function(self, config: ToolConfig) -> Callable[..., Any]:
        function_name = config.function_name
        if not function_name:
            raise ToolRegistryError("function_name is required for custom tools")

        registered = self._custom_functions.get(function_name)
        if registered is not None:
            return registered

        if config.function_module:
            return self._load_from_module(config.function_module, function_name)
        if config.function_path:
            return self._load_from_path(config.function_path, function_name)

        raise ToolRegistryError(
            "Custom function tools must be registered or define function_module/function_path"
        )

    def _load_from_module(self, module_path: str, attribute: str) -> Callable[..., Any]:
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:  # pragma: no cover - module level errors
            raise ToolRegistryError(f"Failed to import module '{module_path}'") from exc

        candidate = getattr(module, attribute, None)
        if not callable(candidate):
            raise ToolRegistryError(
                f"Attribute '{attribute}' in module '{module_path}' is not callable"
            )
        return candidate

    def _load_from_path(self, file_path: str, attribute: str) -> Callable[..., Any]:
        resolved_path = Path(file_path).expanduser().resolve()
        if not resolved_path.exists():
            raise ToolRegistryError(f"Function path '{resolved_path}' does not exist")

        module_name = self._module_name_for_path(resolved_path)
        spec = importlib.util.spec_from_file_location(module_name, resolved_path)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise ToolRegistryError(f"Unable to load module from '{resolved_path}'")
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        loader.exec_module(module)  # type: ignore[arg-type]

        candidate = getattr(module, attribute, None)
        if not callable(candidate):
            raise ToolRegistryError(f"Attribute '{attribute}' in '{resolved_path}' is not callable")
        return candidate

    def _module_name_for_path(self, path: Path) -> str:
        digest = hashlib.sha1(str(path).encode("utf-8"), usedforsecurity=False).hexdigest()
        return f"dynamic_agents.custom.{digest}"

    def _mcp_cache_key(self, config: MCPServerConfig) -> str:
        env_items = tuple(sorted((config.env or {}).items()))
        return "|".join(
            [
                config.connection_type,
                config.command or "",
                config.url or "",
                config.tool_name_prefix or "",
                str(env_items),
            ]
        )


__all__ = ["ToolRegistry", "BUILTIN_TOOLKITS"]
