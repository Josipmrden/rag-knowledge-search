from abc import ABC
from typing import List


class Storage(ABC):
    def initialize_user(self, user_id: str):
        pass

    def get_all_categories(self, user_id: str):
        pass

    def ingest_category(self, user_id: str):
        pass

    def get_similar_documents(self, user_id: str, category: str, question: str, n: int):
        pass

    def get_paragraph_ids(self, user_id: str, category: str):
        pass

    def sample_n_connected_paragraphs(
        self, user_id: str, category: str, number_of_questions: int
    ):
        pass

    def ingest_paragraphs(
        self,
        user_id: str,
        category: str,
        paragraphs: List[str],
        embeddings: List,
        lang_prefix: str,
        mode: str,
    ):
        pass
