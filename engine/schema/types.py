from enum import Enum

class EntityType(str, Enum):
    VENUE = "VENUE"
    RETAILER = "RETAILER"
    COACH = "COACH"
    INSTRUCTOR = "INSTRUCTOR"
    CLUB = "CLUB"
    LEAGUE = "LEAGUE"
    EVENT = "EVENT"
    TOURNAMENT = "TOURNAMENT"
