import faiss
import os
import uuid
import json
import numpy as np
from typing import List
from storage import Storage
from sentence_transformers import SentenceTransformer
import random


class FaissStorage(Storage):
    def __init__(self, index_dir="faiss_index"):
        super().__init__()
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        # self._model = SentenceTransformer("all-mpnet-base-v2", device="cpu")
        # self._model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        try:
            self._model = SentenceTransformer("local_model/", device="cpu")
        except NotImplementedError:
            self._model = SentenceTransformer("local_model/")

    def _get_user_dir(self, user_id: str):
        return f"{self.index_dir}/{user_id}"

    def _get_index_path(self, user_id: str, category: str):
        return os.path.join(self._get_user_dir(user_id), f"{category}.index")

    def _get_metadata_path(self, user_id: str, category: str):
        return os.path.join(self._get_user_dir(user_id), f"{category}.json")

    def initialize_user(self, user_id: str):
        os.makedirs(f"{self.index_dir}/{user_id}", exist_ok=True)

    def get_all_categories(self, user_id: str):
        return [
            f.replace(".index", "")
            for f in os.listdir(self._get_user_dir(user_id))
            if f.endswith(".index")
        ]

    def ingest_paragraphs(
        self,
        user_id: str,
        category: str,
        paragraphs: List[str],
        embeddings: List,
        lang_prefix: str,
        mode: str,
    ):
        index_path = self._get_index_path(user_id, category)
        metadata_path = self._get_metadata_path(user_id, category)

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)

        if os.path.exists(index_path) and mode == "append":
            index = faiss.read_index(index_path)
            with open(metadata_path, "r") as f:
                existing_metadata = json.load(f)
        else:
            existing_metadata = []

        vectors = np.array(embeddings).astype("float32")
        index.add(vectors)

        for idx, content in enumerate(paragraphs):
            existing_metadata.append(
                {
                    "id": str(uuid.uuid4()),
                    "content": content.strip(),
                    "page": category,
                    "index": idx,
                    "lang_prefix": lang_prefix,
                }
            )

        faiss.write_index(index, index_path)
        with open(metadata_path, "w") as f:
            json.dump(existing_metadata, f)

        return len(paragraphs)

    def get_similar_documents(
        self, user_id: str, category: str, query_vector: List[float], n: int
    ):
        index_path = self._get_index_path(user_id, category)
        metadata_path = self._get_metadata_path(user_id, category)

        if not os.path.exists(index_path):
            return []

        index = faiss.read_index(index_path)
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        query_vector = np.array(query_vector).astype("float32").reshape(1, -1)
        distances, indices = index.search(query_vector, n)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(metadata):
                results.append(
                    {"content": metadata[idx]["content"], "similarity": 1 - float(dist)}
                )

        return results

    def get_paragraph_ids(self, user_id: str, category: str) -> List[str]:
        metadata_path = self._get_metadata_path(user_id, category)
        if not os.path.exists(metadata_path):
            return []
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        return [entry["id"] for entry in metadata]

    def sample_n_connected_paragraphs(
        self, user_id: str, category: str, number_of_questions: int
    ):
        metadata_path = self._get_metadata_path(user_id, category)
        if not os.path.exists(metadata_path):
            return None

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        sample_size = min(len(metadata), number_of_questions)
        sampled = random.sample(metadata, sample_size)
        return [{"content": entry["content"]} for entry in sampled]

    def get_all_paragraphs(self, user_id: str, category: str) -> list[str]:
        metadata_path = self._get_metadata_path(user_id, category)
        if not os.path.exists(metadata_path):
            return []
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        return [{"content": entry["content"], "id": entry["id"]} for entry in metadata]

    def delete_paragraph(self, user_id: str, category: str, paragraph_id: str):
        index_path = self._get_index_path(user_id, category)
        metadata_path = self._get_metadata_path(user_id, category)

        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            print(f"❌ No index or metadata found for category '{category}'")
            return

        # Load metadata
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # Find and remove the target entry
        updated_metadata = [entry for entry in metadata if entry["id"] != paragraph_id]

        if len(updated_metadata) == len(metadata):
            print(f"⚠️ Paragraph ID '{paragraph_id}' not found in '{category}'.")
            return

        # Recompute embeddings for updated metadata
        contents = [entry["content"] for entry in updated_metadata]
        if contents:
            embeddings = self._model.encode(contents, convert_to_numpy=True).astype(
                "float32"
            )
            index = faiss.IndexFlatL2(embeddings.shape[1])
            index.add(embeddings)
            faiss.write_index(index, index_path)
        else:
            # If no content remains, remove index file
            os.remove(index_path)

        # Write back updated metadata
        with open(metadata_path, "w") as f:
            json.dump(updated_metadata, f)

        print(f"✅ Paragraph '{paragraph_id}' deleted from '{category}'")
