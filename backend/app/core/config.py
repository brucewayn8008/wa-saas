from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "wa-saas"
    API_V1_STR: str = "/api/v1"

    # Environment: "dev" enables conveniences (e.g. auth fallbacks); "prod" locks them off.
    ENV: str = "dev"

    # POSTGRES
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "wa_saas"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    GO_GATEWAY_URL: str = "http://localhost:5005"  # legacy whatsmeow gateway

    # wacli — near-term WhatsApp transport (https://wacli.sh/)
    WACLI_BIN: str = "wacli"
    WACLI_STORE_DIR: str = ""  # empty → CLI default (~/.wacli)
    WACLI_TIMEOUT_SECONDS: int = 120
    WACLI_WEBHOOK_SECRET: str = ""  # Feature 06 inbound webhook

    # LLM providers
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    # Gemini is the default reply model; Anthropic is the escalation model (hot / high-value
    # leads, or when Gemini fails). All model ids are env-overridable.
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBED_MODEL: str = "text-embedding-004"   # 768-dim → matches memory_facts.embedding
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    LLM_ESCALATION_ENABLED: bool = True

    # Conversation timing (debounce coalesces multi-bubble bursts; typing delay humanizes)
    REPLY_DEBOUNCE_SECONDS: float = 6.0
    USER_TYPING_TTL_SECONDS: float = 12.0
    TYPING_DELAY_MAX_SECONDS: float = 6.0

    # Clerk (auth + Organizations)
    CLERK_SECRET_KEY: str = ""
    CLERK_API_URL: str = "https://api.clerk.dev/v1"
    CLERK_JWKS_URL: str = ""
    CLERK_PEM_PUBLIC_KEY: str = ""  # Optional: offline verification

    # WhatsApp Business Cloud API
    WHATSAPP_API_BASE: str = "https://graph.facebook.com/v21.0"
    WHATSAPP_APP_SECRET: str = ""      # webhook signature verification
    WHATSAPP_VERIFY_TOKEN: str = ""    # webhook GET challenge

    # Stripe (billing)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Object storage (media) — S3 / Cloudflare R2 compatible
    OBJECT_STORAGE_ENDPOINT: str = ""
    OBJECT_STORAGE_BUCKET: str = ""
    OBJECT_STORAGE_KEY: str = ""
    OBJECT_STORAGE_SECRET: str = ""

    # Compliance defaults
    CUSTOMER_SERVICE_WINDOW_HOURS: int = 24
    DEFAULT_DAILY_MESSAGE_LIMIT: int = 35

    @property
    def IS_PROD(self) -> bool:
        return self.ENV.lower() in ("prod", "production")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()
