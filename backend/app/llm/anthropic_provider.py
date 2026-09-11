"""Adapter gọi Claude thật.

Dùng structured outputs: `messages.parse(output_format=ExtractionResult)` trả về
`response.parsed_output` đã được validate theo schema, nên không cần parse JSON tay.
"""

from app.llm.base import ExtractionError, ExtractionRequest, ExtractionResult
from app.llm.prompt import SYSTEM_PROMPT, build_user_prompt

MAX_TOKENS = 16000


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, client=None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        self._client = client
        self._model = model

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(request)}],
                output_format=ExtractionResult,
            )
        except Exception as exc:  # lỗi mạng, rate limit, 4xx/5xx từ SDK
            raise ExtractionError(f"Gọi Anthropic thất bại: {exc}") from exc

        if getattr(response, "stop_reason", None) == "refusal":
            raise ExtractionError("Anthropic từ chối xử lý báo cáo này")

        result = getattr(response, "parsed_output", None)
        if result is None:
            raise ExtractionError("Anthropic không trả về kết quả có cấu trúc")

        return result
