import logging
from dataclasses import dataclass, field
from typing import Dict


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    base_url: str = "https://cn-north-1-production-apis.toddleapp.cn"
    default_timeout: int = 30
    max_page_size: int = 1000
    default_headers: Dict[str, str] = field(
        default_factory=lambda: {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )


CONFIG = Config()
