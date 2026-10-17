"""Pure-Python palette generator: skin undertone -> harmonious makeup hues.

Deterministic given the caller's random.Random instance. No network,
no side effects, no ML. Hue families follow simple complementary /
analogous color-harmony rules per undertone.
"""

FAMILIES = {
    # ---- warm undertones ----
    "terracotta": {
        "undertones": ["warm", "neutral"],
        "lips": ["#B5542D", "#A34A28", "#C06A3B"],
        "blush": ["#D98A68", "#C97B5A"],
        "shadows": ["#8A5A3B", "#C98B5E", "#5E3A24", "#E0B48F"],
        "textures": ["matte", "satin"],
        "names": ["Copper Jackpot", "Terracotta Triple-7", "Ember Spin"],
    },
    "coral": {
        "undertones": ["warm", "neutral"],
        "lips": ["#E2725B", "#D95F4B", "#EE7E6B"],
        "blush": ["#F0977F", "#E8836B"],
        "shadows": ["#C98B5E", "#8A5A3B", "#F0C29B", "#A34A28"],
        "textures": ["satin", "gloss"],
        "names": ["Coral Cascade", "Sunset Spin", "Jackpot Glow"],
    },
    "bronze": {
        "undertones": ["warm"],
        "lips": ["#8C5A2B", "#7A4A22", "#9C6A35"],
        "blush": ["#C98B5E", "#B87B4F"],
        "shadows": ["#5E3A24", "#8A5A3B", "#D4A574", "#3E2A18"],
        "textures": ["metallic", "shimmer"],
        "names": ["Bronze Bonanza", "Gilded Reel", "Lucky Bronze"],
    },
    "honey": {
        "undertones": ["warm", "neutral"],
        "lips": ["#C68E5E", "#B57E50", "#D4A06A"],
        "blush": ["#E0B48F", "#D4A06A"],
        "shadows": ["#8A5A3B", "#C98B5E", "#E8C9A0", "#6E4A30"],
        "textures": ["satin", "matte"],
        "names": ["Honey Hit", "Nude Jackpot", "Golden Nudge"],
    },
    # ---- cool undertones ----
    "berry": {
        "undertones": ["cool", "neutral"],
        "lips": ["#8E2A4B", "#7A2340", "#A03555"],
        "blush": ["#C06A85", "#B25A75"],
        "shadows": ["#5A2A3A", "#8E4A5B", "#D49AAE", "#3E1E28"],
        "textures": ["matte", "satin"],
        "names": ["Berry Bonanza", "Jackpot Jam", "Wild Berry Spin"],
    },
    "mauve": {
        "undertones": ["cool"],
        "lips": ["#9E6B7E", "#8A5A6E", "#B07E90"],
        "blush": ["#C49AAE", "#B58AA0"],
        "shadows": ["#6E4A5A", "#9E7A8A", "#D4B8C4", "#4E3440"],
        "textures": ["matte", "shimmer"],
        "names": ["Mauve Magic", "Dusty Jackpot", "Lucky Mauve"],
    },
    "rose": {
        "undertones": ["cool", "neutral"],
        "lips": ["#D46A7E", "#C25A6E", "#E07E90"],
        "blush": ["#E89AAB", "#DE8A9E"],
        "shadows": ["#9E5A6E", "#C48A9E", "#F0C4CE", "#7A3A4A"],
        "textures": ["satin", "gloss"],
        "names": ["Rosé Reel", "Petal Payout", "Jackpot Bloom"],
    },
    "plum": {
        "undertones": ["cool"],
        "lips": ["#6E2A4B", "#5E2340", "#7E3555"],
        "blush": ["#A05A75", "#905065"],
        "shadows": ["#3E1E2E", "#5E2A40", "#8E5A6E", "#2A1420"],
        "textures": ["metallic", "matte"],
        "names": ["Plum Payday", "Midnight Spin", "Velvet Jackpot"],
    },
}


def families_for(undertone):
    """Family names harmonious with the given undertone."""
    if undertone not in ("warm", "cool", "neutral"):
        undertone = "neutral"
    return [name for name, spec in FAMILIES.items() if undertone in spec["undertones"]]


def taste_weight(likes, dislikes):
    """Laplace-smoothed preference weight: liked families spin more often."""
    return (likes + 1) / (likes + dislikes + 2)


def generate_palette(undertone, taste, rng):
    """Build one look palette.

    undertone: 'warm' | 'cool' | 'neutral'
    taste: {(family, texture): (likes, dislikes)}
    rng: random.Random instance (caller-seeded -> deterministic)
    """
    candidates = families_for(undertone)
    fam_weights = []
    for fam in candidates:
        likes = sum(l for (f, _t), (l, _d) in taste.items() if f == fam)
        dislikes = sum(d for (f, _t), (_l, d) in taste.items() if f == fam)
        fam_weights.append(taste_weight(likes, dislikes))
    family = rng.choices(candidates, weights=fam_weights, k=1)[0]

    spec = FAMILIES[family]
    tex_weights = [taste_weight(*taste.get((family, t), (0, 0))) for t in spec["textures"]]
    texture = rng.choices(spec["textures"], weights=tex_weights, k=1)[0]

    return {
        "family": family,
        "texture": texture,
        "lip": {"hex": rng.choice(spec["lips"]), "texture": texture},
        "blush_hex": rng.choice(spec["blush"]),
        "shadows": rng.sample(spec["shadows"], k=min(3, len(spec["shadows"]))),
        "intensity": rng.randint(60, 90),
        "look_name": rng.choice(spec["names"]),
    }
