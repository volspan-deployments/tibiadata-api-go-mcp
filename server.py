from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

mcp = FastMCP("TibiaData API")

BASE_URL = "https://api.tibiadata.com/v4"


@mcp.tool()
async def get_character(name: str) -> dict:
    """Retrieve detailed information about a specific Tibia character, including their level, vocation, guild, achievements, and other profile data. Use this when the user asks about a Tibia player or character."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/character/{name}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_guild(name: str) -> dict:
    """Retrieve information about a specific Tibia guild, including its members, description, founding date, and war history. Use this when the user asks about a Tibia guild."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/guild/{name}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_world(name: str) -> dict:
    """Retrieve information about a specific Tibia game world/server, including online players, location, PvP type, and status. Use this when the user asks about a specific Tibia server or world."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/world/{name}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def list_worlds() -> dict:
    """Retrieve a list of all Tibia game worlds/servers with their basic status information. Use this when the user wants to see all available Tibia servers or compare worlds."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/worlds")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_highscores(
    world: str,
    category: str,
    vocation: Optional[str] = "all",
    page: Optional[int] = 1
) -> dict:
    """Retrieve the highscore rankings for a specific Tibia world and category (e.g., experience, magic level, fishing). Use this when the user wants to see top-ranked players on a world or in a skill."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BASE_URL}/highscores/{world}/{category}/{vocation}/{page}"
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_creature(race: str) -> dict:
    """Retrieve detailed information about a specific Tibia creature/monster, including its loot, hit points, experience, and other stats. Use this when the user asks about a Tibia monster or creature."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/creature/{race}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_spells(vocation: Optional[str] = "all") -> dict:
    """Retrieve information about Tibia spells, optionally filtered by vocation. Use this when the user asks about Tibia spells or magic abilities available to characters."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        if vocation and vocation != "all":
            url = f"{BASE_URL}/spells/{vocation}"
        else:
            url = f"{BASE_URL}/spells"
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_api_info() -> dict:
    """Retrieve metadata and health information about the TibiaData API itself, including version, build details, and readiness status. Use this to check if the API is operational or to get version information."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        info_response = await client.get(f"{BASE_URL}/info")
        info_response.raise_for_status()
        info_data = info_response.json()

        try:
            health_response = await client.get("https://api.tibiadata.com/healthz")
            health_data = {"healthz": health_response.text, "healthz_status": health_response.status_code}
        except Exception as e:
            health_data = {"healthz_error": str(e)}

        return {**info_data, **health_data}




async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)

class _FixAcceptHeader:
    """Ensure Accept header includes both types FastMCP requires."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()
            if "text/event-stream" not in accept:
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope, headers=new_headers)
        await self.app(scope, receive, send)

app = _FixAcceptHeader(Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
