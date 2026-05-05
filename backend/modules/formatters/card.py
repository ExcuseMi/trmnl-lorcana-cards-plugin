def shape_card(raw: dict) -> dict:
    classifications = raw.get('Classifications', [])
    if isinstance(classifications, str):
        classifications = [c.strip() for c in classifications.split(',') if c.strip()]

    return {
        'id': raw.get('Unique_ID', ''),
        'name': raw.get('Name', ''),
        'color': raw.get('Color', ''),
        'cost': raw.get('Cost'),
        'type': raw.get('Type', ''),
        'lore': raw.get('Lore'),
        'strength': raw.get('Strength'),
        'willpower': raw.get('Willpower'),
        'inkable': raw.get('Inkable', True),
        'rarity': raw.get('Rarity', ''),
        'set_name': raw.get('Set_Name', ''),
        'set_id': raw.get('Set_ID', ''),
        'set_num': raw.get('Set_Num', ''),
        'artist': raw.get('Artist', ''),
        'classifications': classifications,
        'flavor_text': raw.get('Flavor_Text', ''),
        'image': raw.get('Image', ''),
        'franchise': raw.get('Franchise', ''),
        'card_num': raw.get('Card_Num', ''),
        'set_release_date': raw.get('Release_Date', ''),
    }
