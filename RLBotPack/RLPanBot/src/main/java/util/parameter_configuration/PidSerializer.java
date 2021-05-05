package util.parameter_configuration;

import util.controllers.PidController;

import java.util.ArrayList;
import java.util.List;

public class PidSerializer {
    public static final String LOCAL_CLASS_PATH = "src\\main\\java\\util\\parameter_configuration\\";
    public static final String PID_CFG_PATH = LOCAL_CLASS_PATH + "pid_cfg\\";
    public static final String THROTTLE_FILENAME = PID_CFG_PATH + "pid_throttle_val.pcg";
    public static final String STEERING_FILENAME = PID_CFG_PATH + "pid_steering_val.pcg";
    public static final String PITCH_YAW_FILENAME = PID_CFG_PATH + "pid_pitch_yaw_val.pcg";
    public static final String ROLL_FILENAME = PID_CFG_PATH + "pid_roll_val.pcg";
    public static final String AERIAL_ANGLE_FILENAME = PID_CFG_PATH + "pid_aerial_angle_val.pcg";
    public static final String AERIAL_BOOST_FILENAME = PID_CFG_PATH + "pid_aerial_boost_val.pcg";
    public static final String DRIBBLE_FILENAME = PID_CFG_PATH + "pid_dribble_val.pcg";
    public static final String AIR_DRIBBLE_ORIENTATION_XY_FILENAME = PID_CFG_PATH + "pid_air_dribble_orientation_xy_val.pcg";
    public static final String AIR_DRIBBLE_ORIENTATION_Z_FILENAME = PID_CFG_PATH + "pid_air_dribble_orientation_z_val.pcg";
    public static final String AIR_DRIBBLE_FILENAME = PID_CFG_PATH + "pid_air_dribble_val.pcg";

    public static PidController fromFileToPid(String fileName, PidController previousPid) {
        List<String> parameters = IOFile.getFileContent(fileName);

        double kp = Double.valueOf(parameters.get(0));
        double ki = Double.valueOf(parameters.get(1));
        double kd = Double.valueOf(parameters.get(2));

        PidController newPid = new PidController(kp, ki, kd);
        previousPid.transferInternalMemoryTo(newPid);

        return newPid;
    }

    public static void fromPidToFile(String fileName, PidController pidToPutInFile) {
        List<String> stringArray = new ArrayList<>();

        String kp = String.valueOf(pidToPutInFile.getProportionnalConstant());
        String ki = String.valueOf(pidToPutInFile.getIntegralConstant());
        String kd = String.valueOf(pidToPutInFile.getDerivativeConstant());

        stringArray.add(kp);
        stringArray.add(ki);
        stringArray.add(kd);

        IOFile.createFileWithContent(fileName, stringArray);
    }
}
