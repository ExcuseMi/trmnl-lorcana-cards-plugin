import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))

from modules.providers.lorcana import LorcanaProvider, _parse_multi

RAW_CARD = {
    'Unique_ID': 'TFC-001',
    'Name': 'César Vergara Card',
    'Color': 'Amber',
    'Cost': 3,
    'Type': 'Character',
    'Lore': 2,
    'Strength': 2,
    'Willpower': 3,
    'Inkable': True,
    'Rarity': 'Rare',
    'Set_Name': 'The First Chapter',
    'Set_ID': 'TFC',
    'Set_Num': 1,
    'Card_Num': 1,
    'Artist': 'César Vergara / Eri Wëlli',
    'Classifications': 'Storyborn, Hero',
    'Body_Text': '',
    'Flavor_Text': '',
    'Image': 'https://example.com/card.jpg',
    'Franchise': 'Frozen',
    'Release_Date': '',
}


def _make_provider():
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return LorcanaProvider(name='lorcana', redis=redis)


def _mock_resp(cards: list, encoding: str = 'utf-8'):
    raw_bytes = json.dumps(cards).encode(encoding)
    resp = AsyncMock()
    resp.raise_for_status = MagicMock()
    resp.read = AsyncMock(return_value=raw_bytes)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _mock_session(resp):
    session = MagicMock()
    session.get = MagicMock(return_value=resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


class TestEncoding(unittest.IsolatedAsyncioTestCase):

    async def _fetch_with_bytes(self, raw_bytes):
        provider = _make_provider()
        resp = AsyncMock()
        resp.raise_for_status = MagicMock()
        resp.read = AsyncMock(return_value=raw_bytes)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)
        session = _mock_session(resp)
        with patch('modules.providers.lorcana.aiohttp.ClientSession', return_value=session):
            return await provider._fetch()

    async def test_utf8_encoding(self):
        cards = await self._fetch_with_bytes(json.dumps([RAW_CARD]).encode('utf-8'))
        self.assertIsNotNone(cards)
        self.assertEqual(cards[0]['artist'], 'César Vergara / Eri Wëlli')

    async def test_latin1_encoding(self):
        # API sometimes sends latin-1 bytes — accented chars must survive
        cards = await self._fetch_with_bytes(json.dumps([RAW_CARD]).encode('latin-1'))
        self.assertIsNotNone(cards)
        self.assertEqual(cards[0]['artist'], 'César Vergara / Eri Wëlli')

    async def test_latin1_no_question_marks(self):
        cards = await self._fetch_with_bytes(json.dumps([RAW_CARD]).encode('latin-1'))
        self.assertNotIn('?', cards[0]['artist'])


class TestFiltering(unittest.IsolatedAsyncioTestCase):

    def _card(self, **overrides):
        return {**RAW_CARD, **overrides}

    async def _fetch(self, cards, **filters):
        provider = _make_provider()
        resp = _mock_resp(cards)
        session = _mock_session(resp)
        with patch('modules.providers.lorcana.aiohttp.ClientSession', return_value=session):
            return await provider._fetch(**filters)

    async def test_no_filters_returns_all(self):
        cards = [self._card(Unique_ID='X-001'), self._card(Unique_ID='X-002')]
        result = await self._fetch(cards)
        self.assertEqual(len(result), 2)

    async def test_rarity_single(self):
        cards = [
            self._card(Unique_ID='X-001', Rarity='Legendary'),
            self._card(Unique_ID='X-002', Rarity='Common'),
        ]
        result = await self._fetch(cards, rarity='Legendary')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rarity'], 'Legendary')

    async def test_rarity_multi(self):
        cards = [
            self._card(Unique_ID='X-001', Rarity='Legendary'),
            self._card(Unique_ID='X-002', Rarity='Enchanted'),
            self._card(Unique_ID='X-003', Rarity='Common'),
        ]
        result = await self._fetch(cards, rarity='Legendary,Enchanted')
        self.assertEqual(len(result), 2)
        self.assertNotIn('Common', {c['rarity'] for c in result})

    async def test_rarity_super_rare(self):
        cards = [
            self._card(Unique_ID='X-001', Rarity='Super Rare'),
            self._card(Unique_ID='X-002', Rarity='Rare'),
        ]
        result = await self._fetch(cards, rarity='Super Rare')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rarity'], 'Super Rare')

    async def test_color_single(self):
        cards = [
            self._card(Unique_ID='X-001', Color='Amber'),
            self._card(Unique_ID='X-002', Color='Ruby'),
        ]
        result = await self._fetch(cards, color='Amber')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['color'], 'Amber')

    async def test_color_multi_ink_card(self):
        # Dual-ink cards like "Amber, Steel" should match either color filter
        cards = [
            self._card(Unique_ID='X-001', Color='Amber, Steel'),
            self._card(Unique_ID='X-002', Color='Ruby'),
        ]
        result = await self._fetch(cards, color='Amber')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'X-001')

    async def test_color_multi_filter(self):
        cards = [
            self._card(Unique_ID='X-001', Color='Amber'),
            self._card(Unique_ID='X-002', Color='Ruby'),
            self._card(Unique_ID='X-003', Color='Steel'),
        ]
        result = await self._fetch(cards, color='Amber,Ruby')
        self.assertEqual(len(result), 2)

    async def test_card_type_filter(self):
        cards = [
            self._card(Unique_ID='X-001', Type='Character'),
            self._card(Unique_ID='X-002', Type='Action'),
        ]
        result = await self._fetch(cards, card_type='Action')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'Action')

    async def test_set_id_filter(self):
        cards = [
            self._card(Unique_ID='TFC-001', Set_ID='TFC'),
            self._card(Unique_ID='WIN-001', Set_ID='WIN'),
        ]
        result = await self._fetch(cards, set_id='WIN')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['set_id'], 'WIN')

    async def test_missing_image_excluded(self):
        cards = [
            self._card(Unique_ID='X-001', Image=''),
            self._card(Unique_ID='X-002'),
        ]
        result = await self._fetch(cards)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'X-002')

    async def test_empty_pool_returns_none(self):
        cards = [self._card(Rarity='Common')]
        result = await self._fetch(cards, rarity='Legendary')
        self.assertIsNone(result)

    async def test_api_error_returns_none(self):
        provider = _make_provider()
        with patch('modules.providers.lorcana.aiohttp.ClientSession', side_effect=Exception('network error')):
            result = await provider._fetch()
        self.assertIsNone(result)


class TestParseMulti(unittest.TestCase):

    def test_single(self):
        self.assertEqual(_parse_multi('Amber'), ['Amber'])

    def test_multi(self):
        self.assertEqual(_parse_multi('Amber,Ruby'), ['Amber', 'Ruby'])

    def test_spaces(self):
        self.assertEqual(_parse_multi('Amber, Ruby'), ['Amber', 'Ruby'])

    def test_empty(self):
        self.assertEqual(_parse_multi(''), [])

    def test_none(self):
        self.assertEqual(_parse_multi(None), [])


if __name__ == '__main__':
    unittest.main()
