#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.3

Debug code to test the fetching of Spotify access token based on provided SP_DC_COOKIE value
https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_totp_test.py

Python pip3 requirements:

requests
python-dateutil
pyotp

---------------

Change log:

v1.3 (06 Jul 25):
- updated list of secret cipher bytes for v9 and v10 and switched to use version 10

v1.2 (01 Jul 25):
- updated list of secret cipher bytes and switched to use version 8

v1.1 (10 Jun 25):
- Switched server-time call to use HTTP Date header for edge time
- Switched to /api/token endpoint for web-player access token retrieval

v1.0 (19 Mar 25):
- Added support for TOTP parameters in Spotify Web Player token endpoint
"""


import argparse
import base64
import logging
import secrets
import time
from time import time_ns
from datetime import datetime
import random
from email.utils import parsedate_to_datetime
import pyotp
import requests
import json
from dateutil import tz

# Define below or via --sp-dc flag
SP_DC_COOKIE = ""

TOKEN_URL = "https://open.spotify.com/api/token"
SERVER_TIME_URL = "https://open.spotify.com/"
USER_AGENT = ""
TOTP_VER = 10

_LOGGER = logging.getLogger(__name__)


def get_random_user_agent() -> str:
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
        os_choice = random.choice(['windows', 'mac', 'linux'])
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
        else:
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
        os_choice = 'mac'
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
        else:
            return ""
    else:
        return ""


def fetch_server_time(ua: str) -> int:

    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
    }

    _LOGGER.debug("Fetching server time from %s", SERVER_TIME_URL)
    response = requests.head(SERVER_TIME_URL, headers=headers, timeout=5)
    response.raise_for_status()
    date_hdr = response.headers.get("Date")
    if not date_hdr:
        raise RuntimeError("Missing 'Date' header")
    _LOGGER.debug("Server time header: %s", date_hdr)
    return int(parsedate_to_datetime(date_hdr).timestamp())


# TOTP_VER = 10


def generate_totp():
    _LOGGER.debug("Generating TOTP")

    secret_cipher_dict = {
        "10": [61, 110, 58, 98, 35, 79, 117, 69, 102, 72, 92, 102, 69, 93, 41, 101, 42, 75],
        "9": [109, 101, 90, 99, 66, 92, 116, 108, 85, 70, 86, 49, 68, 54, 87, 50, 72, 121, 52, 64, 57, 43, 36, 81, 97, 72, 53, 41, 78, 56],
        "8": [37, 84, 32, 76, 87, 90, 87, 47, 13, 75, 48, 54, 44, 28, 19, 21, 22],
        "7": [59, 91, 66, 74, 30, 66, 74, 38, 46, 50, 72, 61, 44, 71, 86, 39, 89],
        "6": [21, 24, 85, 46, 48, 35, 33, 8, 11, 63, 76, 12, 55, 77, 14, 7, 54],
        "5": [12, 56, 76, 33, 88, 44, 88, 33, 78, 78, 11, 66, 22, 22, 55, 69, 54],
    }
    secret_cipher_bytes = secret_cipher_dict[str(TOTP_VER)]

    transformed = [e ^ ((t % 33) + 9) for t, e in enumerate(secret_cipher_bytes)]
    joined = "".join(str(num) for num in transformed)
    hex_str = joined.encode().hex()
    secret = base64.b32encode(bytes.fromhex(hex_str)).decode().rstrip("=")

    _LOGGER.debug("Computed secret: %s", secret)
    return pyotp.TOTP(secret, digits=6, interval=30)


def refresh_access_token_from_sp_dc(sp_dc: str) -> dict:
    transport = True
    init = True
    session = requests.Session()
    data: dict = {}
    token = ""

    ua = USER_AGENT or get_random_user_agent()
    server_time = fetch_server_time(ua)
    totp_obj = generate_totp()
    client_time = int(time_ns() / 1000 / 1000)
    otp_value = totp_obj.at(server_time)
    _LOGGER.debug("Using OTP: %s", otp_value)
    _LOGGER.debug("TOTP ver: %s", TOTP_VER)

    params = {
        "reason": "transport",
        "productType": "web-player",
        "totp": otp_value,
        "totpServer": otp_value,
        "totpVer": TOTP_VER,
    }

    if TOTP_VER < 10:
        params.update({
            "sTime": server_time,
            "cTime": client_time,
            "buildDate": time.strftime("%Y-%m-%d", time.gmtime(server_time)),
            "buildVer": f"web-player_{time.strftime('%Y-%m-%d', time.gmtime(server_time))}_{server_time * 1000}_{secrets.token_hex(4)}",
        })

    headers = {
        "User-Agent": ua,
        "Accept": "application/json",
        "Referer": "https://open.spotify.com/",
        "App-Platform": "WebPlayer",
        "Cookie": f"sp_dc={sp_dc}",
    }

    last_err = ""

    try:
        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data.get("accessToken", "")
        _LOGGER.debug("Token response (transport):\n%s", json.dumps(data, indent=4))

    except (requests.RequestException, requests.HTTPError, ValueError) as e:
        transport = False
        last_err = str(e)

    if not transport or (transport and not check_token_validity(token, data.get("clientId", ""), ua)):
        _LOGGER.info("Retrying token init mode")
        params["reason"] = "init"

        try:

            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            token = data.get("accessToken", "")
            _LOGGER.debug("Token response (init):\n%s", json.dumps(data, indent=4))

        except (requests.RequestException, requests.HTTPError, ValueError) as e:
            init = False
            last_err = str(e)

    if not init or not data or "accessToken" not in data:
        raise Exception(f"refresh_access_token_from_sp_dc(): Unsuccessful token request{': ' + last_err if last_err else ''}")

    return {
        "access_token": token,
        "expires_at": data["accessTokenExpirationTimestampMs"] // 1000,
        "client_id": data.get("clientId", ""),
        "length": len(token)
    }


def check_token_validity(access_token: str, client_id: str = "", user_agent: str = "") -> bool:
    url = "https://api.spotify.com/v1/me"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": client_id,
    }

    if user_agent:
        headers.update({
            "User-Agent": user_agent
        })

    try:
        response = requests.get(url, headers=headers, timeout=5)
        valid = response.status_code == 200
    except Exception:
        valid = False

    _LOGGER.debug("Token valid: %s", valid)

    return valid


def main():
    global USER_AGENT

    parser = argparse.ArgumentParser(description="Fetch Spotify access token based on provided SP_DC value")
    parser.add_argument("--sp-dc", help="Value of sp_dc cookie", default=None)
    args = parser.parse_args()

    sp_dc = args.sp_dc or SP_DC_COOKIE
    if not sp_dc:
        _LOGGER.error("sp_dc must be provided via --sp-dc or set in the script")
        return

    if not USER_AGENT:
        USER_AGENT = get_random_user_agent()

    try:
        token_data = refresh_access_token_from_sp_dc(sp_dc)
        token = token_data["access_token"]
        exp_ts = token_data["expires_at"]
        client_id = token_data["client_id"]

        print("\n📦 Access Token:", token)
        print("⏳ Expires at:", datetime.fromtimestamp(exp_ts, tz.tzlocal()).isoformat())
        print(f"👤 Client ID: {client_id}\n")

        valid = check_token_validity(token, client_id, USER_AGENT)
        print("✅ Token is valid." if valid else "❌ Token is not valid.")
    except Exception:
        _LOGGER.exception("Failed to refresh token")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
