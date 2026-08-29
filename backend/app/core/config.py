"""Application settings loaded from environment (.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    debug: bool = False

    database_url: str
    supabase_url: str
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    cors_origins: str = "http://localhost:5173"

    # Brevo transactional email API: our own notices (password-changed today;
    # the deferred employee-acknowledgement email phase reuses this same
    # account later). Password recovery itself is sent by Supabase Auth, not
    # us -- these settings are only for notices we compose ourselves.
    #
    # Was SMTP (smtplib -> smtp.gmail.com:587); switched after a real
    # production incident on the sibling app (app_leave_approve, 2026-08-29,
    # same Render hosting, same shared Gmail account) found that Render
    # blocks ALL outbound SMTP at the network level -- every send failed
    # with `OSError: [Errno 101] Network is unreachable` regardless of
    # provider or credentials. Brevo's HTTP API (https://api.brevo.com) is
    # plain HTTPS, so it isn't affected.
    brevo_api_key: str = ""
    mail_from: str = ""
    mail_from_name: str = "ฝ่ายบุคคล"

    @property
    def brevo_configured(self) -> bool:
        return bool(self.brevo_api_key and self.mail_from)

    # Used to build links in the daily digest email (services/notifications.py)
    # back into the evaluation the recipient needs to act on.
    frontend_url: str = "https://app-evaluation-system.vercel.app"

    # Shared secret an external cron (e.g. cron-job.org, same idea as the
    # UptimeRobot keep-alive ping already documented for cold starts) must
    # send as `X-Cron-Secret` to trigger POST /api/notifications/daily-digest.
    # Left unset by default so the endpoint fails closed rather than being
    # silently callable by anyone.
    cron_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
