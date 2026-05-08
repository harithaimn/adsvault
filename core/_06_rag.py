# This was with the Business Relevance ranking system.
# This was after 8.  i don't need this right now i think.  it's like  deteriorates my outputs.  6.5.2026, 5.47pm.


# core/_06_rag.py

from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np
import pandas as pd
import re
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

# ==============================
# ENV
# ==============================
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")

# ==============================
# S3 PATH
# ==============================
S3_INPUT = "data/5_data_cleaning/act_379859374796069_with_pages_final_industry_benchmarked_clean.csv"

# ==============================
# S3 CLIENT
# ==============================
s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION
)


class RAGRetriever:
    def __init__(self, ads: list[dict]):
        self.ads = ads
        #self.model = SentenceTransformer("all-MiniLM-L6-v2")
        #self.model = SentenceTransformer("BAAI/bge-m3") # Malay, mixed-language retrieval, slang. Not using this since this is big.

        #self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

        # Load embedding model that has been downloaded from core/_06_1_download_models.py
        self.model = SentenceTransformer(
            "./models/paraphrase-multilingual-MiniLM-L12-v2"
        )

        # Reranker
        #self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        # Load reranker model that has been downloaded from core/_06_1_download_models.py
        self.reranker = CrossEncoder(
            "./models/ms-marco-MiniLM-L-6-v2"
        )

        self.texts = [self._build_text(ad) for ad in ads]


        # BM25
        # tokenize texts (simple split is enough for now)
        self.tokenized_texts = [t.lower().split() for t in self.texts]

        # build BM25 index
        self.bm25 = BM25Okapi(self.tokenized_texts)


        cache_path = "core/embeddings.npy"

        need_build = True

        if os.path.exists(cache_path):
            emb = np.load(cache_path)
            if len(emb) == len(self.ads):
                self.embeddings = emb
                need_build = False
            else:
                os.remove(cache_path)

        if need_build:
            self.embeddings = self.model.encode(
                self.texts,
                batch_size=64,
                normalize_embeddings=True,
                show_progress_bar=True
            )
            np.save(cache_path, self.embeddings)

    # =====================================
    # HELPERS
    # =====================================

    def clean(self, x):
        if pd.isna(x):
            return ""
        return str(x).strip()
    
    # =====================================
    # 5. BETTER PREPROCESSING
    # =====================================
    def preprocess_text(self, text):
        text = self.clean(text)

        # lowercase
        text = text.lower()

        # remove urls
        text = re.sub(r"http\S+|www\S+", " ", text)

        # split hashtags
        # #PizzaRoma -> pizza roma
        text = re.sub(r"#([A-Z][a-z]+)", r" \1", text)
        text = re.sub(r"#", " ", text)

        # remove repeated punctuation
        text = re.sub(r"[!?.,]{2,}", " ", text)

        # remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text


    def to_float(self, x, default=0.0):
        try:
            if pd.isna(x):
                return default
            return float(x)
        except:
            return default

    def _build_text(self, ad: dict) -> str:
        """
        Keep only strongest retrieval signals.
        Avoid bloated weak fields.
        """

        #ad_body = self.clean(ad.get("ad_body"))
        ad_body = self.preprocess_text(ad.get("ad_body"))
        page_category = self.preprocess_text(ad.get("page_category"))
        campaign_name = self.preprocess_text(ad.get("campaign_name"))
        creative_name = self.preprocess_text(ad.get("creative_name"))
        page_name = self.preprocess_text(ad.get("page_name"))
        interests = self.preprocess_text(ad.get("interests"))
        behaviors = self.preprocess_text(ad.get("behaviors"))

        return " | ".join([

            # HIGH importance
            ad_body,
            #ad_body,

            page_category,
            #page_category,

            # MEDIUM importance
            creative_name,
            campaign_name,

            # LOW importance
            interests,
            behaviors,
            page_name
        ])
        
        # return " | ".join([
        #     self.clean(ad.get("ad_body")),
        #     self.clean(ad.get("creative_name")),
        #     self.clean(ad.get("campaign_name")),
        #     #self.clean(ad.get("industry")),
        #     self.clean(ad.get("page_category")),
        #     self.clean(ad.get("interests")),
        #     self.clean(ad.get("behaviors")),
        # ])

    # =====================================
    # SCORING
    # =====================================

    def _performance_score(self, ad):
        results_val = self.to_float(ad.get("results"), 0)
        benchmark = self.to_float(ad.get("benchmark_min_pass"), 1)

        if benchmark <= 0:
            benchmark = 1

        # ratio = results_val / benchmark

        # # cap at 2x
        # ratio = min(ratio, 2.0)

        # # normalize 0-100
        # return (ratio / 2.0) * 100

        # relative performance
        ratio = results_val / benchmark

        # logarithmic scaling
        score = np.log1p(ratio) * 20

        # cap safely
        score = min(score, 100)

        return round(score, 1)

    # def _industry_score(self, ad):
    #     return self.to_float(ad.get("industry_score"), 50)

    # def _keyword_boost(self, query: str, ad_text: str):
    #     q = query.lower().strip()
    #     txt = ad_text.lower()

    #     if not q:
    #         return 0

    #     if q in txt:
    #         return 5.0

    #     return 0.0

    def _keyword_boost(self, query, ad_text, sim):
        q = query.lower().strip()
        txt = ad_text.lower()

        if not q:
            return 0

        # Only boost if semantic match is already decent
        if sim < 0.28:
            return 0

        count = txt.count(q)

        # Single-word commercial query
        if " " not in q:
            if count >= 2:
                return 12
            elif count == 1:
                return 4
            else:
                return -6

        # Multi-word query
        if count >= 1:
            return 6

        return 0



    def _tier_label(self, sim):
        if sim >= 0.45:
            return "First Tier"
        elif sim >= 0.28:   # from 0.32
            return "Second Tier"
        elif sim >= 0.24:  # from 0.18
            return "Third Tier"

        # if sim >= 0.55:
        #     return "First Tier"
        # elif sim >= 0.40:
        #     return "Second Tier"
        # elif sim >= 0.25:
        #     return "Third Tier"
        return None

    # =====================================
    # MAIN SEARCH
    # =====================================

    def retrieve_tiered(
        self,
        query: str,
        k: int = 10,
        candidate_pool: int = 100
    ) -> list[dict]:

        query = query.strip()

        if not query:
            return []

        # -----------------------------
        # Encode query
        # -----------------------------
        q_emb = self.model.encode(
            [query],
            normalize_embeddings=True
        )[0]

        # -----------------------------
        # Semantic search
        # -----------------------------
        sims = np.dot(self.embeddings, q_emb)

        idx = np.argsort(sims)[::-1][:candidate_pool]


        # -----------------------------
        # BM25 lexical scoring
        # -----------------------------
        query_tokens = query.lower().split()
        bm25_scores = self.bm25.get_scores(query_tokens)

        bm25_max = max(bm25_scores) if len(bm25_scores) > 0 else 1

        def normalize_bm25(score):
            if bm25_max == 0:
                return 0
            return score / bm25_max



        candidates = []

        # diversity trackers
        campaign_count = {}
        page_count = {}

        for i in idx:
            sim = float(sims[i])

            tier = self._tier_label(sim)

            if tier is None:
                continue

            ad = dict(self.ads[i])  # copy
            ad["_idx"] = i

            ad_text = self.texts[i]

            # semantic_score = sim * 100
            # performance_score = self._performance_score(ad)
            # #industry_score = self._industry_score(ad)
            # keyword_boost = self._keyword_boost(query, ad_text, sim)

            # final_score = (
            #     semantic_score * 0.75 +
            #     performance_score * 0.25 +
            #     #industry_score * 0.15 +
            #     keyword_boost
            # )

            # -----------------------------
            # Hybrid scoring
            # -----------------------------
            semantic_score = sim  # keep in 0–1

            lexical_score = normalize_bm25(bm25_scores[i])

            # combine semantic + lexical
            hybrid_score = (
                0.7 * semantic_score +
                0.3 * lexical_score
            )

            # scale to 0–100
            hybrid_score_scaled = hybrid_score * 100

            performance_score = self._performance_score(ad)
            keyword_boost = self._keyword_boost(query, ad_text, sim)

            # final_score = (
            #     hybrid_score_scaled * 0.85 +
            #     performance_score * 0.15 +
            #     keyword_boost
            # )

            final_score = (
                hybrid_score_scaled +
                keyword_boost
            )

            # store debug values
            ad["semantic_score"] = round(semantic_score * 100, 1)
            ad["lexical_score"] = round(lexical_score * 100, 1)
            ad["hybrid_score"] = round(hybrid_score_scaled, 1)


            #ad["semantic_score"] = round(semantic_score, 1)
            ad["performance_score"] = round(performance_score, 1)
            #ad["industry_score"] = round(industry_score, 1)
            ad["score"] = round(final_score, 1)
            ad["tier"] = tier

            candidates.append(ad)

        
        # -----------------------------
        # 1. Sort by final score
        # -----------------------------
        candidates.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # -----------------------------
        # 2. Cross-encoder reranking
        # -----------------------------
        top_n = min(len(candidates), 30)

        rerank_candidates = candidates[:top_n]

        pairs = [
            (query, self.texts[ad["_idx"]])
            for ad in rerank_candidates
        ]

        rerank_scores = self.reranker.predict(pairs)

        # normalize rerank scores to 0–1
        r_min = min(rerank_scores)
        r_max = max(rerank_scores) if len(rerank_scores) > 0 else 1

        def normalize_rerank(s):
            if r_max == r_min:
                return 0
            return (s - r_min) / (r_max - r_min)

        # inject rerank into score
        for idx_r, ad in enumerate(rerank_candidates):
            r_score = normalize_rerank(rerank_scores[idx_r])

            ad["rerank_score"] = round(r_score * 100, 1)

            ad["score"] = (
                ad["score"] * 0.7 +
                (r_score * 100) * 0.3
            )


        # 3. FINAL SORT (this is missing in your version)
        candidates.sort(key=lambda x: x["score"], reverse=True)

        filtered_candidates = []

        for ad in candidates:

            tier = ad["tier"]
            score = ad["score"]

            if tier == "First Tier" and score >= 30:
                filtered_candidates.append(ad)

            elif tier == "Second Tier" and score >= 18:
                filtered_candidates.append(ad)

            elif tier == "Third Tier" and score >= 10:
                filtered_candidates.append(ad)

        candidates = filtered_candidates


        # -----------------------------
        # 4. Business ranking
        # relevance first
        # performance second
        # -----------------------------
        for ad in candidates:

            performance_score = self._performance_score(ad)

            ad["business_score"] = round(performance_score, 1)

            ad["final_business_score"] = (
                ad["score"] * 0.8 +
                performance_score * 0.2
            )

        # final ranking
        candidates.sort(
            key=lambda x: x["final_business_score"],
            reverse=True
        )

        # -----------------------------
        # Diversity control
        # max 2 same campaign
        # max 3 same page
        # -----------------------------
        final_results = []

        for ad in candidates:
            campaign = self.clean(ad.get("campaign_name")) or "UNKNOWN"
            page = self.clean(ad.get("page_name")) or "UNKNOWN"

            c_count = campaign_count.get(campaign, 0)
            p_count = page_count.get(page, 0)

            if c_count >= 2:
                continue

            if p_count >= 3:
                continue

            final_results.append(ad)

            campaign_count[campaign] = c_count + 1
            page_count[page] = p_count + 1

            if len(final_results) >= k:
                break

        return final_results


# =====================================
# RUNNER
# =====================================

def main():
    obj = s3.get_object(
        Bucket=S3_BUCKET,
        Key=S3_INPUT
    )

    df = pd.read_csv(obj["Body"])

    print("Loaded:", len(df))

    ads = df.to_dict(orient="records")

    rag = RAGRetriever(ads)

    query = input("Enter query: ").strip()

    results = rag.retrieve_tiered(query, k=20)

    print("\n=== RESULTS BY TIER ===")

    tiers = {
        "First Tier": [],
        "Second Tier": [],
        "Third Tier": []
    }

    for r in results:
        tiers[r["tier"]].append(r)

    for tier_name in [
        "First Tier",
        "Second Tier",
        "Third Tier"
    ]:
        print(f"\n{tier_name}")
        print("-" * 80)

        for r in tiers[tier_name]:
            print("Campaign Name :", r.get("campaign_name", ""))
            print("Ad Name       :", r.get("ad_name", ""))
            print("Ad Title      :", r.get("ad_title", ""))
            print("Ad Body       :", str(r.get("ad_body", ""))[:700])
            print("Result Type   :", r.get("result_type", ""))
            print("Results       :", r.get("results", ""))
            print("Cost          :", r.get("spend", ""))
            print("Cost per Result:", r.get("cost_per_results", ""))
            print("Industry      :", r.get("industry", ""))
            print("Page Name     :", r.get("page_name", ""))
            print("Page Category :", r.get("page_category", ""))
            print("Tier          :", r.get("tier", ""))
            print("Relevance Score         :", r.get("score", ""))  # Before was Score
            print("Business Score:", r.get("business_score", ""))
            print("Final Score   :", r.get("final_business_score", ""))
            print("Semantic      :", r.get("semantic_score", ""))
            print("-" * 100)


if __name__ == "__main__":
    main()
    