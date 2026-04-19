from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class MarketContext(BaseModel):
    my_company_stats: Dict
    rival_company_stats: Dict
    hidden_alliances: List[Dict]

class ReactionMap(BaseModel):
    competitor_aggression: Literal["Aggressive", "Neutral", "Defensive"] = Field(..., description="Overall competitor reaction")
    investor_sentiment: Literal["Positive", "Neutral", "Skeptical"] = Field(..., description="General investor reaction to the move")
    talent_retention: Literal["Joining", "Stable", "Leaving"] = Field(..., description="Impact on talent within the organization")

class MarketPrediction(BaseModel):
    who: str = Field(..., description="The entity affected")
    what: str = Field(..., description="The specific event or outcome")
    when: str = Field(..., description="Timeframe of the outcome")

class BestMove(BaseModel):
    verdict: str = Field(..., description="High contrast best move recommendation")
    chain_of_thought: str = Field(..., description="Deep reasoning validating the verdict against crustdata metrics")
    
class OracleDeck(BaseModel):
    reaction_map: ReactionMap
    predictions: List[MarketPrediction]
    best_move: BestMove
