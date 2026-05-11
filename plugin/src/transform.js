function transform(input) {
  var LABELS = {
    set: 'Set',
    released: 'Released',

    num: 'No.',
    franchise: 'Franchise',
    ink: 'Ink',
    type: 'Type',
    rarity: 'Rarity',
    artist: 'Artist',
    cost: 'Cost',
    lore: 'Lore',
    str: 'Strength',
    will: 'Willpower',
    inkable: 'Inkable',

  };

  var raw = Array.isArray(input.data) ? input.data : [];

  return {
    items: raw.slice(0, 4),
    labels: LABELS,
    pool_warning: typeof input.pool_warning === 'number' ? input.pool_warning : null,
  };
}
