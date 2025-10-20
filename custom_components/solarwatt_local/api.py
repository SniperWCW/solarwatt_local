import logging
from aiohttp import ClientSession, CookieJar

_LOGGER = logging.getLogger(__name__)

class SolarwattAPI:
    def __init__(self, host: str, password: str):
        self.host = host
        self.password = password
        self._session = ClientSession(cookie_jar=CookieJar(unsafe=True))
        self._logged_in = False

    async def login(self):
        login_url = f"http://{self.host}/auth/login"
        data = {"username": "installer", "password": self.password, "url": "/"}
        async with self._session.post(login_url, data=data) as resp:
            text = await resp.text()
            if resp.status != 200 or "logon" in text.lower():
                raise Exception(f"Login fehlgeschlagen, Status: {resp.status}")
            self._logged_in = True
            _LOGGER.info("Login erfolgreich bei Solarwatt Gateway %s", self.host)

    async def get_items(self):
        if not self._logged_in:
            await self.login()
        url = f"http://{self.host}/rest/items"
        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Fehler beim Abrufen von Items: HTTP {resp.status}")
            try:
                return await resp.json()
            except Exception:
                text = await resp.text()
                _LOGGER.error("Antwort ist kein JSON, Text: %s", text[:200])
                raise

    async def close(self):
        await self._session.close()
