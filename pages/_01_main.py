# pages/_01_main.py

import streamlit as st
import pandas as pd
import numpy as np
import boto3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ======================================================
# ENV
# ======================================================
load_dotenv()

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")

S3_INPUT = "data/5_data_cleaning/act_379859374796069_with_pages_final_industry_benchmarked_clean.csv"

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="AdsVault",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================================
# PATH
# ======================================================
ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# ======================================================
# CSS
# ======================================================
st.markdown("""
<style>

/* ======================================================
GLOBAL
====================================================== */

html, body, [class*="css"]{
    font-family: Inter, sans-serif;
}

.block-container{
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
    padding-left: 32px !important;
    padding-right: 32px !important;
    max-width: 1650px;
}

/* ======================================================
BACKGROUND
====================================================== */

.stApp{
    background:
    radial-gradient(circle at top left, rgba(212,175,55,0.06), transparent 22%),
    radial-gradient(circle at top right, rgba(212,175,55,0.04), transparent 18%),
    #060b14;
    color: white;
}

/* ======================================================
TEXT
====================================================== */

h1,h2,h3,h4{
    letter-spacing:-0.02em;
}

p, span, label{
    color:#d1d5db;
}

/* ======================================================
INPUT
====================================================== */

div[data-baseweb="input"]{
    background:#0b1220 !important;
    border:1px solid rgba(212,175,55,0.12) !important;
    border-radius:14px !important;
}

div[data-baseweb="input"]:focus-within{
    border:1px solid rgba(212,175,55,0.45) !important;
    box-shadow:0 0 0 1px rgba(212,175,55,0.18);
}

/* ======================================================
BUTTON
====================================================== */

.stButton > button{
    background:linear-gradient(
        135deg,
        #8B6B1F,
        #D4AF37
    ) !important;

    color:white !important;
    border:none !important;
    border-radius:12px !important;
    height:44px;
    font-weight:600;
}

.stButton > button:hover{
    filter:brightness(1.05);
}

/* ======================================================
METRICS
====================================================== */

div[data-testid="stMetric"]{
    background:linear-gradient(
        180deg,
        rgba(17,24,39,0.96),
        rgba(10,14,22,1)
    );

    border:1px solid rgba(212,175,55,0.12);

    padding:18px;
    border-radius:18px;

    box-shadow:
    0 8px 30px rgba(0,0,0,0.22);
}

/* ======================================================
TOP CARD V2
====================================================== */

.hero-img{
    width:100%;
    height:260px;

    object-fit:cover;

    border-radius:14px;

    display:block;
}

.card-top{
    display:flex;

    align-items:center;

    justify-content:space-between;

    margin-bottom:12px;
}

.score-text{
    font-size:36px;
    font-weight:800;
    color:#F5D76E;
}

.meta-block{
    margin-top:14px;
}

.meta-row{
    display:flex;

    align-items:center;

    justify-content:space-between;

    gap:10px;

    padding:7px 0;

    border-bottom:1px solid rgba(255,255,255,0.04);
}

.meta-label{
    font-size:13px;
    color:#94A3B8;
    font-weight:500;
}

.meta-value{
    font-size:13px;
    color:white;
    text-align:right;
}

.card-section-title{
    font-size:13px;
    font-weight:700;
    margin-top:18px;
    margin-bottom:10px;
    color:white;
}

.body-box{
    background:rgba(255,255,255,0.03);

    border:1px solid rgba(255,255,255,0.04);

    border-radius:12px;

    padding:12px;

    font-size:13px;

    line-height:1.6;

    color:#d1d5db;
}
            
/* ======================================================
BADGES
====================================================== */

.small-badge{
    display:inline-block;

    padding:5px 10px;

    border-radius:999px;

    font-size:11px;
    font-weight:700;

    margin-right:6px;
}

/* FIRST TIER */

.badge-first{
    background:rgba(34,197,94,0.12);
    border:1px solid rgba(34,197,94,0.28);
    color:#4ADE80;
}

/* SECOND TIER */

.badge-second{
    background:rgba(212,175,55,0.12);
    border:1px solid rgba(212,175,55,0.25);
    color:#F5D76E;
}

/* THIRD TIER */

.badge-third{
    background:rgba(148,163,184,0.10);
    border:1px solid rgba(148,163,184,0.22);
    color:#CBD5E1;
}

/* ======================================================
TABLES
====================================================== */

[data-testid="stDataFrame"]{
    border:1px solid rgba(212,175,55,0.12);
    border-radius:18px;
    overflow:hidden;
}

/* ======================================================
PROGRESS
====================================================== */

.stProgress > div > div > div > div{
    background:linear-gradient(
        90deg,
        #8B6B1F,
        #D4AF37,
        #F5D76E
    );
}

/* ======================================================
SECTION TITLES
====================================================== */

.tbl-title{
    font-size:24px;
    font-weight:700;
    margin-bottom:12px;
    letter-spacing:-0.02em;
}

/* ======================================================
HORIZONTAL SCROLL ADS
====================================================== */

.scroll-container{
    display:flex;

    overflow-x:auto;

    gap:16px;

    padding-top:6px;
    padding-bottom:10px;

    scroll-behavior:smooth;
}

.scroll-container::-webkit-scrollbar{
    height:8px;
}

.scroll-container::-webkit-scrollbar-track{
    background:#0b1220;
    border-radius:999px;
}

.scroll-container::-webkit-scrollbar-thumb{
    background:rgba(212,175,55,0.35);
    border-radius:999px;
}

.similar-card{
    min-width:240px;
    max-width:240px;

    background:linear-gradient(
        180deg,
        rgba(17,24,39,0.96),
        rgba(10,14,22,1)
    );

    border:1px solid rgba(212,175,55,0.12);

    border-radius:14px;

    overflow:hidden;

    flex-shrink:0;

    box-shadow:
    0 8px 20px rgba(0,0,0,0.25);
}

.similar-meta{
    padding:10px;
}

.similar-title{
    font-size:13px;
    font-weight:600;
    color:white;
    margin-bottom:6px;
}

.similar-sub{
    font-size:11px;
    color:#94a3b8;
}
            
/* ======================================================
TIP BOX
====================================================== */

.tip-box{
    margin-top:12px;

    padding:14px;

    border-radius:16px;

    background:rgba(17,24,39,0.95);

    border:1px solid rgba(212,175,55,0.12);

    color:#d1d5db;
}

            
            
/* ======================================================
STREAMLIT CONTAINER OVERRIDE
====================================================== */

[data-testid="stVerticalBlockBorderWrapper"]{
background:linear-gradient(
    180deg,
    rgba(17,24,39,0.96),
    rgba(10,14,22,1)
) !important;

border:1px solid rgba(212,175,55,0.14) !important;

border-radius:18px !important;

padding:14px !important;

overflow:hidden !important;

box-shadow:
0 10px 30px rgba(0,0,0,0.25) !important;
            
</style>
""", unsafe_allow_html=True)


# ======================================================
# S3
# ======================================================
@st.cache_resource(show_spinner=False)
def get_s3():
    return boto3.client(
        "s3",
        region_name=AWS_DEFAULT_REGION
    )

# ======================================================
# LOAD DATA
# ======================================================
@st.cache_data(show_spinner=False)
def load_data():
    obj = get_s3().get_object(
        Bucket=S3_BUCKET,
        Key=S3_INPUT
    )
    return pd.read_csv(obj["Body"])

# ======================================================
# LOAD RAG
# ======================================================
@st.cache_resource(show_spinner=False)
def load_rag(df):
    from core._06_rag import RAGRetriever
    return RAGRetriever(df.to_dict(orient="records"))

# ======================================================
# HELPERS
# ======================================================
def safe(x):
    if pd.isna(x):
        return ""
    return str(x)


def presign(key, expiry=86400):
    if not key:
        return None

    return get_s3().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key
        },
        ExpiresIn=expiry
    )


def s3_exists(key):
    try:
        get_s3().head_object(
            Bucket=S3_BUCKET,
            Key=key
        )
        return True
    except:
        return False


def first_existing(keys):
    for key in keys:
        if s3_exists(key):
            return key
    return None


def get_media_url(row):

    ad_id = safe(row.get("ad_id"))
    ad_account_id = safe(row.get("ad_account_id"))

    if not ad_id or not ad_account_id:
        return None

    base = f"data/ads_images_videos/{ad_account_id}"

    candidates = [
        f"{base}/images/{ad_id}_ig.jpg",
        f"{base}/images/{ad_id}_ig.png",
        f"{base}/images/{ad_id}.jpg",
        f"{base}/images/{ad_id}.png",
        f"{base}/thumbnails/{ad_id}_video.jpg",
        f"{base}/thumbnails/{ad_id}_video.png",
        f"{base}/images/{ad_id}_alt.jpg",
        f"{base}/images/{ad_id}_alt.png",
    ]

    key = first_existing(candidates)

    if not key:
        return None

    return presign(key)


def tier_name(score):
    if score >= 60:
        return "First Tier"
    elif score >= 45:
        return "Second Tier"
    return "Third Tier"

def tier_class(score):

    if score >= 60:
        return "badge-first"

    elif score >= 45:
        return "badge-second"

    return "badge-third"


def top_category(results):
    vals = [
        safe(r.get("page_category"))
        for r in results
        if safe(r.get("page_category"))
    ]

    if not vals:
        return "-"

    return pd.Series(vals).value_counts().index[0]


# ======================================================
# LOAD
# ======================================================
df = load_data()

with st.spinner("Loading RAG engine..."):
    rag = load_rag(df)

total_ads = df["ad_id"].nunique()

# ======================================================
# HEADER
# ======================================================
st.markdown("# AdsVault")
st.markdown("""
<div style="
height:1px;
background:linear-gradient(
90deg,
rgba(212,175,55,0),
rgba(212,175,55,0.5),
rgba(212,175,55,0)
);
margin-bottom:20px;
"></div>
""", unsafe_allow_html=True)
c1, c2 = st.columns([8,1])

with c1:
    query = st.text_input(
        "",
        placeholder="pizza",
        label_visibility="collapsed"
    )

with c2:
    run = st.button(
        "Search",
        use_container_width=True
    )

# ======================================================
# DEFAULT VIEW
# ======================================================
if not run or not query.strip():

    st.subheader("Full Ads Table")

    st.dataframe(
        df.head(300),
        use_container_width=True,
        height=860
    )

    st.stop()

# ======================================================
# SEARCH
# ======================================================
with st.spinner("Searching..."):
    results = rag.retrieve_tiered(query, k=15) # k=10 default

if not results:
    st.warning("No results found.")
    st.stop()

# ======================================================
# KPI
# ======================================================
scores = [r["score"] for r in results]
avg_score = round(np.mean(scores), 1)

brands = len(set(
    safe(r.get("page_name"))
    for r in results
    if safe(r.get("page_name"))
))

st.markdown(f"## Search Query: `{query}`")

k0,k1,k2,k3 = st.columns(4)

k0.metric("Total Ads (Benchmarked)", f"{total_ads:,}")
k1.metric("Ads Found", f"{len(results):,}")
k2.metric("Avg Score", f"{avg_score}")
k3.metric("Best Tier", tier_name(max(scores)))
#k4.metric("Top Category", top_category(results))
#k5.metric("Brands", f"{brands:,}")

# ======================================================
# TOP 3
# ======================================================
st.markdown("## Top 3 Highest Ranked Ads")

#cols = st.columns(3)
cols = st.columns([1,1,1], gap="large")

for col, r, idx in zip(cols, results[:3], [1,2,3]):

    with col:
        with st.container(border=True):

            st.markdown(f"""
<div style="
display:flex;
align-items:center;
justify-content:space-between;
margin-bottom:10px;
">

<div style="
font-size:30px;
font-weight:700;
color:#F5D76E;
">
{round(r['score'],1)}
</div>

<div class="small-badge {tier_class(r['score'])}">
{tier_name(r['score'])}
</div>

</div>
""", unsafe_allow_html=True)

            media = get_media_url(r)

            # if media:
            #     st.image(media, use_container_width=True)
            if media:
                st.markdown(f"""
                <div style="
                height:450px;
                overflow:hidden;
                border-radius:14px;
                margin-bottom:12px;
                ">
                    <img src="{media}" style="
                        width:100%;
                        height:100%;
                        object-fit:cover;
                    ">
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
<div style="
color:#F5D76E;
font-size:16px;
font-weight:700;
margin-top:10px;
margin-bottom:3px;
">
{safe(r.get('ad_account_name'))}
</div>
""", unsafe_allow_html=True)

            st.markdown(f"""
<div style="
color:#E5E7EB;
font-size:14px;
font-weight:500;
margin-bottom:6px;
">
{safe(r.get('page_name'))} | {safe(r.get('page_category'))}
</div>
""", unsafe_allow_html=True)

            campaign = safe(r.get("campaign_name"))

            if len(campaign) > 80:
                campaign = campaign[:80] + "..."

            adset = safe(r.get("adset_name"))

            if len(adset) > 50:
                adset = adset[:50] + "..."

            ad = safe(r.get("ad_name"))

            if len(ad) > 80:
                ad = ad[:80] + "..."



            body = safe(r.get("ad_body"))

            if len(body) > 1000:
                body = body[:1000] + "..."

            body = body.replace("\n", "<br>")


            status = safe(r.get("ad_status"))


            # ======================================================
            # PSYCHOGRAPHICS
            # ======================================================

            interests_raw = safe(r.get("interests"))
            behaviors_raw = safe(r.get("behaviors"))

            interest_list = [
                x.strip()
                for x in interests_raw.split(",")
                if x.strip()
            ]

            behavior_list = [
                x.strip()
                for x in behaviors_raw.split(",")
                if x.strip()
            ]

            if len(interest_list) > 4:
                interests = (
                    ", ".join(interest_list[:4])
                    + f" +{len(interest_list)-4} more"
                )
            else:
                interests = ", ".join(interest_list)

            if len(behavior_list) > 3:
                behaviors = (
                    ", ".join(behavior_list[:3])
                    + f" +{len(behavior_list)-3} more"
                )
            else:
                behaviors = ", ".join(behavior_list)

            gender = safe(r.get("genders"))
            countries = safe(r.get("countries"))

            age_min = r.get("age_min")
            age_max = r.get("age_max")

            if pd.notna(age_min):
                age_min = int(float(age_min))
            else:
                age_min = None

            if pd.notna(age_max):
                age_max = int(float(age_max))
            else:
                age_max = None

            if age_min is not None or age_max is not None:
                age_text = f"{age_min} — {age_max}"
            else:
                age_text = ""


            psychographic_html = ""

            if interests:
                psychographic_html += f"""
<div class="meta-row">
    <div class="meta-label">Interests</div>
    <div class="meta-value">{interests}</div>
</div>
                """

            if behaviors:
                psychographic_html += f"""
<div class="meta-row">
    <div class="meta-label">Behaviors</div>
    <div class="meta-value">{behaviors}</div>
</div>
                """

            if gender:
                psychographic_html += f"""
<div class="meta-row">
    <div class="meta-label">Gender</div>
    <div class="meta-value">{gender}</div>
</div>
                """

            if age_text:
                psychographic_html += f"""
<div class="meta-row">
    <div class="meta-label">Age</div>
    <div class="meta-value">{age_text}</div>
</div>
                """

            if countries:
                psychographic_html += f"""
<div class="meta-row">
    <div class="meta-label">Countries</div>
    <div class="meta-value">{countries}</div>
</div>
                """
                


            start_date = safe(r.get("campaign_start_date"))
            end_date = safe(r.get("campaign_end_date"))

            if end_date:
                date_text = f"{start_date} — {end_date}"
            else:
                date_text = start_date


            ## Result, Spend and CPR Cards 
            results_val = float(r.get("results", 0))
            spend_val = float(r.get("spend", 0))
            cpr_val = float(r.get("cost_per_results", 0))

            results_pct = min(results_val / 150000, 1.0)
            spend_pct = min(spend_val / 1000, 1.0)
            cpr_pct = min(cpr_val / 5, 1.0)

            st.markdown(f"""

            <div style="
            display:grid;
            grid-template-columns:1fr 1fr 1fr;
            gap:12px;
            margin-top:18px;
            ">

            <!-- RESULTS -->

            <div class="body-box">

            <div class="meta-label">
            Results
            </div>

            <div style="
            font-size:18px;
            font-weight:800;
            margin-top:6px;
            margin-bottom:10px;
            ">
            {results_val:,.0f}
            </div>

            <div style="
            height:6px;
            background:rgba(255,255,255,0.06);
            border-radius:999px;
            overflow:hidden;
            ">

            <div style="
            width:{results_pct*100}%;
            height:100%;
            background:linear-gradient(
            90deg,
            #16A34A,
            #4ADE80
            );
            ">
            </div>

            </div>

            </div>

            <!-- SPEND -->

            <div class="body-box">

            <div class="meta-label">
            Spend
            </div>

            <div style="
            font-size:18px;
            font-weight:800;
            margin-top:6px;
            margin-bottom:10px;
            ">
            RM {spend_val:,.2f}
            </div>

            <div style="
            height:6px;
            background:rgba(255,255,255,0.06);
            border-radius:999px;
            overflow:hidden;
            ">

            <div style="
            width:{spend_pct*100}%;
            height:100%;
            background:linear-gradient(
            90deg,
            #D4AF37,
            #F5D76E
            );
            ">
            </div>

            </div>

            </div>

            <!-- CPR -->

            <div class="body-box">

            <div class="meta-label">
            CPR
            </div>

            <div style="
            font-size:18px;
            font-weight:800;
            margin-top:6px;
            margin-bottom:10px;
            ">
            RM {cpr_val:,.3f}
            </div>

            <div style="
            height:6px;
            background:rgba(255,255,255,0.06);
            border-radius:999px;
            overflow:hidden;
            ">

            <div style="
            width:{cpr_pct*100}%;
            height:100%;
            background:linear-gradient(
            90deg,
            #64748B,
            #CBD5E1
            );
            ">
            </div>

            </div>

            </div>

            </div>

            """, unsafe_allow_html=True)




            st.markdown(f"""

<div class="meta-block">

<div class="meta-row">
    <div class="meta-label">Campaign</div>
    <div class="meta-value">
        {campaign}
    </div>
</div>

<div class="meta-row">
    <div class="meta-label">Ad Set</div>
    <div class="meta-value">
        {adset}
    </div>
</div>

<div class="meta-row">
    <div class="meta-label">Ad</div>
    <div class="meta-value">
        {ad}
    </div>
</div>

<div class="meta-row">
    <div class="meta-label">Result Type</div>
    <div class="meta-value">
        {safe(r.get("result_type"))}
    </div>
</div>

<div class="meta-row">
    <div class="meta-label">Dates</div>
    <div class="meta-value">
        {date_text}
    </div>
</div>

<div class="meta-row">
    <div class="meta-label">Ad Status</div>
    <div class="meta-value">
        {status}
    </div>
</div>

<div class="meta-row">
    <div class="meta-label">Psychographics</div>
    <div class="meta-value">
        Audience Targeting
    </div>
</div>
{psychographic_html}


</div>

<div class="card-section-title">
Ad Body
</div>

<div class="body-box">
{body}
</div>

""", unsafe_allow_html=True)

       

# ======================================================
# OTHER SIMILAR ADS
# ======================================================
st.markdown("## Other Similar Ads")

cards_html = '<div class="scroll-container">'

for r in results[3:]:

    media = get_media_url(r)

    score = round(r["score"], 1)

    brand = safe(r.get("page_name"))

    results_val = safe(r.get("results"))

    cpr = safe(r.get("cost_per_results"))

    image_html = ""

    if media:
        image_html = f'''
<div style="
    height:120px;
    overflow:hidden;
">
    <img src="{media}" style="
        width:100%;
        height:100%;
        object-fit:cover;
        display:block;
    ">
</div>
'''

    cards_html += f"""
<div class="similar-card">

{image_html}

<div class="similar-meta">

<div class="similar-title">
    {brand}
</div>

<div class="similar-sub">
    Score: {score}
</div>

<div class="similar-sub">
    Results: {results_val}
</div>

<div class="similar-sub">
    CPR: RM {cpr}
</div>

</div>

</div>
"""

cards_html += "</div>"

st.markdown(cards_html, unsafe_allow_html=True)

# ======================================================
# TABLE
# ======================================================
st.markdown('<div class="tbl-title">Top Ranked Ads</div>', unsafe_allow_html=True)

rows = []

for i, r in enumerate(results, start=1):

    rows.append({
        "Rank": i,
        "Preview": get_media_url(r),
        "Score": round(r["score"],1),
        "Tier": tier_name(r["score"]),
        "Ad Account": safe(r.get("ad_account_name")),
        "Start Date": safe(r.get("campaign_start_date")),
        "End Date": safe(r.get("campaign_end_date")),
        "Campaign": safe(r.get("campaign_name")),
        "Objective": safe(r.get("campaign_objective")),
        "Campaign Status": safe(r.get("campaign_status")),
        "Ad Set": safe(r.get("adset_name")),
        "Adset Status": safe(r.get("adset_status")),
        "Ad Name / Title": safe(r.get("ad_name")),
        "Ad Status": safe(r.get("ad_status")),
        "Ad Body": safe(r.get("ad_body")),
        "Industry": safe(r.get("industry")),
        "Page Name": safe(r.get("page_name")),
        "Page Category": safe(r.get("page_category")),
        "Page Description": safe(r.get("page_description")),
        "Page About": safe(r.get("page_about")),
        "Page Website": safe(r.get("page_website")),
        "Interests Target": safe(r.get("interests")),
        "Behaviors Target": safe(r.get("behaviors")),
        "Gender": safe(r.get("genders")),
        "Age Min": safe(r.get("age_min")),
        "Age Max": safe(r.get("age_max")),
        "Countries": safe(r.get("countries")),
        "Result Type": safe(r.get("result_type")),
        "Results": safe(r.get("results")),
        "Cost (RM)": safe(r.get("spend")),
        "Cost Per Results (RM)": round(r.get("cost_per_results"),3),
    })

table_df = pd.DataFrame(rows)

st.data_editor(
    table_df,
    use_container_width=True,
    height=470,
    hide_index=True,
    disabled=True,
    column_config={
        "Preview": st.column_config.ImageColumn(
            "Preview",
            width="small"
        ),
        "Rank": st.column_config.NumberColumn(
            "Rank",
            width="small"
        ),
        "Score": st.column_config.NumberColumn(
            "Score",
            format="%.1f"
        ),
    }
)

# ======================================================
# FULL ADS TABLE
# ======================================================
with st.expander("View Full Ads Database"):
    #st.divider()
    st.markdown('<div class="tbl-title">Full Ads Table</div>', unsafe_allow_html=True)

    full_cols = [
        "ad_account_name",
        "campaign_name",
        "adset_name",
        "ad_name",
        "page_name",
        "page_category",
        "results",
        "cost_per_results",
        "spend",
        "date_start",
        "date_stop"
    ]

    full_cols = [c for c in full_cols if c in df.columns]

    st.dataframe(
        df[full_cols],
        use_container_width=True,
        height=750
    )


# ======================================================
# FOOTER
# ======================================================
st.markdown(
    f"""
    <div class="tip-box">
    Tip: {tier_name(max(scores))} results are the strongest results for "{query}".
    </div>
    """,
    unsafe_allow_html=True
)