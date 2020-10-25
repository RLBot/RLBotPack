import numpy as np
from rlbot.utils.structures.game_data_struct import (
    MAX_NAME_LENGTH,
    ScoreInfo,
    BoxShape,
    CollisionShape,
    DropShotInfo,
    BoostPadState,
    TileInfo,
    TeamInfo,
    GameInfo,
    MAX_PLAYERS,
    MAX_BOOSTS,
    MAX_TILES,
    MAX_TEAMS,
    MAX_GOALS,
)
from rlbot.utils.structures.ball_prediction_struct import MAX_SLICES

dtype_Vector3 = np.dtype(("<f4", 3), align=True)

# game tick packet
dtype_Physics = np.dtype(
    [
        ("location", dtype_Vector3),
        ("rotation", dtype_Vector3),
        ("velocity", dtype_Vector3),
        ("angular_velocity", dtype_Vector3),
    ],
    align=True,
)

dtype_Name = np.dtype(("S2", (MAX_NAME_LENGTH,)))

dtype_Touch = np.dtype(
    [
        ("player_name", dtype_Name),
        ("time_seconds", "<f4"),
        ("hit_location", dtype_Vector3),
        ("hit_normal", dtype_Vector3),
        ("team", "<i4"),
        ("player_index", "<i4"),
    ],
    align=True,
)


dtype_ScoreInfo = np.dtype(ScoreInfo)

dtype_BoxShape = np.dtype(BoxShape)
dtype_CollisionShape = np.dtype(CollisionShape)

dtype_PlayerInfo = np.dtype(
    [
        ("physics", dtype_Physics),
        ("score_info", dtype_ScoreInfo),
        ("is_demolished", "?"),
        ("has_wheel_contact", "?"),
        ("is_super_sonic", "?"),
        ("is_bot", "?"),
        ("jumped", "?"),
        ("double_jumped", "?"),
        ("name", dtype_Name),
        ("team", "u1"),
        ("boost", "<i4"),
        ("hitbox", dtype_BoxShape),
        ("hitbox_offset", dtype_Vector3),
        ("spawn_id", "<i4"),
    ],
    align=True,
)

dtype_DropShotInfo = np.dtype(DropShotInfo)

dtype_BallInfo = np.dtype(
    [
        ("physics", dtype_Physics),
        ("latest_touch", dtype_Touch),
        ("drop_shot_info", dtype_DropShotInfo),
        ("collision_shape", dtype_CollisionShape),
    ],
    align=True,
)

dtype_BoostPadState = np.dtype(BoostPadState)
dtype_TileInfo = np.dtype(TileInfo)
dtype_TeamInfo = np.dtype(TeamInfo)
dtype_GameInfo = np.dtype(GameInfo)


dtype_GameTickPacket = np.dtype(
    [
        ("game_cars", dtype_PlayerInfo * MAX_PLAYERS),
        ("num_cars", "<i4"),
        ("game_boosts", dtype_BoostPadState * MAX_BOOSTS),
        ("num_boost", "<i4"),
        ("game_ball", dtype_BallInfo),
        ("game_info", dtype_GameInfo),
        ("dropshot_tiles", dtype_TileInfo * MAX_TILES),
        ("num_tiles", "<i4"),
        ("teams", dtype_TeamInfo * MAX_TEAMS),
        ("num_teams", "<i4"),
    ],
    align=True,
)


# field info
dtype_BoostPad = np.dtype([("location", dtype_Vector3), ("is_full_boost", "?")], align=True)


dtype_GoalInfo = np.dtype(
    [
        ("team_num", "u1"),
        ("location", dtype_Vector3),
        ("direction", dtype_Vector3),
        ("width", "<i4"),
        ("height", "<i4"),
    ],
    align=True,
)

dtype_FieldInfoPacket = np.dtype(
    [
        ("boost_pads", dtype_BoostPad * MAX_BOOSTS),
        ("num_boosts", "<i4"),
        ("goals", dtype_GoalInfo * MAX_GOALS),
        ("num_goals", "<i4"),
    ],
    align=True,
)

# ball prediction
dtype_Slice = np.dtype([("physics", dtype_Physics), ("game_seconds", "<f4")], align=True)

dtype_BallPrediction = np.dtype([("slices", dtype_Slice * MAX_SLICES), ("num_slices", "<i4")], align=True)

dtype_full_boost = np.dtype(
    [("location", float, 3), ("is_full_boost", "?"), ("is_active", "?"), ("timer", float)], align=True
)
