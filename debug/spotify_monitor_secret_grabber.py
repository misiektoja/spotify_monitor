#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.3

Automatic extractor for secret keys used for TOTP generation in Spotify Web Player JavaScript bundles
https://github.com/misiektoja/spotify_monitor#debugging-tools

Python pip3 requirements:

playwright

Install:

pip install playwright
playwright install

---------------

Change log:

v1.3 (30 Apr 26):
- Added static extraction from inline secret object literals in current Spotify web-player bundles
- Preserved the original runtime property hook as a fallback for older bundle formats

v1.2 (12 Oct 25):
- Added CLI output modes (--secret, --secretbytes and --secretdict CLI flags, see -h for help)
- Added --all mode writing all secret formats to files (secrets.json, secretBytes.json, secretDict.json) (thx @tomballgithub)

v1.1 (12 Jul 25):
- Added JSON array output for plain secrets and secret bytes

v1.0 (09 Jul 25):
- Initial proof-of-concept, confirmed to extract v10, v11 and v12 secrets
"""


import asyncio
import ast
import re
from datetime import datetime
import json
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import argparse
import sys


BUNDLE_RE = re.compile(r"""(?x)(?:vendor~web-player|encore~web-player|web-player)\.[0-9a-f]{4,}\.(?:js|mjs)""")
JS_STRING_PATTERN = r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
SECRET_FIRST_RE = re.compile(r"\{\s*(?:secret|['\"]secret['\"])\s*:\s*(?P<secret>" + JS_STRING_PATTERN + r")\s*,\s*(?:version|['\"]version['\"])\s*:\s*(?P<version>\d+)\s*\}")
VERSION_FIRST_RE = re.compile(r"\{\s*(?:version|['\"]version['\"])\s*:\s*(?P<version>\d+)\s*,\s*(?:secret|['\"]secret['\"])\s*:\s*(?P<secret>" + JS_STRING_PATTERN + r")\s*\}")
TIMEOUT = 45000  # 45s
VERBOSE = True

OUTPUT_FILES = {
    'plain_json': 'secrets.json',
    'bytes_json_array': 'secretBytes.json',
    'bytes_json_dict': 'secretDict.json',
}


def _inline_int_array(nums):
    return '[ ' + ', '.join(str(n) for n in nums) + ' ]'


def _write_secretbytes_compact(fp, items):
    fp.write('[\n')
    last = len(items) - 1
    for i, itm in enumerate(items):
        comma = ',' if i < last else ''
        fp.write(f'  {{ "version": {itm["version"]}, "secret": {_inline_int_array(itm["secret"])} }}{comma}\n')
    fp.write(']\n')


def _write_secretdict_compact(fp, mapping):
    keys = sorted(mapping.keys(), key=lambda k: int(k))
    fp.write('{\n')
    for i, v in enumerate(keys):
        comma = ',' if i < len(keys) - 1 else ''
        fp.write(f'  "{v}": {_inline_int_array(mapping[v])}{comma}\n')
    fp.write('}\n')


# Logs a timestamped message when verbose output is enabled
def log(m):
    if VERBOSE:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")


# Decodes a quoted JavaScript string literal used by a secret object
def decode_js_string_literal(literal):
    try:
        value = ast.literal_eval(literal)
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, str) else None


# Extracts versioned TOTP secrets from current inline bundle object literals
def extract_bundle_secrets(source):
    captures = []
    seen = set()
    for pattern in (SECRET_FIRST_RE, VERSION_FIRST_RE):
        for match in pattern.finditer(source):
            secret = decode_js_string_literal(match.group('secret'))
            if secret is None:
                continue
            version = int(match.group('version'))
            key = (version, secret)
            if key in seen:
                continue
            seen.add(key)
            captures.append({'secret': secret, 'version': version, 'source': 'bundle'})
    return captures


# Formats extracted secrets for the selected output mode
def summarise(caps: List[Dict[str, Any]], mode=None):
    real = {}

    for cap in caps:
        sec = cap.get('secret')
        if not isinstance(sec, str):
            continue
        ver = cap.get('version') or (isinstance(cap.get('obj'), dict) and cap['obj'].get('version'))
        if ver is None:
            continue
        real[str(ver)] = sec

    if not real:
        log('No real secrets with version.')
        return

    sorted_items = sorted(real.items(), key=lambda kv: int(kv[0]))
    formatted_data = [{"version": int(v), "secret": s} for v, s in sorted_items]
    secret_bytes = [{"version": int(v), "secret": [ord(c) for c in s]} for v, s in sorted_items]
    secret_dict = {v: [ord(c) for c in s] for v, s in sorted_items}

    if mode is None:
        print("\n--- List of extracted secrets ---\n")
        for v, s in sorted(real.items(), key=lambda kv: int(kv[0])):
            print(f"v{v}: '{s}'")

        print("\n--- Plain secrets (JSON array) ---\n")
        print(json.dumps(formatted_data, indent=2))

        print("\n--- Secret bytes (JSON array) ---\n")
        print('[')
        for idx, itm in enumerate(secret_bytes):
            comma = ',' if idx < len(secret_bytes) - 1 else ''
            print('  {')
            print(f'    "version": {itm["version"]},')
            print(f'    "secret": {_inline_int_array(itm["secret"])}')
            print(f'  }}{comma}')
        print(']')

        print("\n--- Secret bytes (JSON object/dict): version -> byte list mapping ---\n")
        print('{')
        last = len(real) - 1
        for idx, (v, s) in enumerate(sorted(real.items(), key=lambda kv: int(kv[0]))):
            arr = [ord(c) for c in s]
            comma = ',' if idx < last else ''
            print(f'  "{v}": {_inline_int_array(arr)}{comma}')
        print('}')

    elif mode == 'secret':
        print(json.dumps(formatted_data, indent=2))

    elif mode == 'secretbytes':
        print('[')
        for idx, itm in enumerate(secret_bytes):
            comma = ',' if idx < len(secret_bytes) - 1 else ''
            print(f'  {{ "version": {itm["version"]}, "secret": {_inline_int_array(itm["secret"])} }}{comma}')
        print(']')

    elif mode == 'secretdict':
        print('{')
        last = len(real) - 1
        for idx, (v, s) in enumerate(sorted(real.items(), key=lambda kv: int(kv[0]))):
            arr = [ord(c) for c in s]
            comma = ',' if idx < last else ''
            print(f'  "{v}": {_inline_int_array(arr)}{comma}')
        print('}')

    elif mode == 'all':
        try:
            with open(OUTPUT_FILES['plain_json'], 'w') as f:
                json.dump(formatted_data, f, indent=2)
                f.write('\n')
            with open(OUTPUT_FILES['bytes_json_array'], 'w') as f:
                _write_secretbytes_compact(f, secret_bytes)
            with open(OUTPUT_FILES['bytes_json_dict'], 'w') as f:
                _write_secretdict_compact(f, secret_dict)
            if VERBOSE:
                print(f"[+] Wrote plain secrets to {OUTPUT_FILES['plain_json']}")
                print(f"[+] Wrote secret bytes array to {OUTPUT_FILES['bytes_json_array']}")
                print(f"[+] Wrote secret bytes dict to {OUTPUT_FILES['bytes_json_dict']}")
        except Exception as e:
            print(f"Error writing output files: {e}", file=sys.stderr)


# Extracts TOTP secrets from a live Spotify web-player session
async def grab_live():
    hook = """(()=>{if(globalThis.__secretHookInstalled)return;globalThis.__secretHookInstalled=true;globalThis.__captures=[];
Object.defineProperty(Object.prototype,'secret',{configurable:true,set:function(v){try{__captures.push({secret:v,version:this.version,obj:this});}catch(e){}
Object.defineProperty(this,'secret',{value:v,writable:true,configurable:true,enumerable:true});}});})();"""

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context()
        await ctx.add_init_script(hook)
        pg = await ctx.new_page()
        bundle_urls = []

        # Records matching Spotify bundle URLs for static parsing
        def record_bundle_response(resp):
            filename = resp.url.split('/')[-1].split('?', 1)[0]
            if BUNDLE_RE.fullmatch(filename):
                if resp.url not in bundle_urls:
                    bundle_urls.append(resp.url)
                log(f"[bundle] {filename} ({resp.status})")

        pg.on('response', record_bundle_response)
        log('Opening open.spotify.com ...')
        await pg.goto('https://open.spotify.com', timeout=TIMEOUT)
        await pg.wait_for_load_state('networkidle', timeout=TIMEOUT)
        await pg.wait_for_timeout(3000)
        caps = await pg.evaluate('__captures')

        for bundle_url in bundle_urls:
            try:
                response = await ctx.request.get(bundle_url, timeout=TIMEOUT)
                if not response.ok:
                    log(f"Bundle scan skipped HTTP {response.status}: {bundle_url}")
                    continue
                bundle_caps = extract_bundle_secrets(await response.text())
                caps.extend(bundle_caps)
                if bundle_caps:
                    log(f"Bundle scan found {len(bundle_caps)} versioned secret(s) in {bundle_url.split('/')[-1].split('?', 1)[0]}")
            except Exception as e:
                log(f"Bundle scan failed for {bundle_url}: {e}")

        if caps:
            for c in caps:
                if isinstance(c.get('secret'), str) and c.get('version') is not None:
                    log(f"Secret v{c.get('version')}: {c.get('secret')}")

        await b.close()
        return caps or []


# Parses CLI options and runs the secret extraction workflow
def main():
    parser = argparse.ArgumentParser(description='Extract Spotify web-player TOTP secrets')
    parser.add_argument('--secret', action='store_true', help='Output plain secrets JSON only')
    parser.add_argument('--secretbytes', action='store_true', help='Output secret-bytes JSON only')
    parser.add_argument('--secretdict', action='store_true', help='Output version->byte-list dict JSON only')
    parser.add_argument('--all', action='store_true', help='Write plain, bytes array and bytes dict JSON files')
    args = parser.parse_args()

    mode = None
    if args.secret:
        mode = 'secret'
    elif args.secretbytes:
        mode = 'secretbytes'
    elif args.secretdict:
        mode = 'secretdict'
    elif args.all:
        mode = 'all'

    global VERBOSE
    if mode and mode != 'all':
        VERBOSE = False
    elif mode == 'all':
        VERBOSE = True

    try:
        caps = asyncio.run(grab_live())
        summarise(caps, mode)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
