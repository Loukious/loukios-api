import json
from PIL import Image, ImageFont, ImageDraw
import base64
import io
import requests
import os
import sys
import traceback
import concurrent.futures
from skimage.io._plugins.pil_plugin import pil_to_ndarray, ndarray_to_pil
from skimage import transform as tf

def log(message):
    print(message)
    sys.stdout.flush()

class Item:
    def __init__(self):
        self.id = ""
        self.name = ""
        self.icon = ""
        self.rarity = ""
        self.description = ""
        self.tags = []

    def IsReactive(self):
        """Checks if item is 'reactive' by looking for certain flags in gameplay tags."""
        if self.tags:
            for tag in self.tags:
                if tag.startswith("Cosmetics.UserFacingFlags"):
                    return True
            return False
        return False

    def GetSource(self):
        """Returns the 'Cosmetics.Source.xxx' portion of the tag, e.g. 'ItemShop', uppercased."""
        if self.tags:
            for tag in self.tags:
                if tag.startswith("Cosmetics.Source"):
                    # Example: Cosmetics.Source.ItemShop => 'ITEMSHOP'
                    return tag[17:].upper()
        return None

    def GetSeason(self):
        """Returns a simplified season string from 'Cosmetics.Filter.Season.X' tag."""
        if self.tags:
            for tag in self.tags:
                if tag.startswith("Cosmetics.Filter.Season."):
                    nb = int(tag.split(".")[-1])
                    if nb < 9:
                        return f"C1S{nb}"
                    elif 9 < nb < 19:
                        return f"C2S{nb - 9}"
                    else:
                        return f"C3S{nb - 18}"
        return None

    def DownloadImg(self):
        """Downloads the icon PNG if it doesn't already exist locally."""
        out_path = f'icons/{self.id.lower()}.png'
        if not os.path.exists('icons'):
            os.makedirs('icons')

        if not os.path.exists(out_path):
            try:
                with requests.session() as s:
                    response = s.get(self.icon, stream=True)
                    response.raise_for_status()  # raise exception if failed
                    with open(out_path, 'wb') as out_file:
                        out_file.write(response.content)
                        out_file.flush()
            except Exception:
                log(f"Failed to download: {self.icon}")
                log(traceback.format_exc())

def CreateIcon(item, design):
    """Create a final 256x256 icon with background, item PNG, overlays, etc."""
    try:
        # If the final icon is already there, skip re-creation
        out_path = f"icons/{item.id.lower()}.png"
        if os.path.exists(out_path):
            return  # Skip everything if the file already exists

        # Decode base64 images from design
        rarity_design = design["rarities"].get(item.rarity, None)
        if rarity_design is None:
            # If rarity key doesn't exist, skip or fallback
            log(f"Unknown rarity: {item.rarity} for {item.id}")
            return

        background = Image.open(io.BytesIO(base64.b64decode(rarity_design["background"]))).resize((256, 256))
        upper = Image.open(io.BytesIO(base64.b64decode(rarity_design["upper"]))).resize((256, 256))
        lower = Image.open(io.BytesIO(base64.b64decode(rarity_design["lower"]))).resize((256, 256))

        # Prepare base icon
        icon = Image.new("RGB", (256, 256))
        icon.paste(background, (0, 0), background.convert("RGBA"))
        icon.paste(upper, (0, 0), upper.convert("RGBA"))

        # Download item icon if missing
        item.DownloadImg()
        item_icon = Image.open(f"icons/{item.id.lower()}.png").convert("RGBA")
        icon.paste(item_icon, (0, 0), item_icon)

        icon.paste(lower, (0, 0), lower.convert("RGBA"))

        # If reactive, place custom overlay
        if item.IsReactive():
            reactive_img = Image.open(
                io.BytesIO(base64.b64decode(design["gameplayTags"]["custom"]))
            ).resize((256, 256))
            icon.paste(reactive_img, (0, 0), reactive_img.convert("RGBA"))

        # Create an overlay (text, etc.)
        overlay = Image.new("RGBA", (280, 50))
        draw = ImageDraw.Draw(overlay, "RGBA")

        # --- Draw Item Name ---
        NameFont = ImageFont.truetype("all.ufont", size=16)
        left, top, right, bottom = draw.textbbox((0, 0), item.name, font=NameFont)
        text_width = right - left
        text_height = bottom - top
        # Center text horizontally at ~128, top ~12
        draw.text(
            (128 - text_width / 2, 12 - text_height / 2),
            item.name,
            font=NameFont,
            fill="#FFFFFF",
            stroke_width=1,
            stroke_fill="black"
        )

        # --- Draw Item Description ---
        DescFont = ImageFont.truetype("desc.ufont", size=8)
        left, top, right, bottom = draw.textbbox((0, 0), item.description, font=DescFont)
        text_width = right - left
        text_height = bottom - top
        # Center text horizontally at ~128, top ~27
        draw.text(
            (128 - text_width / 2, 27 - text_height / 2),
            item.description,
            font=DescFont,
            fill="#FFFFFF",
            stroke_width=1,
            stroke_fill="black"
        )

        # --- Draw Source ---
        source = item.GetSource()
        if source:
            SourceFont = ImageFont.truetype("all.ufont", size=9)
            draw.text(
                (15, 36),
                source,
                font=SourceFont,
                fill="#A7B8BC"
            )

        # --- Draw Season ---
        season = item.GetSeason()
        if season:
            SeasonFont = ImageFont.truetype("all.ufont", size=9)
            # Right-align near x=240
            draw.text(
                (240, 36),
                season,
                font=SeasonFont,
                fill="#A7B8BC"
            )

        # Shear transform using scikit-image
        overlay_arr = pil_to_ndarray(overlay)
        afine_tf = tf.AffineTransform(shear=-0.25)
        overlay_a = tf.warp(overlay_arr, inverse_map=afine_tf)
        overlay_sheared = ndarray_to_pil(overlay_a)

        # Paste overlay near bottom of icon
        icon.paste(overlay_sheared, (0, 206), overlay_sheared)
        icon.save(out_path)
    except Exception:
        log(f"Error creating icon for {item.id}")
        log(traceback.format_exc())


def GenerateIcons():
    log("Generating icons...")

    # Load external JSON once for all icons
    with open('Cataba.json', 'r') as f:
        design = json.load(f)

    url = "https://fortnite-api.com/v2/cosmetics/br?responseFlags=2"
    with requests.session() as s:
        data = s.get(url, stream=True).json()

    known_rarities = {
        "common", "uncommon", "rare", "epic", "legendary", "mythic",
        "exotic", "transcendent", "unattainable", "marvelseries",
        "platformseries", "dcuseries", "shadowseries", "cubeseries",
        "columbusseries", "creatorcollabseries", "slurpseries",
        "frozenseries", "lavaseries"
    }

    with open("CustomCos.json", "r") as cus:
        custom = json.load(cus)
    MythicTags = custom["MythicTags"]
    MythicIds = custom["MythicIds"]
    ExoticIds = custom["ExoticIds"]
    ExoticTags = custom["ExoticTags"]
    TranscendentIds = custom["TranscendentIds"]
    TranscendentTags = custom["TranscendentTags"]
    BlackListTags = custom["BlackListedTags"]
    BlackList = custom["BlackListedIds"]

    items_list = []

    # Build the list of items
    for item_data in data.get("data", []):
        # We only care about certain item types:
        if item_data["type"]["value"] not in [
            "glider", "backpack", "pickaxe", "wrap", "outfit", 
            "petcarrier", "emote"
        ]:
            continue

        # 'images' may or may not exist or be empty
        images_dict = item_data.get("images", {})
        icon_url = images_dict.get("icon")  # can be None if 'icon' not present

        # If there's no valid icon, skip
        if not icon_url:
            # You could log it for reference
            log(f"Skipping {item_data['id']} - no 'icon' in images.")
            continue
        out_path = f"icons/{item_data['id'].lower()}.png"
        if os.path.exists(out_path):
            continue
        print(item_data)
        if "series" in item_data and item_data["series"]["backendValue"].lower() in known_rarities:
            rarity_val = item_data["series"]["backendValue"].lower()
        elif item_data["rarity"]["value"] in known_rarities:
            rarity_val = item_data["rarity"]["value"].lower()
        else:
            rarity_val = item_data["rarity"]["backendValue"].split(":")[-1].lower()
        print(rarity_val)
        # Build an Item object
        i = Item()
        i.id = item_data["id"]
        i.name = item_data["name"].upper()
        
        # Convert "icon.png" => "icon_256.png"
        # e.g. if icon_url = "https://some.url/icon.png"
        # strip off extension, append _256
        base_no_ext = icon_url.rsplit(".", 1)[0]  # e.g. "https://some.url/icon"
        i.icon = base_no_ext + "_256.png"
        
        i.description = item_data["description"].split("\r\n")[0].upper()
        i.tags = item_data.get("gameplayTags", [])

        # Apply your custom logic for certain rarities
        if (i.id in MythicIds and i.id not in BlackList) or (
            not set(MythicTags).isdisjoint(i.tags) 
            and set(BlackListTags).isdisjoint(i.tags)
        ):
            i.rarity = "mythic"
        elif (i.id in ExoticIds and i.id not in BlackList) or (
            not set(ExoticTags).isdisjoint(i.tags) 
            and set(BlackListTags).isdisjoint(i.tags)
        ):
            i.rarity = "exotic"
        elif (i.id in TranscendentIds and i.id not in BlackList) or (
            not set(TranscendentTags).isdisjoint(i.tags) 
            and set(BlackListTags).isdisjoint(i.tags)
        ):
            i.rarity = "transcendent"
        else:
            i.rarity = rarity_val

        items_list.append(i)

    # Create icons in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda itm: CreateIcon(itm, design), items_list)

    log("Done generating icons.")
