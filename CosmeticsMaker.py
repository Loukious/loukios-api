import traceback
import requests
import json
import sys


def log(message):
    print(message)
    sys.stdout.flush()


def GenerateCosmetics():
    url = "https://fortnite-api.com/v2/cosmetics/br?responseFlags=2"

    try:
        with requests.Session() as session:
            response = session.get(url)
            response.raise_for_status()  # Ensures HTTP errors are raised
            cosmetics = response.json()
    except requests.RequestException as e:
        log(f"Error fetching cosmetics data: {e}")
        return

    try:
        with open("CustomCos.json", "r") as cus:
            custom = json.load(cus)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"Error loading CustomCos.json: {e}")
        return

    # Load category sets from JSON
    MythicTags = set(custom["MythicTags"])
    MythicIds = set(custom["MythicIds"])
    ExoticIds = set(custom["ExoticIds"])
    ExoticTags = set(custom["ExoticTags"])
    TranscendentIds = set(custom["TranscendentIds"])
    TranscendentTags = set(custom["TranscendentTags"])
    BlackListedTags = set(custom["BlackListedTags"])
    BlackListedIds = set(custom["BlackListedIds"])
    OGs = set(custom["OGs"])

    valid_types = {"glider", "backpack", "pickaxe", "wrap", "outfit", "petcarrier", "emote"}

    cose = {}

    for item in cosmetics.get("data", []):
        try:
            item_id = item["id"].lower()
            item_name = item["name"]
            item_type = item["type"]["value"]
            item_tags = set(item.get("gameplayTags", []))
            item_rarity = item.get("rarity", {}).get("value", "").lower()

            if item_type not in valid_types:
                continue

            # Handle OG items
            if item_id in OGs:
                cose[f"og{item_id}"] = {
                    "name": f"OG {item_name}",
                    "gameplayTags": list(item_tags),
                    "rarity": "0"
                }

            # Determine rarity category
            if (item_id in ExoticIds or ExoticTags & item_tags) and not (item_id in BlackListedIds or BlackListedTags & item_tags):
                rarity = "1"
            elif (item_id in MythicIds or MythicTags & item_tags) and not (item_id in BlackListedIds or BlackListedTags & item_tags):
                rarity = "0"
            elif (item_id in TranscendentIds or TranscendentTags & item_tags) and not (item_id in BlackListedIds or BlackListedTags & item_tags):
                rarity = "2"
            else:
                rarity = item_rarity

            cose[item_id] = {
                "name": item_name,
                "gameplayTags": list(item_tags),
                "rarity": rarity
            }

        except Exception as e:
            log(f"Error processing item {item.get('id', 'Unknown')}: {e}")
            log(traceback.format_exc())

    try:
        with open("cosmetics.json", "w") as outfile:
            json.dump(cose, outfile, indent=4)
        log("Cosmetics file successfully created.")
    except IOError as e:
        log(f"Error writing cosmetics.json: {e}")


# GenerateCosmetics()