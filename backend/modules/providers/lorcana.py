import json
import logging
import random

import aiohttp

from modules.formatters.card import shape_card
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

LORCANA_API = 'https://api.lorcana-api.com'
ID_CAP = 200


def _parse_multi(value: str) -> list[str]:
    return [v.strip() for v in (value or '').split(',') if v.strip()]


class LorcanaProvider(BaseProvider):

    async def _fetch(self, **filters) -> list | None:
        colors = set(_parse_multi(filters.get('color', '')))
        rarities = set(_parse_multi(filters.get('rarity', '')))
        card_type = filters.get('card_type', '').strip()
        set_id = filters.get('set_id', '').strip()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{LORCANA_API}/bulk/cards', timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    resp.raise_for_status()
                    raw_bytes = await resp.read()
            try:
                text = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = raw_bytes.decode('latin-1')
            raw = json.loads(text)
        except Exception as exc:
            log.error('Error fetching lorcana cards: %s', exc)
            return None

        raw_list = raw if isinstance(raw, list) else []

        cards = []
        for c in raw_list:
            if not c.get('Image'):
                continue
            if colors:
                card_colors = {col.strip() for col in c.get('Color', '').split(',')}
                if not colors & card_colors:
                    continue
            if rarities and c.get('Rarity') not in rarities:
                continue
            if card_type and c.get('Type') != card_type:
                continue
            if set_id and str(c.get('Set_ID', '')) != set_id:
                continue
            cards.append(shape_card(c))

        if not cards:
            return None

        if len(cards) > ID_CAP:
            cards = random.sample(cards, ID_CAP)

        return cards
