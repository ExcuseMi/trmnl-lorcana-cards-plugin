function transform(input) {
  var LABELS = {
    cost: 'Cost',
    lore: 'Lore',
    str: 'Str',
    will: 'Wlp',
    type: 'Type',
    rarity: 'Rarity',
    set: 'Set',
    artist: 'Artist',
    ink: 'Ink',
    inkable: 'Inkable',
    franchise: 'Franchise',
  };

  var raw = Array.isArray(input.data) ? input.data : [];

  return {
    items: raw.slice(0, 4),
    labels: LABELS,
    pool_warning: typeof input.pool_warning === 'number' ? input.pool_warning : null,
  };
}
