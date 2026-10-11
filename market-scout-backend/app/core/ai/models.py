from dataclasses import dataclass

TOKENS_PER_MILLION = 1_000_000
DEFAULT_MODEL_ID = "claude-opus-5-5"


@dataclass(frozen=True)
class AiModel:
    id: str
    label: str
    input_per_mtok_usd: float
    output_per_mtok_usd: float
    supports_effort: bool


MODELS: tuple[AiModel, ...] = (
    AiModel("claude-opus-5-5", "Claude Opus 5.5", 4.0, 20.0, True),
    AiModel("claude-sonnet-5-5", "Claude Sonnet 5.5", 2.0, 10.0, True),
    AiModel("claude-haiku-4-5", "Claude Haiku 4.5", 1.0, 5.0, False),
)

_BY_ID = {model.id: model for model in MODELS}


def get_model(model_id: str) -> AiModel | None:
    return _BY_ID.get(model_id)


def cost_usd(model: AiModel, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * model.input_per_mtok_usd + output_tokens * model.output_per_mtok_usd) / TOKENS_PER_MILLION
