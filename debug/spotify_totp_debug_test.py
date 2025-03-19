import asyncio
import logging
import random
from random import randrange
import time
from time import time_ns
import base64
import random
import pyotp
from aiohttp import ClientSession, ClientError, TCPConnector

_LOGGER = logging.getLogger(__name__)

SP_DC = "sp_dc_value"

TOKEN_URL = "https://open.spotify.com/get_access_token"
SERVER_TIME_URL = "https://open.spotify.com/server-time"
USER_AGENT = ""


def get_random_user_agent():
    browser = random.choice(['chrome', 'firefox', 'edge', 'safari'])

    if browser == 'chrome':
        os_choice = random.choice(['mac', 'windows'])
        if os_choice == 'mac':
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(4, 9)}) "
                f"AppleWebKit/{random.randrange(530, 537)}.{random.randrange(30, 37)} (KHTML, like Gecko) "
                f"Chrome/{random.randrange(80, 105)}.0.{random.randrange(3000, 4500)}.{random.randrange(60, 125)} "
                f"Safari/{random.randrange(530, 537)}.{random.randrange(30, 36)}"
            )
        else:
            chrome_version = random.randint(80, 105)
            build = random.randint(3000, 4500)
            patch = random.randint(60, 125)
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.{build}.{patch} Safari/537.36"
            )

    elif browser == 'firefox':
        os_choice = random.choice(['windows', 'mac', 'linux', 'android'])
        version = random.randint(90, 110)
        if os_choice == 'windows':
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        elif os_choice == 'mac':
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        elif os_choice == 'linux':
            return (
                f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )

    elif browser == 'edge':
        os_choice = random.choice(['windows', 'mac'])
        chrome_version = random.randint(80, 105)
        build = random.randint(3000, 4500)
        patch = random.randint(60, 125)
        version_str = f"{chrome_version}.0.{build}.{patch}"
        if os_choice == 'windows':
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{version_str} Safari/537.36 Edg/{version_str}"
            )
        else:
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{random.randint(13, 16)}.0 Safari/605.1.15 Edg/{version_str}"
            )

    elif browser == 'safari':
        os_choice = random.choice(['mac', 'ios'])
        if os_choice == 'mac':
            mac_major = random.randrange(11, 16)
            mac_minor = random.randrange(0, 10)
            webkit_major = random.randint(600, 610)
            webkit_minor = random.randint(1, 20)
            webkit_patch = random.randint(1, 20)
            safari_version = random.randint(13, 16)
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{mac_major}_{mac_minor}) "
                f"AppleWebKit/{webkit_major}.{webkit_minor}.{webkit_patch} (KHTML, like Gecko) "
                f"Version/{safari_version}.0 Safari/{webkit_major}.{webkit_minor}.{webkit_patch}"
            )


def hex_to_bytes(data: str) -> bytes:
    data = data.replace(" ", "")
    return bytes.fromhex(data)


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
    secret_bytes = hex_to_bytes(hex_str)
    secret = base64.b32encode(secret_bytes).decode().rstrip('=')
    _LOGGER.debug("Computed secret: %s", secret)

    headers = {
        "Host": "open.spotify.com",
        "User-Agent": USER_AGENT,
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
    async with ClientSession(cookies=cookies, connector=TCPConnector(ssl=False)) as session:
        totp_obj, server_time, _ = await generate_totp(session)
        _LOGGER.debug("Got TOTP object: %s", totp_obj)
        client_time = int(time_ns() / 1000 / 1000)
        timestamp = int(time.time())
        otp_value = totp_obj.at(server_time)
        _LOGGER.debug("Using OTP value: %s", otp_value)
        sp_dc = cookies.get("sp_dc", "")

        params = {
            "reason": "transport",
            "productType": "web-player",
            "totp": otp_value,
            "totpServer": otp_value,
            "totpVer": 5,
            "sTime": server_time,
            "cTime": client_time,
        }

        headers = {
            "User-Agent": USER_AGENT,
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

        if len(token) != 378:
            _LOGGER.debug("Transport mode token length (%d) != 378, retrying with mode 'init'", len(token))
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
    url = "https://api.spotify.com/v1/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Id": client_id,
        "User-Agent": USER_AGENT,
    }
    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        async with session.get(url, headers=headers) as response:
            text = await response.text()
            _LOGGER.debug("Token validity response: status %s, text: %s", response.status, text)
            return response.status == 200


async def main():
    cookies = {
        "sp_dc": SP_DC
    }

    try:
        USER_AGENT = get_random_user_agent()
        # USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0"
        # USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.3833.78 Safari/537.36 Edg/100.0.3833.78"
        token_data = await async_refresh_token(cookies)
        _LOGGER.debug("Got token data: %s", token_data)
        access_token = token_data["access_token"]
        client_id = token_data["client_id"]
        expires_at = token_data["expires_at"]
        print("Access Token:", access_token)
        print("Token Length:", len(access_token))
        print("Expires At (decoded):", time.ctime(expires_at // 1000))
        print("User agent:", USER_AGENT)
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
