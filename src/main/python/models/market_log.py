from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

@dataclass
class MarketLog:
    """
    Represents a single snapshot of market funding data.
    """
    currency: str
    rates_data: Dict[int, Dict[str, Optional[float]]]
    timestamp: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None # The database ID, populated after insertion
