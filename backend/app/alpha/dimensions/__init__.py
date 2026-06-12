"""Registry of all active scoring dimensions.

The ordered list here IS the strategy set the composite engine runs. Append a
new ``DimensionScorer`` to extend the model; weights should sum to ~1.0.
"""
from app.alpha.dimensions.fundamental import FundamentalDimension
from app.alpha.dimensions.institutional import InstitutionalDimension
from app.alpha.dimensions.risk import RiskDimension
from app.alpha.dimensions.technical import TechnicalDimension
from app.alpha.dimensions.thematic import ThematicDimension

ALL_DIMENSIONS = [
    TechnicalDimension(),      # 30%
    InstitutionalDimension(),  # 25%
    FundamentalDimension(),    # 20%
    ThematicDimension(),       # 15%
    RiskDimension(),           # 10%
]

__all__ = ["ALL_DIMENSIONS"]
