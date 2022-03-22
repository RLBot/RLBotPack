from enum import Enum, auto
     
class posRelativeToBall(Enum):
    # right behind or under the ball
    IN_POSSESSION = auto()
    # just past the ball, perhaps due to a whiff
    CLOSE_IN_FRONT = auto()
    # in front of the ball, but not right in front of it
    OFFSIDE = auto()
    # behind the ball and facing away from it
    FAR_BEHIND_AWAY = auto()
    # behind the ball and facing towards it, perhaps attacking
    FAR_BEHIND_TOWARD = auto()
    # self explanatory
    DEMOLISHED = auto()
    UNKNOWN = auto()

class posOnField(Enum):
    # in goal
    GOALIE = auto()
    # retreating to net or defense along the left, right, or center of the field
    RETREATING_LEFT = auto()
    RETREATING_RIGHT = auto()
    RETREATING_CENTER = auto()
    # pushing forward along the left, right, or center of the field
    ADVANCING_LEFT = auto()
    ADVANCING_RIGHT = auto()
    ADVANCING_CENTER = auto()
    # in the offensive corners
    ATTACKING_LEFT_CORNER = auto()
    ATTACKING_RIGHT_CORNER = auto()
    # in a position for a pass center
    ATTACKING_CENTER = auto()
    # self explanatory
    DEMOLISHED = auto()
    UNKNOWN = auto()