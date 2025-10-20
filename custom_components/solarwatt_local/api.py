import asyncio
from aiohttp import ClientSession, ClientResponseError, TCPConnector
from yarl import URL


class SolarwattAPI:
def __init__(self, host: str, password: str, session: ClientSession | None = None):
self.base = URL(f"http://{host}")
self.password = password
# Use connector that allows IPv4/IPv6 etc.
self._session = session or ClientSession(connector=TCPConnector(ssl=False))
self._logged_in = False


async def login(self) -> int:
login_url = self.base.with_path("/auth/login")
data = {"username": "installer", "password": self.password, "url": "/"}
async with self._session.post(str(login_url), data=data, allow_redirects=True) as resp:
if resp.status not in (200, 302, 303):
raise ClientResponseError(resp.request_info, resp.history, status=resp.status)
# cookie should now be stored in the session's cookie_jar
self._logged_in = True
return resp.status


async def get_items(self):
if not self._logged_in:
await self.login()
items_url = self.base.with_path("/rest/items")
async with self._session.get(str(items_url)) as resp:
resp.raise_for_status()
text = await resp.text()
# Some setups return JSON content-type; try json() first
try:
return await resp.json()
except Exception:
# fallback: attempt to parse text as json
import json
return json.loads(text)


async def get_item(self, item_name: str):
if not self._logged_in:
await self.login()
url = self.base.with_path(f"/rest/items/{item_name}")
async with self._session.get(str(url)) as resp:
resp.raise_for_status()
return await resp.json()


async def close(self):
await self._session.close()
