from datetime import datetime
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


CONTENT_PREVIEW_LENGTH = 500


class VectorService:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )

    def _create_content_preview(self, content: str) -> str:
        """Create a content preview truncated to CONTENT_PREVIEW_LENGTH chars."""
        if len(content) > CONTENT_PREVIEW_LENGTH:
            return content[:CONTENT_PREVIEW_LENGTH] + "..."
        return content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upsert_embedding(
        self,
        neurolink_item_id: int,
        source_url: str,
        content_type: str | None,
        content: str,
        embedding: list[float]
    ) -> int:
        """
        Upsert an embedding into Supabase.
        Returns the embedding ID.
        """
        content_preview = self._create_content_preview(content)

        data = {
            "neurolink_item_id": neurolink_item_id,
            "source_url": source_url,
            "content_type": content_type,
            "content_preview": content_preview,
            "embedding": embedding
        }

        # Upsert based on neurolink_item_id unique constraint
        result = self.client.table("item_embeddings").upsert(
            data,
            on_conflict="neurolink_item_id"
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]["id"]

        raise Exception("Failed to upsert embedding - no data returned")

    def delete_embedding(self, neurolink_item_id: int) -> bool:
        """Delete an embedding by neurolink_item_id."""
        result = self.client.table("item_embeddings").delete().eq(
            "neurolink_item_id", neurolink_item_id
        ).execute()
        return True

    def search_similar(
        self,
        query_embedding: list[float],
        match_threshold: float = 0.7,
        match_count: int = 10,
        content_type: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None
    ) -> list[dict]:
        """
        Search for similar items using the match_items function.
        Returns list of matches with similarity scores.
        """
        params = {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count
        }

        if content_type:
            params["filter_content_type"] = content_type
        if after:
            params["filter_after"] = after.isoformat()
        if before:
            params["filter_before"] = before.isoformat()

        result = self.client.rpc("match_items", params).execute()

        return result.data if result.data else []


def get_vector_service() -> VectorService:
    """Factory function to get VectorService instance."""
    return VectorService()
