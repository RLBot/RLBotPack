package rlbotexample.bot_behaviour.skill_controller.debuging;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

public class OtherPlayerAccelerationSpeedPrinter extends SkillController {

    private Vector3 currentPlayerPosition;
    private Vector3 lastPlayerPosition;
    private Vector3 currentPlayerSpeed;
    private Vector3 lastPlayerSpeed;
    private Vector3 currentAcceleration;

    public OtherPlayerAccelerationSpeedPrinter() {
        super();
        currentPlayerPosition = new Vector3();
        lastPlayerPosition = new Vector3();
        currentPlayerSpeed = new Vector3();
        lastPlayerSpeed = new Vector3();
        currentAcceleration = new Vector3();
    }

    @Override
    public void updateOutput(DataPacket input) {
        // drive and turn to reach destination F
        lastPlayerPosition = currentPlayerPosition;
        currentPlayerPosition = input.allCars.get(input.allCars.size()-1).position;

        lastPlayerSpeed = currentPlayerSpeed;
        currentPlayerSpeed = currentPlayerPosition.minus(lastPlayerPosition);

        currentAcceleration = currentPlayerSpeed.minus(lastPlayerSpeed);

        System.out.println(currentAcceleration.magnitude());
    }

    @Override
    public void setupController() {
    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
