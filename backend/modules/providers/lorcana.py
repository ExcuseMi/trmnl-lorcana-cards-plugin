import asyncio
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
        colors = _parse_multi(filters.get('color', ''))
        rarities = _parse_multi(filters.get('rarity', ''))
        card_type = filters.get('card_type', '').strip()
        set_id = filters.get('set_id', '').strip()

        c_list = colors or ['']
        r_list = rarities or ['']

        tasks = [
            self._fetch_cards_single(color=c, rarity=r, card_type=card_type, set_id=set_id)
            for c in c_list for r in r_list
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen = {}
        for res in results:
            if isinstance(res, list):
                for card in res:
                    card_id = card.get('id', '')
                    if card_id and card_id not in seen:
                        seen[card_id] = card

        cards = list(seen.values())
        if not cards:
            return None

        if len(cards) > ID_CAP:
            cards = random.sample(cards, ID_CAP)

        return cards

    async def _fetch_cards_single(
        self, color: str = '', rarity: str = '', card_type: str = '', set_id: str = ''
    ) -> list:
        params = {}
        if color:
            params['Color'] = color
        if rarity:
            params['Rarity'] = rarity
        if card_type:
            params['Type'] = card_type
        if set_id:
            params['Set_ID'] = set_id

        url = f'{LORCANA_API}/bulk/cards' if not params else f'{LORCANA_API}/cards/fetch'

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            raw_list = data if isinstance(data, list) else []
            return [shape_card(c) for c in raw_list if c.get('Image')]
        except Exception as exc:
            log.error('Error fetching lorcana cards (color=%s rarity=%s type=%s set=%s): %s',
                      color, rarity, card_type, set_id, exc)
            return []
