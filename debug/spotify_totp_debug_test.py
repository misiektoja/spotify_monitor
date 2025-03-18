import asyncio
import logging
from random import randrange
import time

import pyotp
from aiohttp import ClientSession, ClientError

_LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://open.spotify.com/get_access_token"


def get_random_user_agent():
    return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{randrange(11, 15)}_{randrange(4, 9)}) AppleWebKit/{randrange(530, 537)}.{randrange(30, 37)} (KHTML, like Gecko) Chrome/{randrange(80, 105)}.0.{randrange(3000, 4500)}.{randrange(60, 125)} Safari/{randrange(530, 537)}.{randrange(30, 36)}"


def base32_from_bytes(e: bytes, secret_sauce: str) -> str:
    t = 0
    n = 0
    r = ""
    for byte in e:
        n = (n << 8) | byte
        t += 8
        while t >= 5:
            index = (n >> (t - 5)) & 31
            r += secret_sauce[index]
            t -= 5
    if t > 0:
        r += secret_sauce[(n << (5 - t)) & 31]
    return r


def clean_buffer(e: str) -> bytes:
    e = e.replace(" ", "")
    return bytes(int(e[i:i+2], 16) for i in range(0, len(e), 2))


async def generate_totp(session: ClientSession) -> tuple[pyotp.TOTP, int, str]:
    _LOGGER.debug("Generating TOTP")
    secret_cipher_bytes = [
        12, 56, 76, 33, 88, 44, 88, 33,
        78, 78, 11, 66, 22, 22, 55, 69, 54,
    ]
    transformed = [e ^ ((t % 33) + 9) for t, e in enumerate(secret_cipher_bytes)]
    joined = "".join(str(num) for num in transformed)
    utf8_bytes = joined.encode("utf-8")
    hex_str = "".join(format(b, 'x') for b in utf8_bytes)
    secret_bytes = clean_buffer(hex_str)
    secret_sauce = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    secret = base32_from_bytes(secret_bytes, secret_sauce)
    _LOGGER.debug("Computed secret: %s", secret)

    headers = {
        "Host": "open.spotify.com",
        "User-Agent": get_random_user_agent(),
        "Accept": "*/*",
    }
    async with session.get("https://open.spotify.com/server-time", headers=headers) as resp:
        resp.raise_for_status()
        json_data = await resp.json()
        server_time = json_data.get("serverTime")
        if server_time is None:
            raise Exception("Failed to get server time")
    return pyotp.TOTP(secret, digits=6, interval=30), server_time, secret


async def async_refresh_token(cookies: dict):
    async with ClientSession(cookies=cookies) as session:
        totp_obj, server_time, _ = await generate_totp(session)
        _LOGGER.debug("Got TOTP object: %s", totp_obj)
        timestamp = int(time.time())
        otp_value = totp_obj.at(server_time)
        _LOGGER.debug("Using OTP value: %s", otp_value)
        sp_dc = cookies.get("sp_dc", "")
        params = {
            "reason": "transport",
            "productType": "web_player",
            "totp": otp_value,
            "totpVer": 5,
            "ts": timestamp,
        }
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "*/*",
            "Cookie": f"sp_dc={sp_dc}" if sp_dc else "",
        }
        try:
            async with session.get(
                TOKEN_URL,
                params=params,
                allow_redirects=False,
                headers=headers,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("Got response: %s", data)
        except ClientError as ex:
            _LOGGER.exception("Error getting token: %s", ex)
            raise ex

        token = data.get("accessToken", "")

        if len(token) != 374:
            _LOGGER.debug("Transport mode token length (%d) != 374, retrying with mode 'init'", len(token))
            params["reason"] = "init"
            async with session.get(
                TOKEN_URL,
                params=params,
                allow_redirects=False,
                headers=headers,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug("Got response (init mode): %s", data)

        if not data or "accessToken" not in data:
            raise Exception("Unsuccessful token request")

        return {
            "access_token": data["accessToken"],
            "expires_at": data["accessTokenExpirationTimestampMs"],
            "client_id": data.get("clientId", "")
        }


async def check_token_validity(token: str, client_id: str) -> bool:
    url = "https://api.spotify.com/v1/recommendations/available-genre-seeds"
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Id": client_id,
        "User-Agent": get_random_user_agent(),
    }
    async with ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            text = await response.text()
            _LOGGER.debug("Token validity response: status %s, text: %s", response.status, text)
            return response.status == 200


async def main():
    cookies = {
        "sp_dc": "sp_dc_value",
    }

    try:
        token_data = await async_refresh_token(cookies)
        _LOGGER.debug("Got token data: %s", token_data)
        access_token = token_data["access_token"]
        client_id = token_data["client_id"]
        expires_at = token_data["expires_at"]
        print("Access Token:", access_token)
        print("Token Length:", len(access_token))
        print("Expires At (decoded):", time.ctime(expires_at // 1000))
        valid = await check_token_validity(access_token, client_id)
        if valid:
            print("Token is valid.")
        else:
            print("Token is not valid.")
    except Exception as e:
        _LOGGER.error("Failed to refresh token: %s", e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
