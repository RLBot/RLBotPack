package rlbotexample.bot_behaviour.panbot;

import rlbot.flat.GameTickPacket;
import rlbot.render.Renderer;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;

public abstract class BotBehaviour {

    private BotOutput myBotOutput;

    public BotBehaviour() {
        myBotOutput = new BotOutput();
    }

    public BotOutput output() {
        return myBotOutput;
    }

    public void setOutput(BotOutput output) {
        myBotOutput.throttle(output.throttle());
        myBotOutput.steer(output.steer());
        myBotOutput.pitch(output.pitch());
        myBotOutput.yaw(output.yaw());
        myBotOutput.roll(output.roll());
        myBotOutput.jump(output.jump());
        myBotOutput.boost(output.boost());
        myBotOutput.drift(output.drift());
    }

    public abstract BotOutput processInput(DataPacket input, GameTickPacket packet);

    public abstract void updateGui(Renderer renderer, DataPacket input, double currentFps, double averageFps, long botExecutionTime);
}
