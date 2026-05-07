"""
_00_3_s3_asset_upload.py

Minimal pipeline:
1. Read enriched CSV from data/first_bulk_media/
2. Download image/video from URLs
3. Rename using ad_id
4. Upload to S3

Requirements:
pip install boto3 pandas requests python-dotenv
"""

import os
import mimetypes
import requests
import pandas as pd
import boto3
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# =========================
# ENV
# =========================
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = "data/ads_images_videos" 

INPUT_DIR = "data/first_bulk_media"

# =========================
# S3 Client
# =========================
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION
)


# =========================
# Helpers
# =========================
def get_ext(url, fallback=".bin"):
    ext = os.path.splitext(url.split("?")[0])[1].lower()

    if ext:
        return ext

    guess = mimetypes.guess_extension(
        mimetypes.guess_type(url)[0] or ""
    )

    return guess or fallback


def download_bytes(url):
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.content
    except requests.RequestException:
        print(f"Error downloading {url}")
        return None


def upload_bytes(data, key):
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=data
    )


#def process_asset(url, ad_id, folder, suffix=""):
def process_asset(url, ad_id, ad_account_id, folder, suffix=""):
    if pd.isna(url) or not url:
        return

    data = download_bytes(url)
    if not data:
        return

    ext = get_ext(url)

    filename = f"{ad_id}{suffix}{ext}"
    #key = f"{folder}/{filename}"
    #key = f"{S3_PREFIX}/{folder}/{filename}"
    key = f"{S3_PREFIX}/{ad_account_id}/{folder}/{filename}"

    upload_bytes(data, key)


# =========================
# Main per CSV
# =========================
def process_file(path):
    df = pd.read_csv(path)

    for _, row in tqdm(df.iterrows(), total=len(df), desc=os.path.basename(path)):

        ad_id = row.get("ad_id")
        ad_account_id = row.get("ad_account_id")

        # Main image
        process_asset(
            row.get("creative_image_url"),
            ad_id,
            ad_account_id,
            "images"
        )

        # Fallback image
        process_asset(
            row.get("creative_image2_url"),
            ad_id,
            ad_account_id,
            "images",
            "_alt"
        )

        # Thumbnail
        process_asset(
            row.get("creative_thumbnail_url"),
            ad_id,
            ad_account_id,
            "thumbnails"
        )

        # Video thumbnail
        process_asset(
            row.get("creative_video_thumbnail"),
            ad_id,
            ad_account_id,
            "thumbnails",
            "_video"
        )

        # Video
        process_asset(
            row.get("creative_video_url"),
            ad_id,
            ad_account_id,
            "videos"
        )

        # IG image
        process_asset(
            row.get("ig_image_url"),
            ad_id,
            ad_account_id,
            "images",
            "_ig"
        )

        # IG video
        process_asset(
            row.get("ig_video_url"),
            ad_id,
            ad_account_id,
            "videos",
            "_ig"
        )

        # IG thumb
        process_asset(
            row.get("ig_thumbnail_url"),
            ad_id,
            ad_account_id,
            "thumbnails",
            "_ig"
        )


def main():
    files = [
        os.path.join(INPUT_DIR, f)
        for f in os.listdir(INPUT_DIR)
        if f.endswith(".csv")
    ]

    for file in files:
        process_file(file)


if __name__ == "__main__":
    main()