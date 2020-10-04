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

public class RefuelBoost extends SkillController {

    private CarDestination desiredDestination;
    private BotBehaviour bot;
    private SkillController driveToDestination;

    public RefuelBoost(BotBehaviour bot) {
        this.desiredDestination = new CarDestination();
        this.bot = bot;
        this.driveToDestination = new DriveToDestination(desiredDestination, bot);
    }

    @Override
    public void updateOutput(DataPacket input) {
        Vector3 playerPosition = input.car.position;

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

        // get closest from car
        BoostPad closestNotTakenPad = notTakenBoostPads.get(0);
        for(int i = 1; i < notTakenBoostPads.size(); i++) {
            if(closestNotTakenPad.getLocation().minus(playerPosition).magnitude() > notTakenBoostPads.get(i).getLocation().minus(playerPosition).magnitude()) {
                closestNotTakenPad = notTakenBoostPads.get(i);
            }
        }

        // update the destination
        desiredDestination.setThrottleDestination(closestNotTakenPad.getLocation());
        desiredDestination.setSteeringDestination(closestNotTakenPad.getLocation());

        // got to destination
        driveToDestination.setupAndUpdateOutputs(input);
        bot.output().boost(false);
    }

    @Override
    public void setupController() {

    }

    @Override
    public void debug(Renderer renderer, DataPacket input) {
        renderer.drawLine3d(Color.LIGHT_GRAY, input.car.position, desiredDestination.getThrottleDestination());
    }
}
