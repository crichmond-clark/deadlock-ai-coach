"""Deadlock API fixture data for tests."""

HEROES_LIST = [
    {"hero_id": 63, "name": "Mina", "class_name": "CitadelHero_Mina", "image_url": "https://example.com/mina.png"},
    {"hero_id": 1, "name": "Abrams", "class_name": "CitadelHero_Abrams", "image_url": "https://example.com/abrams.png"},
]

ITEMS_LIST = [
    {"id": 1233782561, "name": "Love Bites", "item_type": "ability", "class_name": "ability", "image_url": "https://example.com/lovebites.png"},
    {"id": 24215179, "name": "Bullet Armor", "item_type": "armor", "class_name": "item", "image_url": "https://example.com/bulletarmor.png"},
    {"id": 999, "name": "Unknown Thing"},
]

MATCH_METADATA = {
    "match_id": 44009651,
    "duration_s": 1800,
    "start_time": 1713139200,
    "game_mode": 1,
    "winning_team": 2,
    "average_badge_team0": 15,
    "average_badge_team1": 12,
    "players": [
        {
            "account_id": 112233,
            "player_slot": 0,
            "hero_id": 63,
            "team": 0,
            "assigned_lane": 1,
            "kills": 8,
            "deaths": 3,
            "assists": 12,
            "net_worth": 24500,
            "last_hits": 120,
            "denies": 15,
            "level": 22,
        },
        {
            "account_id": None,
            "player_slot": 5,
            "hero_id": 1,
            "team": 1,
            "assigned_lane": 3,
            "kills": 0,
            "deaths": 10,
            "assists": 5,
            "net_worth": 8000,
            "last_hits": 45,
            "denies": 2,
            "level": 14,
        },
    ],
}
