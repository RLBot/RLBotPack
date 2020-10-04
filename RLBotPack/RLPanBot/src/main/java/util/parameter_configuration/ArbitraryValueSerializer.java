package util.parameter_configuration;

public class ArbitraryValueSerializer {

    public static final String LOCAL_CLASS_PATH = "src\\main\\java\\util\\parameter_configuration\\";
    public static final String ARBITRARY_CFG_PATH = LOCAL_CLASS_PATH + "arbitrary_cfg\\";
    public static final String BOOST_FOR_THROTTLE_THRESHOLD_FILENAME = ARBITRARY_CFG_PATH + "boost_throttle_threshold_val.arb";
    public static final String BOOST_FOR_THROTTLE_DRIBBLE_THRESHOLD_FILENAME = ARBITRARY_CFG_PATH + "boost_throttle_dribble_threshold_val.arb";
    public static final String DRIFT_FOR_STEERING_THRESHOLD_FILENAME = ARBITRARY_CFG_PATH + "drift_steering_threshold_val.arb";
    public static final String AIR_DRIBBLE_BALL_RADIUS_COEFFICIENT = ARBITRARY_CFG_PATH + "air_dribble_ball_radius_coefficient.arb";
    public static final String AIR_DRIBBLE_NOSE_DISTANCE_FROM_PLAYER = ARBITRARY_CFG_PATH + "air_dribble_nose_distance_from_player_position.arb";
    public static final String AIR_DRIBBLE_DISPLACEMENT_AMOUNT_COEFFICIENT = ARBITRARY_CFG_PATH + "air_dribble_displacement_amount_coefficient.arb";
    public static final String BALL_PREDICTION_SPIN_INFLUENCE_ON_VELOCITY = ARBITRARY_CFG_PATH + "ball_prediction_spin_influence_on_velocity.arb";
    public static final String BALL_PREDICTION_VELOCITY_INFLUENCE_ON_SPIN = ARBITRARY_CFG_PATH + "ball_prediction_velocity_influence_on_spin.arb";

    public static double serialize(String fileName) {
        return Double.valueOf(IOFile.getFileContent(fileName).get(0));
    }
}
