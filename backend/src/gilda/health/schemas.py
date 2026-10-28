from dataclasses import dataclass
from typing import Literal


@dataclass
class HealthStatus:
    api: Literal["ok"]
    database: Literal["ok", "unreachable"]
