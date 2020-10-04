package rlbotexample.bot_behaviour.panbot;

import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.debug.BezierDebugger;
import util.vector.Vector3;

import java.awt.*;

public class PanBotGuiLogger {

    private CarDestination desiredDestination;

    public PanBotGuiLogger(CarDestination desiredDestination) {
        this.desiredDestination = desiredDestination;
    }

    public void displayDebugLines(Renderer renderer, DataPacket input) {
        Vector3 myPosition = input.car.position;
        Vector3 throttleDestination = desiredDestination.getThrottleDestination();
        Vector3 steeringDestination = desiredDestination.getSteeringDestination();

        renderer.drawLine3d(Color.LIGHT_GRAY, myPosition, throttleDestination);
        renderer.drawLine3d(Color.MAGENTA, myPosition, steeringDestination);
        //renderer.drawLine3d(Color.green, myPosition, aerialDestination);
        BezierDebugger.renderPath(desiredDestination.getPath(), Color.blue, renderer);
        //BezierDebugger.renderPositionControlledByCar(input, Color.PINK, renderer);
    }
}
