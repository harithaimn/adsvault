"""
Implemented with image url ingest (all kinds of images/videos)
Implemented with adset psychographics ingestion too.

Updated -- 22.4.26 , 11.57am:
Fast core ingestion:
- No extra image/video enrichment API calls
- Keeps direct creative fields returned in ads query
- Keeps psychographics
- Keeps skip bad campaign/adset handling
- Keeps checkpoint saves


"""

import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timezone
from tqdm import tqdm

load_dotenv()

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_DATE_SINCE = os.getenv("META_DATE_SINCE")

GRAPH_VERSION = "v24.0"

#AD_ACCOUNT_ID = "act_379859374796069" # # Decoris | CLIENTS #3 | Malaysia [IOC]
AD_ACCOUNT_ID = None

BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


# =========================
# Extraction helpers (UNCHANGED)
# =========================
def extract_page_id(creative):
    if not creative:
        return None

    eos = creative.get("effective_object_story_id")
    if eos and "_" in eos:
        return eos.split("_")[0]

    oss = creative.get("object_story_spec")
    if oss:
        return oss.get("page_id")

    return None


def extract_results(results_block):
    if not isinstance(results_block, list) or not results_block:
        return None, 0

    first = results_block[0]
    indicator = first.get("indicator")

    values = first.get("values", [])
    if not values:
        return indicator, 0

    try:
        value = float(values[0].get("value", 0))
    except (TypeError, ValueError):
        value = 0

    return indicator, value


def extract_cpr(cpr_block):
    if not isinstance(cpr_block, list) or not cpr_block:
        return None

    first = cpr_block[0]
    values = first.get("values", [])
    if not values:
        return None

    try:
        return float(values[0].get("value"))
    except (TypeError, ValueError):
        return None


def extract_leads(actions):
    if not isinstance(actions, list):
        return 0

    for a in actions:
        if a.get("action_type") == "onsite_conversion.lead_grouped":
            try:
                return int(float(a.get("value", 0)))
            except:
                return 0

    return 0


def extract_cpl(costs):
    if not isinstance(costs, list):
        return None

    for c in costs:
        if c.get("action_type") == "onsite_conversion.lead_grouped":
            try:
                return float(c.get("value"))
            except:
                return None

    return None

date_since = META_DATE_SINCE
date_until = datetime.now(timezone.utc).date().isoformat()


# ========================
# ADSET PSYCHOGRAPHICS HELPER
# ========================

def parse_targeting(targeting):
    if not targeting:
        return {}

    flexible = targeting.get("flexible_spec", [])

    interests = []
    behaviors = []

    for spec in flexible:
        interests.extend(
            [x.get("name") for x in spec.get("interests", [])]
        )

        behaviors.extend(
            [x.get("name") for x in spec.get("behaviors", [])]
        )

    countries = (
        targeting.get("geo_locations", {})
                 .get("countries", [])
    )

    return {
        "age_min": targeting.get("age_min"),
        "age_max": targeting.get("age_max"),
        "genders": targeting.get("genders"),
        "countries": countries,
        "interests": list(set(interests)),
        "behaviors": list(set(behaviors)),
    }


# =========================
# API calls
# =========================
def fetch_ad_account_meta():

    url = f"{BASE_URL}/{AD_ACCOUNT_ID}"
    params = {
        "fields": "id,name,account_status",
        "access_token": ACCESS_TOKEN
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()


def fetch_all_campaigns():
    url = f"{BASE_URL}/{AD_ACCOUNT_ID}/campaigns"
    params = {
        "fields": "id,name,status,objective,start_time,stop_time",
        "limit": 100,
        "access_token": ACCESS_TOKEN
    }

    results = []
    while url:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()

        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return results


def fetch_all_adsets(campaign_id):
    url = f"{BASE_URL}/{campaign_id}/adsets"
    params = {
        "fields": "id,name,status",
        "limit": 100,
        "access_token": ACCESS_TOKEN
    }

    results = []
    while url:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()

        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return results


def fetch_all_ads(adset_id):
    url = f"{BASE_URL}/{adset_id}/ads"
    params = {
        "fields": (
            "id,name,status,"
            "creative{"
                "id,"
                "name,"
                "title,"
                "body,"
                "image_url,"
                "thumbnail_url,"
                "effective_object_story_id,"
                "object_story_spec{"
                    "page_id,"
                    "link_data{"
                        "call_to_action{type,value{link,link_caption}},"
                        "child_attachments{image_hash}"
                    "},"
                    "video_data{title,video_id}"
                "}"
            "},"
            f"insights.time_range({{'since':'{date_since}','until':'{date_until}'}})"
            "{date_start,date_stop,spend,results,cost_per_result,actions,cost_per_action_type}"
        ),
        "limit": 100,
        "access_token": ACCESS_TOKEN
    }

    results = []
    while url:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()

        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}

    return results

# =========================
# ADSET PSYCHOGRAPHICS
# =========================
def fetch_adset_psychographics(adset_id):
    url = f"{BASE_URL}/{adset_id}"

    params = {
        "fields": (
            "targeting,"
            "optimization_goal"
        ),
        "access_token": ACCESS_TOKEN
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()

        data = r.json()

        tgt = parse_targeting(data.get("targeting"))

        return {
            #"effective_status": data.get("effective_status"),
            "optimization_goal": data.get("optimization_goal"),

            "age_min": tgt.get("age_min"),
            "age_max": tgt.get("age_max"),
            "genders": tgt.get("genders"),
            "countries": tgt.get("countries"),
            "interests": tgt.get("interests"),
            "behaviors": tgt.get("behaviors"),
        }

    except requests.RequestException:
        return {}
    except ValueError:
        return {}


# =========================
# MAIN
# =========================
def main(account_id):   # Accept parameters for all ads account

    global AD_ACCOUNT_ID
    AD_ACCOUNT_ID = account_id
    
    account = fetch_ad_account_meta()
    campaigns = fetch_all_campaigns()

    rows = []

    """ Periodic checkpoint saves in CSV. """
    save_every = 2000

    os.makedirs("data/first_bulk", exist_ok=True)
    output_path = f"data/first_bulk/adacc_{AD_ACCOUNT_ID}.csv"
    

    for c in tqdm(campaigns, desc="Campaigns", unit="camp"):
        campaign_id = c.get("id")

        # adsets = fetch_all_adsets(campaign_id)
        """ Error handling. Skip bad campaigns """
        try:
            adsets = fetch_all_adsets(campaign_id)
        except requests.RequestException as e:
            tqdm.write(f"[WARN] Skip campaign {campaign_id}: {e}")
            continue

        for adset in tqdm(adsets, desc="Adsets", leave=False, unit="adset"):
            adset_id = adset.get("id")

            psycho = fetch_adset_psychographics(adset_id)

            #ads = fetch_all_ads(adset_id)
            """ Error handling. Skip bad adsets """
            try:
                ads = fetch_all_ads(adset_id)
            except requests.RequestException as e:
                tqdm.write(f"[WARN] Skip adset {adset_id}: {e}")
                continue

            for ad in ads:
                creative = ad.get("creative", {})
                page_id = extract_page_id(creative)


                object_story = creative.get("object_story_spec", {})

                link_data = object_story.get("link_data", {})
                cta = link_data.get("call_to_action", {})
                cta_value = cta.get("value", {})

                video_data = object_story.get("video_data", {})

                # # =========================
                # # VIDEO RESOLUTION
                # # =========================
                # video_id = video_data.get("video_id")
                # video_source = None
                # video_thumbnail = None

                # if video_id:
                #     try:
                #         resp = requests.get(
                #             f"{BASE_URL}/{video_id}",
                #             params={
                #                 "fields": "source,thumbnails",
                #                 "access_token": ACCESS_TOKEN
                #             },
                #             timeout=30

                #         )
                #         resp.raise_for_status()
                #         r = resp.json()

                #         video_source = r.get("source")

                #         thumbs = r.get("thumbnails", {}).get("data", [])
                #         for t in thumbs:
                #             if t.get("is_preferred"):
                #                 video_thumbnail = t.get("uri")
                #                 break

                #     except requests.RequestException:
                #         pass
                #     except ValueError:
                #         pass

                # # =========================
                # # CAROUSEL IMAGE
                # # =========================
                # carousel_default_url = None

                # children = link_data.get("child_attachments", [])

                # hashes = [
                #     x.get("image_hash")
                #     for x in children
                #     if x.get("image_hash")
                # ]

                # if hashes:
                #     try:
                #         resp = requests.get(
                #             f"{BASE_URL}/{AD_ACCOUNT_ID}/adimages",
                #             params={
                #                 "hashes": json.dumps([hashes[0]]),
                #                 "fields": "url",
                #                 "access_token": ACCESS_TOKEN
                #             },
                #             timeout=30
                #         )
                #         resp.raise_for_status()
                #         r = resp.json()

                #         data = r.get("data", [])
                #         if data:
                #             carousel_default_url = data[0].get("url")

                #     except requests.RequestException:
                #         pass
                #     except ValueError:
                #         pass

                # # =========================
                # # FALLBACK IMAGE
                # # =========================
                # creative_image2_url = None

                # if not creative.get("image_url"):
                #     try:
                #         resp = requests.get(
                #             f"{BASE_URL}/{ad.get('id')}",
                #             params={
                #                 "fields": "creative{id,asset_feed_spec{images{hash}}}",
                #                 "access_token": ACCESS_TOKEN
                #             },
                #             timeout=30
                #         )
                #         resp.raise_for_status()
                #         r = resp.json()

                #         imgs = (
                #             r.get("creative", {})
                #              .get("asset_feed_spec", {})
                #              .get("images", [])
                #         )

                #         if imgs:
                #             img_hash = imgs[0].get("hash")

                #             resp2 = requests.get(
                #                 f"{BASE_URL}/{AD_ACCOUNT_ID}/adimages",
                #                 params={
                #                     "hashes": json.dumps([img_hash]),
                #                     "fields": "url",
                #                     "access_token": ACCESS_TOKEN
                #                 },
                #                 timeout=30
                #             )
                #             resp2.raise_for_status()
                #             r2 = resp2.json()

                #             data = r2.get("data", [])
                #             if data:
                #                 creative_image2_url = data[0].get("url")

                #     except requests.RequestException:
                #         pass
                #     except ValueError:
                #         pass

                # # =========================
                # # IG MEDIA
                # # =========================
                # ig_media_type = None
                # ig_image_url = None
                # ig_video_url = None
                # ig_thumbnail_url = None

                # creative_id = creative.get("id")

                # if creative_id:
                #     try:
                #         resp = requests.get(
                #             f"{BASE_URL}/{creative_id}",
                #             params={
                #                 "fields": "effective_instagram_media_id,source_instagram_media_id",
                #                 "access_token": ACCESS_TOKEN
                #             },
                #             timeout=30
                #         )
                #         resp.raise_for_status()
                #         r = resp.json()

                #         ig_id = (
                #             r.get("effective_instagram_media_id")
                #             or r.get("source_instagram_media_id")
                #         )

                #         if ig_id:
                #             resp2 = requests.get(
                #                 f"{BASE_URL}/{ig_id}",
                #                 params={
                #                     "fields": "media_url,media_type,thumbnail_url",
                #                     "access_token": ACCESS_TOKEN
                #                 },
                #                 timeout=30
                #             )
                #             resp2.raise_for_status()
                #             r2 = resp2.json()

                #             ig_media_type = r2.get("media_type")

                #             if ig_media_type == "VIDEO":
                #                 ig_video_url = r2.get("media_url")
                #                 ig_thumbnail_url = (
                #                     r2.get("thumbnail_url")
                #                     or creative.get("thumbnail_url")
                #                 )
                #             else:
                #                 ig_image_url = r2.get("media_url")

                #     except requests.RequestException:
                #         pass
                #     except ValueError:
                #         pass

                for ins in ad.get("insights", {}).get("data", []):
                    result_type, result_value = extract_results(ins.get("results"))
                    cpr_value = extract_cpr(ins.get("cost_per_result"))

                    rows.append({
                        "ad_account_id": account.get("id"),
                        "ad_account_name": account.get("name"),
                        "ad_account_status": account.get("account_status"),

                        # Campaign
                        "campaign_id": campaign_id,
                        "campaign_name": c.get("name"),
                        "campaign_status": c.get("status"),
                        "campaign_objective": c.get("objective"),
                        "campaign_start_date": c.get("start_time"),
                        "campaign_end_date": c.get("stop_time"),

                        # Adset
                        "adset_id": adset_id,
                        "adset_name": adset.get("name"),
                        "adset_status": adset.get("status"),

                        # Adset Psychographics

                        "optimization_goal": psycho.get("optimization_goal"),

                        "age_min": psycho.get("age_min"),
                        "age_max": psycho.get("age_max"),
                        "genders": psycho.get("genders"),
                        "countries": psycho.get("countries"),
                        "interests": psycho.get("interests"),
                        "behaviors": psycho.get("behaviors"),


                        # Ad
                        "ad_id": ad.get("id"),
                        "ad_name": ad.get("name"),
                        "ad_status": ad.get("status"),

                        # Creative
                        "creative_id": creative.get("id"),
                        "ad_title": creative.get("title"),
                        "creative_name": creative.get("name"),
                        "ad_body": creative.get("body"),

                        # Page ID
                        "page_id": page_id,

                        # Creative image & thumbnail
                        "creative_image_url": creative.get("image_url"),
                        "creative_thumbnail_url": creative.get("thumbnail_url"),

                        # CTA
                        "creative_cta_type": cta.get("type"),
                        "creative_cta_link": cta_value.get("link"),
                        "creative_cta_link_caption": cta_value.get("link_caption"),

                        # # Video
                        "creative_video_title": video_data.get("title"),
                        #"creative_video_id": video_id,
                        # "creative_video_url": video_source,
                        # "creative_video_thumbnail": video_thumbnail,

                        # # Carousel Image
                        # "creative_carousel_default_url": carousel_default_url,
                        
                        # # For Creative that don't return image_url, we have a fallback query to get the image URL using creative ID + hash
                        # "creative_image2_url": creative_image2_url,

                        # # IG fields
                        # "ig_media_type": ig_media_type,
                        # "ig_image_url": ig_image_url,
                        # "ig_video_url": ig_video_url,
                        # "ig_thumbnail_url": ig_thumbnail_url,


                        "date_start": ins.get("date_start"),
                        "date_stop": ins.get("date_stop"),

                        "spend": ins.get("spend"),

                        # Results
                        "result_type": result_type,
                        "results": result_value,
                        "cost_per_results": cpr_value,

                        # Leads
                        "leads": extract_leads(ins.get("actions")),
                        "cost_per_lead": extract_cpl(ins.get("cost_per_action_type")),
                    })

                    if len(rows) % save_every == 0:
                        pd.DataFrame(rows).to_csv(output_path, index=False)
                        tqdm.write(f"[SAVE] {len(rows)} rows saved → {output_path}")

    df = pd.DataFrame(rows)
    #df.to_csv("adacc_with_insights.csv", index=False)
    # Output ad_account_id ads
    os.makedirs("data/first_bulk", exist_ok=True)

    output_path = f"data/first_bulk/adacc_{AD_ACCOUNT_ID}.csv"
    df.to_csv(output_path, index=False)

    #print(f"Saved {len(df)} rows → {output_path}")

    return output_path

# if __name__ == "__main__":
#     main()

if __name__ == "__main__":
    raise RuntimeError("Use main(account_id) via runner script")