#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.0

Automatic extractor for secret keys used for TOTP generation in Spotify Web Player JavaScript bundles
https://github.com/misiektoja/spotify_monitor#debugging-tools

Python pip3 requirements:

playwright

Install:

pip install playwright
playwright install

---------------

Change log:

v1.0 (09 Jul 25):
- Initial proof-of-concept, confirmed to extract v10, v11 and v12 secrets
"""


import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright


BUNDLE_RE = re.compile(r"""(?x)(?:vendor~web-player|encore~web-player|web-player)\.[0-9a-f]{4,}\.(?:js|mjs)""")
TIMEOUT = 45000  # 45s
VERBOSE = True


def log(m):
    if VERBOSE:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")


def summarise(caps: List[Dict[str, Any]]):
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

    for v, s in sorted(real.items(), key=lambda kv: int(kv[0])): print(f"v{v}: {s}")

    print('{')
    last = len(real) - 1

    for idx, (v, s) in enumerate(sorted(real.items(), key=lambda kv: int(kv[0]))):
        arr = ', '.join(str(ord(c)) for c in s)
        comma = ',' if idx < last else ''
        print(f'  "{v}": [{arr}]{comma}')

    print('}')


async def grab_live():
    hook = """(()=>{if(globalThis.__secretHookInstalled)return;globalThis.__secretHookInstalled=true;globalThis.__captures=[];
Object.defineProperty(Object.prototype,'secret',{configurable:true,set:function(v){try{__captures.push({secret:v,version:this.version,obj:this});}catch(e){}
Object.defineProperty(this,'secret',{value:v,writable:true,configurable:true,enumerable:true});}});})();"""

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context()
        await ctx.add_init_script(hook)
        pg = await ctx.new_page()
        pg.on('response', lambda resp: BUNDLE_RE.fullmatch(resp.url.split('/')[-1]) and log(f"↓ {resp.url.split('/')[-1]} ({resp.status})"))
        log('→ opening open.spotify.com ...')
        await pg.goto('https://open.spotify.com', timeout=TIMEOUT)
        await pg.wait_for_load_state('networkidle', timeout=TIMEOUT)
        await pg.wait_for_timeout(3000)
        caps = await pg.evaluate('__captures')

        if caps:
            for c in caps:
                # if isinstance(c.get('secret'), str):
                if isinstance(c.get('secret'), str) and c.get('version') is not None:
                    log(f"✔ secret({c.get('version')}) → {c.get('secret')}")

        await b.close()
        return caps or []


def main():
    caps = asyncio.run(grab_live())
    summarise(caps)


if __name__ == '__main__':
    main()
