package util.machine_learning_models.evaluators;

import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.input.dynamic_data.DataPacket;
import util.game_constants.RlConstants;
import util.machine_learning_models.generic_data_structure.generic_data.FileParameter;

public class AirDribbleEvaluatorLogger2 extends BotEvaluator {

    private FileParameter fileParameter;

    public AirDribbleEvaluatorLogger2(FileParameter fileParameter, CarDestination desiredDestination) {
        super(desiredDestination);
        this.fileParameter = fileParameter;
    }

    @Override
    public void updateEvaluation(DataPacket input) {
        // gotta find a way to evaluate air dribbles
        double currentEvaluation = 0;

        // this is where we judge intensely the bot
        currentEvaluation -= input.ball.position.minus(input.car.position).magnitude();
        currentEvaluation -= getDesiredDestination().getThrottleDestination().minus(input.ball.position).magnitude();

        if(input.ball.position.x > RlConstants.WALL_DISTANCE_X - (RlConstants.BALL_RADIUS + 10)) {
            currentEvaluation -= 10000;
        }
        else if(input.ball.position.x < -(RlConstants.WALL_DISTANCE_X - (RlConstants.BALL_RADIUS + 10))) {
            currentEvaluation -= 10000;
        }
        if(input.ball.position.y > RlConstants.WALL_DISTANCE_Y - (RlConstants.BALL_RADIUS + 10)) {
            currentEvaluation -= 10000;
        }
        else if(input.ball.position.y < -(RlConstants.WALL_DISTANCE_Y - (RlConstants.BALL_RADIUS + 10))) {
            currentEvaluation -= 10000;
        }
        if(input.ball.position.z < 150) {
            currentEvaluation -= 10000;
        }
        else if(input.ball.position.z > RlConstants.CEILING_HEIGHT - (RlConstants.BALL_RADIUS + 10)) {
            currentEvaluation -= 10000;
        }

        // apply the new evaluation
        setEvaluation(currentEvaluation/100 + getEvaluation());
    }

    @Override
    public void resetEvaluation() {
        // serialize data so we can visualize it later
        fileParameter.set(getEvaluation());

        // do the things we normally do with superclass implementation
        super.resetEvaluation();
    }
}
