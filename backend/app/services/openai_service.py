import asyncio
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APIConnectionError, APITimeoutError

from app.core.config import settings


SUMMARY_PROMPT = "Summarize this content in 1-2 sentences, capturing the key insight."


class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.summary_model = settings.OPENAI_SUMMARY_MODEL
        self.max_content_length = settings.MAX_CONTENT_LENGTH
        self.rate_limit_delay = settings.RATE_LIMIT_DELAY

    def _truncate_content(self, content: str) -> str:
        """Truncate content to max length."""
        if len(content) > self.max_content_length:
            return content[:self.max_content_length] + "..."
        return content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError))
    )
    async def generate_summary(self, content: str) -> str:
        """Generate a summary for the given content."""
        truncated_content = self._truncate_content(content)

        response = await self.client.chat.completions.create(
            model=self.summary_model,
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": truncated_content}
            ],
            max_tokens=150,
            temperature=0.3
        )

        await asyncio.sleep(self.rate_limit_delay)
        return response.choices[0].message.content.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError))
    )
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for the given text."""
        truncated_text = self._truncate_content(text)

        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=truncated_text
        )

        await asyncio.sleep(self.rate_limit_delay)
        return response.data[0].embedding

    async def generate_embedding_for_item(self, summary: str, content: str) -> list[float]:
        """
        Generate embedding for an item.
        Combines summary + original content for richer semantic representation.
        """
        combined_text = f"{summary}\n\n{content}"
        return await self.generate_embedding(combined_text)

    async def generate_query_embedding(self, query: str) -> list[float]:
        """Generate embedding for a search query."""
        return await self.generate_embedding(query)


def get_openai_service() -> OpenAIService:
    """Factory function to get OpenAI service instance."""
    return OpenAIService()
