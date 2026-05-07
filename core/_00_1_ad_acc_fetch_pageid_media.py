"""
_00_1_ad_acc_fetch_pageid_media.py

Reads core ingestion CSV(s) from data/first_bulk/
Fetches slow media assets separately:
- video direct url + thumbnail (via creative_id)
- fallback image
- IG media

Outputs enriched CSV(s) into:
data/first_bulk_media/
"""

import os
import json
import requests
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

GRAPH_VERSION = "v24.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

INPUT_DIR = "data/first_bulk"
OUTPUT_DIR = "data/first_bulk_media"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# Helpers
# =========================
def safe_get(url, params):
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    except requests.RequestException:
        return None

    except ValueError:
        return None


def fetch_video(video_id):
    if pd.isna(video_id) or not video_id:
        return None, None

    data = safe_get(
        f"{BASE_URL}/{video_id}",
        {
            "fields": "source,thumbnails",
            "access_token": ACCESS_TOKEN
        }
    )

    if not data:
        return None, None

    video_url = data.get("source")

    thumb_url = None
    thumbs = data.get("thumbnails", {}).get("data", [])

    for t in thumbs:
        if t.get("is_preferred"):
            thumb_url = t.get("uri")
            break

    return video_url, thumb_url


def fetch_video_from_creative(creative_id):
    if pd.isna(creative_id) or not creative_id:
        return None, None, None, None

    data = safe_get(
        f"{BASE_URL}/{creative_id}",
        {
            "fields": "object_story_spec{video_data{title,video_id}}",
            "access_token": ACCESS_TOKEN
        }
    )

    if not data:
        return None, None, None, None

    video_data = (
        data.get("object_story_spec", {})
        .get("video_data", {})
    )

    video_id = video_data.get("video_id")
    video_title = video_data.get("title")

    if not video_id:
        return None, None, None, video_title

    video_url, video_thumb = fetch_video(video_id)

    return video_id, video_title, video_url, video_thumb


def fetch_fallback_image(ad_id, ad_account_id):
    if pd.isna(ad_id) or not ad_id:
        return None

    data = safe_get(
        f"{BASE_URL}/{ad_id}",
        {
            "fields": "creative{id,asset_feed_spec{images{hash}}}",
            "access_token": ACCESS_TOKEN
        }
    )

    if not data:
        return None

    imgs = (
        data.get("creative", {})
        .get("asset_feed_spec", {})
        .get("images", [])
    )

    if not imgs:
        return None

    img_hash = imgs[0].get("hash")

    if not img_hash:
        return None

    data2 = safe_get(
        f"{BASE_URL}/{ad_account_id}/adimages",
        {
            "hashes": json.dumps([img_hash]),
            "fields": "url",
            "access_token": ACCESS_TOKEN
        }
    )

    if not data2:
        return None

    rows = data2.get("data", [])
    if not rows:
        return None

    return rows[0].get("url")


def fetch_ig_media(creative_id, creative_thumbnail_url):
    if pd.isna(creative_id) or not creative_id:
        return None, None, None, None

    data = safe_get(
        f"{BASE_URL}/{creative_id}",
        {
            "fields": "effective_instagram_media_id,source_instagram_media_id",
            "access_token": ACCESS_TOKEN
        }
    )

    if not data:
        return None, None, None, None

    ig_id = (
        data.get("effective_instagram_media_id")
        or data.get("source_instagram_media_id")
    )

    if not ig_id:
        return None, None, None, None

    data2 = safe_get(
        f"{BASE_URL}/{ig_id}",
        {
            "fields": "media_url,media_type,thumbnail_url",
            "access_token": ACCESS_TOKEN
        }
    )

    if not data2:
        return None, None, None, None

    media_type = data2.get("media_type")

    if media_type == "VIDEO":
        return (
            media_type,
            None,
            data2.get("media_url"),
            data2.get("thumbnail_url") or creative_thumbnail_url
        )

    return (
        media_type,
        data2.get("media_url"),
        None,
        None
    )


# =========================
# Main
# =========================
def enrich_file(path):
    df = pd.read_csv(path)

    for col in [
        "creative_video_id",
        "creative_video_title",
        "creative_video_url",
        "creative_video_thumbnail",
        "creative_image2_url",
        "ig_media_type",
        "ig_image_url",
        "ig_video_url",
        "ig_thumbnail_url",
    ]:
        if col not in df.columns:
            df[col] = None

    seen_video = {}
    seen_fallback = {}
    seen_ig = {}

    save_every = 2000

    for idx, row in tqdm(
        df.iterrows(),
        total=len(df),
        desc=os.path.basename(path)
    ):

        ad_id = row.get("ad_id")
        ad_account_id = row.get("ad_account_id")
        creative_id = row.get("creative_id")
        creative_image_url = row.get("creative_image_url")
        creative_thumbnail_url = row.get("creative_thumbnail_url")

        # =========================
        # VIDEO via creative_id
        # =========================
        if pd.notna(creative_id):

            if creative_id not in seen_video:
                seen_video[creative_id] = fetch_video_from_creative(
                    creative_id
                )

            (
                v_id,
                v_title,
                v_url,
                v_thumb
            ) = seen_video[creative_id]

            df.at[idx, "creative_video_id"] = v_id
            df.at[idx, "creative_video_title"] = v_title
            df.at[idx, "creative_video_url"] = v_url
            df.at[idx, "creative_video_thumbnail"] = v_thumb

        # =========================
        # FALLBACK IMAGE
        # =========================
        if pd.isna(creative_image_url) or not creative_image_url:

            if ad_id not in seen_fallback:
                seen_fallback[ad_id] = fetch_fallback_image(
                    ad_id,
                    ad_account_id
                )

            df.at[idx, "creative_image2_url"] = seen_fallback[ad_id]

        # =========================
        # IG MEDIA
        # =========================
        if pd.notna(creative_id):

            if creative_id not in seen_ig:
                seen_ig[creative_id] = fetch_ig_media(
                    creative_id,
                    creative_thumbnail_url
                )

            (
                media_type,
                ig_img,
                ig_vid,
                ig_thumb
            ) = seen_ig[creative_id]

            df.at[idx, "ig_media_type"] = media_type
            df.at[idx, "ig_image_url"] = ig_img
            df.at[idx, "ig_video_url"] = ig_vid
            df.at[idx, "ig_thumbnail_url"] = ig_thumb

        if (idx + 1) % save_every == 0:
            out_tmp = os.path.join(
                OUTPUT_DIR,
                os.path.basename(path)
            )

            df.to_csv(out_tmp, index=False)
            tqdm.write(f"[SAVE] {idx + 1} rows saved")

    out = os.path.join(
        OUTPUT_DIR,
        os.path.basename(path)
    )

    df.to_csv(out, index=False)
    print(f"Saved → {out}")


def main():
    files = [
        os.path.join(INPUT_DIR, f)
        for f in os.listdir(INPUT_DIR)
        if f.endswith(".csv")
    ]

    for file in files:
        enrich_file(file)


if __name__ == "__main__":
    main()