#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.9

Debug code to test the fetching of a Spotify access token using a Web Player sp_dc cookie and TOTP parameters
https://github.com/misiektoja/spotify_monitor#debugging-tools

Python pip3 requirements:

requests
python-dateutil
pyotp

For --fetch-secrets functionality (back-ported from spotify_monitor_secret_grabber.py):
playwright

---------------

options:
  -h, --help           show this help message and exit
  --sp-dc SP_DC        Value of sp_dc cookie
  --totp-ver TOTP_VER  Identifier of the secret key when generating a TOTP token (TOTP_VER)
  --fetch-secrets      Additionally fetch and update secret keys used for TOTP generation (extraction via headless web browser, requires playwright)
  --download-secrets   Additionally download and update secret keys used for TOTP generation (from remote or local URL)

---------------

Change log:

v1.9 (12 Oct 25):
- Added support for loading secrets from local files via file:// URLs (with support for expansion of ~ and environment variables in file paths)
- Updated remote URL in SECRET_CIPHER_DICT_URL

v1.8 (14 Jul 25):
- added automatic download of Spotify Web Player TOTP secrets from remote URL (when --download-secrets is used)
- updated list of secret cipher bytes and switched to use version 14

v1.7 (11 Jul 25):
- updated list of secret cipher bytes and switched to use version 13
- added possibility to specify TOTP_VER from cmd line (when --totp-ver is used)

v1.6 (10 Jul 25):
- added automatic extractor for Spotify Web Player TOTP secrets from JS bundles (when --fetch-secrets is used)

v1.5 (09 Jul 25):
- updated list of secret cipher bytes and switched to use version 12

v1.4 (09 Jul 25):
- updated list of secret cipher bytes and switched to use version 11

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
import re
import secrets
import time
from time import time_ns
from datetime import datetime
import random
from email.utils import parsedate_to_datetime
import pyotp
import requests
import json
import sys
from dateutil import tz


# Define below or via --sp-dc flag
SP_DC_COOKIE = ""

TOKEN_URL = "https://open.spotify.com/api/token"
SERVER_TIME_URL = "https://open.spotify.com/"

# Set to 0 to auto-select the highest available version
TOTP_VER = 0

SECRET_CIPHER_DICT = {
    "14": [62, 54, 109, 83, 107, 77, 41, 103, 45, 93, 114, 38, 41, 97, 64, 51, 95, 94, 95, 94],
    "13": [59, 92, 64, 70, 99, 78, 117, 75, 99, 103, 116, 67, 103, 51, 87, 63, 93, 59, 70, 45, 32],
}

# Remote or local URL used to fetch updated secrets needed for TOTP generation
# If you used "spotify_monitor_secret_grabber.py --secretdict > secretDict.json" specify the file location below
# SECRET_CIPHER_DICT_URL = "https://github.com/Thereallo1026/spotify-secrets/blob/main/secrets/secretDict.json?raw=true"
SECRET_CIPHER_DICT_URL = "https://github.com/xyloflake/spot-secrets-go/blob/main/secrets/secretDict.json?raw=true"
# SECRET_CIPHER_DICT_URL = file:///C:/your_path/secretDict.json
# SECRET_CIPHER_DICT_URL = "file:///your_path/secretDict.json"
# SECRET_CIPHER_DICT_URL = "file://~/secretDict.json"

# leave empty to auto generate randomly
USER_AGENT = ""

BUNDLE_RE = re.compile(r"""(?x)(?:vendor~web-player|encore~web-player|web-player)\.[0-9a-f]{4,}\.(?:js|mjs)""")
PLAYWRIGHT_TIMEOUT = 45000  # 45s

_LOGGER = logging.getLogger(__name__)


def fetch_secrets_from_web():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "\nPlaywright module is required for fetching secrets, please install it using:\n"
            "  pip install playwright\n"
            "  playwright install"
        )

    hook = """(()=>{if(globalThis.__secretHookInstalled)return;globalThis.__secretHookInstalled=true;globalThis.__captures=[];
Object.defineProperty(Object.prototype,'secret',{configurable:true,set:function(v){try{__captures.push({secret:v,version:this.version,obj:this});}catch(e){}
Object.defineProperty(this,'secret',{value:v,writable:true,configurable:true,enumerable:true});}});})();"""

    captures = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_init_script(hook)
        page = context.new_page()

        def handle_response(response):
            filename = response.url.split('/')[-1]
            if BUNDLE_RE.fullmatch(filename):
                _LOGGER.debug(f"↓ {filename} ({response.status})")

        page.on('response', handle_response)

        _LOGGER.debug('→ opening open.spotify.com ...')
        page.goto('https://open.spotify.com', timeout=PLAYWRIGHT_TIMEOUT)
        page.wait_for_load_state('networkidle', timeout=PLAYWRIGHT_TIMEOUT)
        page.wait_for_timeout(3000)

        captures = page.evaluate('__captures')

        if captures:
            for c in captures:
                if isinstance(c.get('secret'), str) and c.get('version') is not None:
                    _LOGGER.debug(f"✔ secret({c.get('version')}) → {c.get('secret')}")

        browser.close()

    return captures or []


def update_secret_cipher_dict(captures):
    global SECRET_CIPHER_DICT, TOTP_VER

    real_secrets = {}

    for cap in captures:
        sec = cap.get('secret')
        if not isinstance(sec, str):
            continue
        ver = cap.get('version') or (isinstance(cap.get('obj'), dict) and cap['obj'].get('version'))
        if ver is None:
            continue
        real_secrets[str(ver)] = sec

    if not real_secrets:
        _LOGGER.debug('No real secrets with version.')
        return False

    _LOGGER.debug('List of leaked secrets:\n')
    for v, s in sorted(real_secrets.items(), key=lambda kv: int(kv[0])):
        print(f"v{v}: '{s}'")
    print()

    updated = False
    for ver, secret in real_secrets.items():
        byte_array = [ord(c) for c in secret]

        if ver not in SECRET_CIPHER_DICT or SECRET_CIPHER_DICT[ver] != byte_array:
            SECRET_CIPHER_DICT[ver] = byte_array
            updated = True
            _LOGGER.debug(f"Updated secret for version {ver}")
        else:
            _LOGGER.debug(f"Secret for version {ver} is unchanged")

    _LOGGER.debug('Updated dictionary with secret keys (SECRET_CIPHER_DICT):')
    print('{')
    items = sorted(SECRET_CIPHER_DICT.items(), key=lambda kv: int(kv[0]))
    for idx, (v, arr) in enumerate(reversed(items)):
        comma = ',' if idx < len(items) - 1 else ''
        print(f'  "{v}": {arr}{comma}')
    print('}')

    highest_ver = max(int(v) for v in SECRET_CIPHER_DICT.keys())
    if highest_ver != TOTP_VER:
        _LOGGER.debug(f"Updating TOTP_VER from {TOTP_VER} to {highest_ver}")
        TOTP_VER = highest_ver

    return updated


def fetch_and_update_secrets():
    global SECRET_CIPHER_DICT, TOTP_VER

    if not SECRET_CIPHER_DICT_URL:
        return False

    try:
        if SECRET_CIPHER_DICT_URL.startswith("file:"):
            import os
            from urllib.parse import urlparse, unquote

            parsed = urlparse(SECRET_CIPHER_DICT_URL)

            if parsed.netloc:
                raw_path = f"/{parsed.netloc}{parsed.path or ''}"
            else:
                if SECRET_CIPHER_DICT_URL.startswith("file://"):
                    raw_path = parsed.path or SECRET_CIPHER_DICT_URL[len("file://"):]
                else:
                    raw_path = parsed.path or SECRET_CIPHER_DICT_URL[len("file:"):]

            raw_path = unquote(raw_path)

            if raw_path.startswith("/~"):
                raw_path = raw_path[1:]

            if not raw_path.startswith("/") and not raw_path.startswith("~"):
                raw_path = "/" + raw_path

            path = os.path.expanduser(os.path.expandvars(raw_path))

            with open(path, "r", encoding="utf-8") as f:
                secrets = json.load(f)
        else:
            response = requests.get(SECRET_CIPHER_DICT_URL, timeout=10)
            response.raise_for_status()
            secrets = response.json()

        if not isinstance(secrets, dict) or not secrets:
            raise ValueError("Fetched payload not a non-empty dict")

        for key, value in secrets.items():
            if not isinstance(key, str) or not key.isdigit():
                raise ValueError(f"Invalid key format: {key}")
            if not isinstance(value, list) or not all(isinstance(x, int) for x in value):
                raise ValueError(f"Invalid value format for key {key}")

        _LOGGER.debug('List of downloaded secrets:\n')
        for v, s in sorted(secrets.items(), key=lambda kv: int(kv[0])):
            decoded = ''.join(chr(x) for x in s)
            print(f"v{v}: '{decoded}'")
        print()

        updated = False
        for ver, secret in secrets.items():
            byte_array = list(secret)

            if ver not in SECRET_CIPHER_DICT or SECRET_CIPHER_DICT[ver] != byte_array:
                SECRET_CIPHER_DICT[ver] = byte_array
                updated = True
                _LOGGER.debug(f"Updated secret for version {ver}")
            else:
                _LOGGER.debug(f"Secret for version {ver} is unchanged")

        _LOGGER.debug('Updated dictionary with secret keys (SECRET_CIPHER_DICT):')
        print('{')
        items = sorted(SECRET_CIPHER_DICT.items(), key=lambda kv: int(kv[0]))
        for idx, (v, arr) in enumerate(reversed(items)):
            comma = ',' if idx < len(items) - 1 else ''
            print(f'  "{v}": {arr}{comma}')
        print('}')

        highest_ver = max(int(v) for v in SECRET_CIPHER_DICT.keys())
        if highest_ver != TOTP_VER:
            _LOGGER.debug(f"Updating TOTP_VER from {TOTP_VER} to {highest_ver}")
            TOTP_VER = highest_ver

        return True

    except Exception as e:
        print(f"Failed to get new secrets: {e}")
        return False


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


def generate_totp():
    _LOGGER.debug("Generating TOTP")

    if str((ver := TOTP_VER or max(map(int, SECRET_CIPHER_DICT)))) not in SECRET_CIPHER_DICT:
        raise Exception(f"Defined TOTP_VER ({ver}) is missing in SECRET_CIPHER_DICT")

    secret_cipher_bytes = SECRET_CIPHER_DICT[str(ver)]

    _LOGGER.debug("TOTP ver: %s", ver)
    _LOGGER.debug("TOTP cipher: %s", secret_cipher_bytes)

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
        raise Exception(f"Unsuccessful token request{': ' + last_err if last_err else ''}")

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
    global USER_AGENT, TOTP_VER

    parser = argparse.ArgumentParser(description="Fetch Spotify access token using a Web Player sp_dc cookie and TOTP parameters")
    parser.add_argument("--sp-dc", help="Value of sp_dc cookie", default=None)
    parser.add_argument("--totp-ver", help="Identifier of the secret key when generating a TOTP token (TOTP_VER)", default=None)
    parser.add_argument("--fetch-secrets", action="store_true", help="Additionally fetch and update secret keys used for TOTP generation (extraction via headless web browser, requires playwright)")
    parser.add_argument("--download-secrets", action="store_true", help="Additionally download and update secret keys used for TOTP generation (from remote or local URL)")
    args = parser.parse_args()

    if args.fetch_secrets:
        try:
            _LOGGER.debug("Fetching secret keys used for TOTP generation ...")
            captures = fetch_secrets_from_web()
            if captures:
                update_secret_cipher_dict(captures)
            else:
                _LOGGER.debug("No secrets captured, using existing SECRET_CIPHER_DICT")
        except ImportError as e:
            _LOGGER.error("Error: %s", e)
            return
        except Exception as e:
            _LOGGER.error("Failed to fetch secrets: %s", e)
            _LOGGER.debug("Reverting to existing SECRET_CIPHER_DICT")

    if args.download_secrets:
        _LOGGER.debug("Downloading secret keys used for TOTP generation ...")
        _LOGGER.debug("URL: %s", SECRET_CIPHER_DICT_URL)
        if not fetch_and_update_secrets():
            _LOGGER.error("Failed to download secrets")

    if args.totp_ver:
        try:
            _LOGGER.debug(f"Setting TOTP_VER to {args.totp_ver}")
            TOTP_VER = int(args.totp_ver)
        except Exception as e:
            _LOGGER.error("Failed to set TOTP_VER from parameter: %s", e)
            _LOGGER.debug("Reverting to existing TOTP_VER")

    sp_dc = args.sp_dc or SP_DC_COOKIE
    if not sp_dc:
        parser.print_help(sys.stderr)
        print()
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
