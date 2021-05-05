package rlbotexample.bot_behaviour.skill_controller.advanced_controller.boost_management;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.bot_behaviour.skill_controller.SkillController;
import rlbotexample.bot_behaviour.skill_controller.trash.DriveToDestination;
import rlbotexample.input.boost.BoostManager;
import rlbotexample.input.boost.BoostPad;
import rlbotexample.input.dynamic_data.DataPacket;
import util.vector.Vector3;

import java.awt.*;
import java.util.ArrayList;
import java.util.List;

public class RefuelProximityBoost extends SkillController {

    private CarDestination desiredDestination;
    private BotBehaviour bot;
    private SkillController driveToDestination;

    public RefuelProximityBoost(BotBehaviour bot) {
        this.desiredDestination = new CarDestination();
        this.bot = bot;
        this.driveToDestination = new DriveToDestination(desiredDestination, bot);
    }

    @Override
    public void updateOutput(DataPacket input) {
        Vector3 playerPosition = input.car.position;
        Vector3 playerNoseOrientation = input.car.orientation.noseVector;

        // regroup all boost pads in one single list
        List<BoostPad> boostPads = new ArrayList<>();
        boostPads.addAll(BoostManager.getFullBoosts());
        boostPads.addAll(BoostManager.getSmallBoosts());

        // get only those that are not taken
        List<BoostPad> notTakenBoostPads = new ArrayList<>();
        for (BoostPad boostPad : boostPads) {
            if (boostPad.isActive()) {
                notTakenBoostPads.add(boostPad);
            }
        }

        List<BoostPad> withinRangePads = new ArrayList<>();
        // get all boost pads within desired off-trajectory range
        // (where with respect to the player car do you think it's
        // alright to change slightly the current trajectory so we
        // take a boost while going to destination?)
        for(BoostPad pad: notTakenBoostPads) {
            if(pad.getLocation().minus(playerPosition).magnitude() < 600
                    && Math.abs(playerNoseOrientation.flatten().correctionAngle(pad.getLocation().flatten())) < Math.PI/((input.car.velocity.magnitude()*6/2300) + 4)) {
                withinRangePads.add(pad);
            }
        }

        // get closest in-range pad
        BoostPad closestNotTakenPad = null;
        double distanceOfClosest = Double.MAX_VALUE;
        for (BoostPad withinRangePad : withinRangePads) {
            if (withinRangePad.getLocation().minus(playerPosition).magnitude() < distanceOfClosest) {
                distanceOfClosest = withinRangePad.getLocation().minus(playerPosition).magnitude();
                closestNotTakenPad = withinRangePad;
            }
        }

        // if there were no pad in range, then don't do anything...
        // if there was at least one pad in range, then go to it.
        if(closestNotTakenPad != null) {

            // update the destination
            desiredDestination.setThrottleDestination(closestNotTakenPad.getLocation());
            desiredDestination.setSteeringDestination(closestNotTakenPad.getLocation());

            // got to destination
            driveToDestination.setupAndUpdateOutputs(input);
            bot.output().boost(false);
            bot.output().jump(false);
        }
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        renderer.drawLine3d(Color.LIGHT_GRAY, input.car.position, desiredDestination.getThrottleDestination());
    }
}
