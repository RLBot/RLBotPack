package rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.comit_to_ball;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.jump.JumpHandler;
import rlbotexample.bot_behaviour.skill_controller.jump.implementations.*;
import rlbotexample.input.boost.BoostManager;
import rlbotexample.input.boost.BoostPad;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import util.vector.Vector3;

import java.awt.*;
import java.util.List;

public class BoostAndFlipToDestination extends SkillController {

    private Vector3 destination;
    private final BotBehaviour bot;

    private JumpHandler jumpHandler;
    private boolean hasJumped;

    private int callCounter;

    public BoostAndFlipToDestination(BotBehaviour bot) {
        this.bot = bot;
        this.jumpHandler = new JumpHandler();
        this.callCounter = 0;
    }

    public void setDestination(Vector3 destination) {
        this.destination = destination;
    }

    @Override
    public void updateOutput(DataPacket input) {
        updateJumpBehaviour(input);
    }

    private void updateJumpBehaviour(DataPacket input) {
        BotOutput output = bot.output();
        Vector3 playerPosition = input.car.position;
        Vector3 playerNoseVector = input.car.orientation.noseVector;
        Vector3 playerRoofVector = input.car.orientation.roofVector;
        Vector3 ballPosition = input.ball.position;

        if (jumpHandler.isJumpFinished() && input.car.velocity.magnitude() > 500 && callCounter > 10) {
            if(input.car.hasWheelContact) {
                jumpHandler.setJumpType(new ShortJump());
                output.boost(true);
                hasJumped = true;
                //System.out.println("set jump");
            }
            else if(hasJumped) {
                jumpHandler.setJumpType(new Flip());
                output.boost(false);
                hasJumped = false;
                //System.out.println("set flip");
            }
            else {
                jumpHandler.setJumpType(new Wait());
                hasJumped = false;
            }
        }
        Vector3 localDestination = ballPosition.minus(playerPosition).minusAngle(playerNoseVector);

        jumpHandler.updateJumpState(
                input,
                output,
                localDestination,
                playerRoofVector.minusAngle(new Vector3(0, 0, 1))
        );
        output.jump(jumpHandler.getJumpState());
        callCounter++;
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
    }
}
