package rlbotexample;

import rlbot.Bot;
import rlbot.ControllerState;
import rlbot.flat.GameTickPacket;
import rlbot.manager.BotLoopRenderer;
import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.panbot.BotBehaviour;
import rlbotexample.input.boost.BoostManager;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.output.BotOutput;
import rlbotexample.output.ControlsOutput;
import util.timer.AutoCorrectingLapse;

public class SampleBot implements Bot {

    private final int playerIndex;
    private BotOutput myBotOutput;
    private BotBehaviour botBehaviour;
    private Renderer renderer;
    private double averageFps;
    private long currentFpsTime;
    private long previousFpsTime;
    private long time1;
    private long time2;
    private long deltaTime;
    private double currentFps;


    public SampleBot(int playerIndex, BotBehaviour botBehaviour) {
        this.playerIndex = playerIndex;
        myBotOutput = new BotOutput();
        this.botBehaviour = botBehaviour;
        renderer = getRenderer();
        averageFps = 0;
        currentFpsTime = 0;
        previousFpsTime = 0;
        time1 = 0;
        time2 = 0;
        deltaTime = 0;
        currentFps = 0;

    }

    /**
     * This is where we keep the actual bot logic. This function shows how to chase the getNativeBallPrediction.
     * Modify it to make your bot smarter!
     */
    private ControlsOutput processInput(DataPacket input, GameTickPacket packet) {

        // refresh boostPads information so we can utilize it
        BoostManager.loadGameTickPacket(packet);

        // Bot behaviour
        myBotOutput = botBehaviour.processInput(input, packet);



        // just some debug calculations all the way down to the return...
        previousFpsTime = currentFpsTime;
        currentFpsTime = System.currentTimeMillis();

        if(currentFpsTime - previousFpsTime == 0) {
            currentFpsTime++;
        }
        currentFps = 1.0 / ((currentFpsTime - previousFpsTime) / 1000.0);
        averageFps = (averageFps*29 + (currentFps)) / 30.0;

        botBehaviour.updateGui(renderer, input, currentFps, averageFps, deltaTime);

        // Output the calculated states
        return myBotOutput.getForwardedOutput();
    }

    private Renderer getRenderer() {
        return BotLoopRenderer.forBotLoop(this);
    }

    @Override
    public int getIndex() {
        return this.playerIndex;
    }

    /**
     * This is the most important function. It will automatically get called by the framework with fresh data
     * every frame. Respond with appropriate controls!
     */
    @Override
    public ControllerState processInput(GameTickPacket packet) {
        // timestamp after executing the bot
        time1 = System.currentTimeMillis();

        if (packet.playersLength() <= playerIndex || packet.ball() == null || !packet.gameInfo().isRoundActive()) {
            // Just return immediately if something looks wrong with the data. This helps us avoid stack traces.
            return new ControlsOutput();
        }

        // Update the boost manager and tile manager with the latest data
        BoostManager.loadGameTickPacket(packet);

        // Translate the raw packet data (which is in an unpleasant format) into our custom DataPacket class.
        // The DataPacket might not include everything from GameTickPacket, so improve it if you need to!
        DataPacket dataPacket = new DataPacket(packet, playerIndex);

        // Do the actual logic using our dataPacket.
        ControlsOutput controlsOutput = processInput(dataPacket, packet);

        // timestamp before executing the bot
        time2 = System.currentTimeMillis();

        deltaTime = time2 - time1;
        return controlsOutput;
    }

    public void retire() {
        System.out.println("Retiring pan bot " + playerIndex);
        renderer.eraseFromScreen();
    }
}
