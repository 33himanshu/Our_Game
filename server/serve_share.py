"""Serves the shareable game folder AND relays play-with-a-friend messages over WebSocket.
Both players talk to this one server (through the public tunnel), so no direct browser-to-browser link is needed.
Run:  uv run --python 3.12 --with aiohttp python -B serve_share.py <folder> <port>
"""
import sys, os, json, asyncio
from aiohttp import web, WSMsgType
ROOT = os.path.abspath(sys.argv[1]); PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8788
rooms = {}                      # code -> {'host': ws, 'guest': ws}
CORS = {'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-store'}
async def ws_handler(req):
    code = (req.query.get('room') or '').upper()[:8]; role = req.query.get('role')
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=2_000_000); await ws.prepare(req)
    if not code or role not in ('host', 'guest'): await ws.close(); return ws
    room = rooms.setdefault(code, {})
    if role == 'guest' and 'host' not in room:
        await ws.send_str(json.dumps({'t': '_noroom'})); await ws.close(); rooms.pop(code, None) if not room else None; return ws
    if role in room:            # a second host or guest for the same code replaces the stale one
        try: await room[role].close()
        except Exception: pass
    room[role] = ws; other = 'guest' if role == 'host' else 'host'
    await ws.send_str(json.dumps({'t': '_ready'}))
    if 'host' in room and 'guest' in room:
        for w in (room['host'], room['guest']): await w.send_str(json.dumps({'t': '_open'}))
    try:
        async for m in ws:
            if m.type == WSMsgType.TEXT:
                o = room.get(other)
                if o is not None and not o.closed: await o.send_str(m.data)
            elif m.type in (WSMsgType.ERROR, WSMsgType.CLOSE): break
    finally:
        if room.get(role) is ws:
            room.pop(role, None); o = room.get(other)
            if o is not None and not o.closed:
                try: await o.send_str(json.dumps({'t': '_close'}))
                except Exception: pass
            if not room: rooms.pop(code, None)
    return ws
async def share(req):
    p = os.path.join(ROOT, 'share_url.txt'); url = open(p).read().strip() if os.path.exists(p) else ''
    return web.json_response({'url': url, 'relay': True}, headers=CORS)
async def static(req):
    rel = req.match_info.get('p', '') or 'index.html'; path = os.path.abspath(os.path.join(ROOT, rel))
    if not path.startswith(ROOT) or not os.path.isfile(path): return web.Response(status=404, text='not found')
    return web.FileResponse(path, headers={'Cache-Control': 'no-cache'})
app = web.Application(); app.add_routes([web.get('/ws', ws_handler), web.get('/share.json', share), web.get('/', static), web.get('/{p:.*}', static)])
web.run_app(app, host='127.0.0.1', port=PORT, print=None)
