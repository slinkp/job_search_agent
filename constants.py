HAIKU_LATEST = "claude-haiku-4-5"
SONNET_LATEST = "claude-sonnet-4-5"
GPT_MINI_LATEST = "gpt-5-mini"
GPT_LATEST = "gpt-5.4"

DEFAULT_RECRUITER_MESSAGES = 500


MODEL_CHOICES: list[str] = list(
    sorted(
        set(
            [
                "gpt-4",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "gpt-5",
                "gpt-5-mini",
                "gpt-5.4",
                "claude-3-5-sonnet-20241022",
                "claude-3-7-sonnet-20250219",
                "claude-sonnet-4-20250514",
                "claude-sonnet-4-5",
                HAIKU_LATEST,
                SONNET_LATEST,
                GPT_MINI_LATEST,
                GPT_LATEST,
            ]
        )
    )
)
