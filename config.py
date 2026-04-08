from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]

@dataclass(slots=True)
class Settings:
    prefix: str = os.getenv("PREFIX", "!")
    guild_id: int = int(os.getenv("GUILD_ID", "0"))
    token: str = os.getenv("DISCORD_TOKEN", "")
    db_path: str = str(BASE_DIR / "dmv_system.db")

    web_host: str = os.getenv("WEB_HOST", "0.0.0.0")
    web_port: int = int(os.getenv("WEB_PORT", "8080"))
    run_web_with_bot: bool = os.getenv("RUN_WEB_WITH_BOT", "true").lower() == "true"
    web_secret_key: str = os.getenv("WEB_SECRET_KEY", "change_me")
    web_base_url: str = os.getenv("WEB_BASE_URL", "http://localhost:8080")
    discord_client_id: str = os.getenv("DISCORD_CLIENT_ID", "")
    discord_client_secret: str = os.getenv("DISCORD_CLIENT_SECRET", "")
    discord_redirect_uri: str = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")

    erlc_server_key: str = os.getenv("ERLC_SERVER_KEY", "")

    dmv_staff_roles: list[str] = field(default_factory=list)
    admin_roles: list[str] = field(default_factory=list)
    police_roles: list[str] = field(default_factory=list)
    ticket_staff_roles: list[str] = field(default_factory=list)

    verified_role: str = os.getenv("VERIFIED_ROLE", "Verified")
    unverified_role: str = os.getenv("UNVERIFIED_ROLE", "Unverified")
    applicant_role: str = os.getenv("APPLICANT_ROLE", "DMV Staff")

    welcome_channel: str = os.getenv("WELCOME_CHANNEL", "welcome")
    dmv_logs_channel: str = os.getenv("DMV_LOGS_CHANNEL", "dmv-logs")
    police_logs_channel: str = os.getenv("POLICE_LOGS_CHANNEL", "police-logs")
    applications_channel: str = os.getenv("APPLICATIONS_CHANNEL", "applications")
    ticket_logs_channel: str = os.getenv("TICKET_LOGS_CHANNEL", "ticket-logs")
    ticket_category: str = os.getenv("TICKET_CATEGORY", "Tickets")

    verify_question: str = os.getenv("VERIFY_QUESTION", "What is 2+2?")
    verify_answer: str = os.getenv("VERIFY_ANSWER", "4")

    max_wallet: int = int(os.getenv("MAX_WALLET", "500000"))
    max_bank: int = int(os.getenv("MAX_BANK", "5000000"))
    daily_reward_min: int = int(os.getenv("DAILY_REWARD_MIN", "300"))
    daily_reward_max: int = int(os.getenv("DAILY_REWARD_MAX", "900"))
    work_reward_min: int = int(os.getenv("WORK_REWARD_MIN", "100"))
    work_reward_max: int = int(os.getenv("WORK_REWARD_MAX", "500"))
    no_license_fine: int = int(os.getenv("NO_LICENSE_FINE", "750"))
    bank_interest_rate: float = float(os.getenv("BANK_INTEREST_RATE", "0.02"))

    def __post_init__(self) -> None:
        self.dmv_staff_roles = _split_csv(os.getenv("DMV_STAFF_ROLES", "DMV Staff"))
        self.admin_roles = _split_csv(os.getenv("ADMIN_ROLES", "Administrator"))
        self.police_roles = _split_csv(os.getenv("POLICE_ROLES", "Police"))
        self.ticket_staff_roles = _split_csv(os.getenv("TICKET_STAFF_ROLES", "DMV Staff,Support Team,Administrator"))

settings = Settings()
