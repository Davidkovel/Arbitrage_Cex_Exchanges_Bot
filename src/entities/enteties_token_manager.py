from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class SpreadState:
    last_reported_spread: float = 0.0
    last_actual_spread: float = 0.0
    should_notify: bool = False