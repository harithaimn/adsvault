# Run:
# python core/_06_1_download_models.py
# or
# python -m core._06_1_download_models

from sentence_transformers import SentenceTransformer, CrossEncoder
import os

# ==============================
# Embedding Model
# ==============================
embedding_model_name = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

embedding_save_path = (
    "./models/paraphrase-multilingual-MiniLM-L12-v2"
)

model = SentenceTransformer(embedding_model_name)

model.save(embedding_save_path)

print("\n[Embedding Model Saved]")
print("Model Name :", embedding_model_name)
print("Saved Path :", os.path.abspath(embedding_save_path))


# ==============================
# Reranker Model
# ==============================
reranker_model_name = (
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

reranker_save_path = (
    "./models/ms-marco-MiniLM-L-6-v2"
)

reranker = CrossEncoder(reranker_model_name)

reranker.save(reranker_save_path)

print("\n[Reranker Model Saved]")
print("Model Name :", reranker_model_name)
print("Saved Path :", os.path.abspath(reranker_save_path))


print("\nAll models downloaded and saved successfully.")