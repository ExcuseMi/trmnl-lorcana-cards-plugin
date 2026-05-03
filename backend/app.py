import asyncio
import json
import logging
import os
import random

import aiohttp
from quart import Quart, Response, jsonify, request
from redis.asyncio import Redis

from modules.providers.lorcana import LorcanaProvider, _parse_multi
from modules.utils.ip_whitelist import init_ip_whitelist, require_tiered_access

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
log = logging.getLogger(__name__)

app = Quart(__name__)

REFRESH_HOURS = float(os.getenv('REFRESH_HOURS', '1'))
LOW_CARD_WARNING = int(os.getenv('LOW_CARD_WARNING_THRESHOLD', '10'))
LORCANA_SETS_API = 'https://api.lorcana-api.com/sets/all'
SETS_CACHE_KEY = 'lorcana:sets:v1'

_redis = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', '6379')),
    db=0,
    decode_responses=True,
)
_provider = LorcanaProvider(name='lorcana', redis=_redis)


@app.before_serving
async def _startup():
    await init_ip_whitelist()
    log.info('Lorcana Cards backend started — cache TTL: %sh', REFRESH_HOURS)


@app.route('/card')
@require_tiered_access(lambda: _redis, prefix='card')
async def card():
    colors = ','.join(sorted(_parse_multi(request.args.get('color', ''))))
    rarities = ','.join(sorted(_parse_multi(request.args.get('rarity', ''))))
    card_type = request.args.get('card_type', '').strip()
    set_id = request.args.get('set_id', '').strip()

    args = dict(color=colors, rarity=rarities, card_type=card_type, set_id=set_id)
    ttl = REFRESH_HOURS * 3600

    if await _provider.is_expired(ttl, **args):
        cached = await _provider.get_cached(**args)
        if cached:
            asyncio.create_task(_provider.refresh(**args))
        else:
            cached = await _provider.refresh(**args)
    else:
        cached = await _provider.get_cached(**args)

    if not cached:
        return jsonify({'error': 'Failed to fetch cards'}), 503

    selected = random.sample(cached, min(4, len(cached)))
    resp = {'data': selected}
    if len(cached) < LOW_CARD_WARNING:
        resp['pool_warning'] = len(cached)
    return jsonify(resp)


@app.route('/sets', methods=['GET', 'POST', 'OPTIONS'])
async def sets():
    if request.method == 'OPTIONS':
        return _cors(Response('', status=204))

    search = await _parse_search()

    raw_sets = None
    try:
        cached = await _redis.get(SETS_CACHE_KEY)
        if cached:
            raw_sets = json.loads(cached)
    except Exception:
        pass

    if raw_sets is None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LORCANA_SETS_API, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    raw_sets = await resp.json()
            try:
                await _redis.set(SETS_CACHE_KEY, json.dumps(raw_sets), ex=86400)
            except Exception:
                pass
        except Exception as exc:
            log.error('Error fetching sets: %s', exc)
            return _cors(jsonify({'error': 'Failed to fetch sets'})), 503

    result = _build_sets(raw_sets, search)
    return _cors(Response(json.dumps(result), content_type='application/json'))


async def _parse_search() -> str:
    if request.method == 'POST':
        try:
            body = await request.get_json(silent=True) or {}
            term = body.get('query') or body.get('search') or body.get('q') or ''
            return str(term).lower().strip()
        except Exception:
            pass
    queries = request.args.getlist('query')
    for q in reversed(queries):
        if q.strip():
            return q.lower().strip()
    return request.args.get('q', '').lower().strip()


def _build_sets(raw_sets: list, search: str) -> list:
    result = []
    for s in raw_sets:
        sid = s.get('Set_ID') or s.get('id', '')
        name = s.get('Set_Name') or s.get('name', '')
        release_date = s.get('Release_Date') or s.get('release_date', '')
        year_text = f" ({release_date[:4]})" if release_date else ''
        label = f"{name}{year_text}"
        if not sid or not label:
            continue
        if not search or search in label.lower():
            result.append({'id': sid, 'name': label, '_date': release_date})
    result.sort(key=lambda x: x.pop('_date'), reverse=True)
    if not search or search in 'most recent ★':
        most_recent = result[0]['id'] if result else ''
        result.insert(0, {'id': most_recent or 'most_recent', 'name': 'Most Recent ★'})
    return result


def _cors(response: Response) -> Response:
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response


@app.route('/health')
async def health():
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
