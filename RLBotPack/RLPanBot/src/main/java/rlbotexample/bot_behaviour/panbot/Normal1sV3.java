package rlbotexample.bot_behaviour.panbot;

import rlbot.flat.GameTickPacket;
import rlbot.render.Renderer;
import rlbotexample.bot_behaviour.car_destination.CarDestination;
import rlbotexample.bot_behaviour.metagame.possessions.PossessionEvaluator;
import rlbotexample.bot_behaviour.path.BallPositionPath;
import rlbotexample.bot_behaviour.path.EnemyNetPositionPath;
import rlbotexample.bot_behaviour.path.PathHandler;
import rlbotexample.bot_behaviour.path.PlayerNetPositionPath;
import rlbotexample.bot_behaviour.skill_controller.*;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.aerials.AerialSetupController;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.boost_management.RefuelProximityBoost;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.defense.ShadowDefense;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense.Dribble;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense.Flick;
import rlbotexample.bot_behaviour.skill_controller.advanced_controller.offense.Flip;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.DriveToDestination2Controller;
import rlbotexample.bot_behaviour.skill_controller.basic_controller.DriveToPredictedBallBounceController;
import rlbotexample.bot_behaviour.skill_controller.trash.DriveToDestination;
import rlbotexample.bot_behaviour.skill_controller.triple_threat.kickoff.comit_to_ball.KickoffSpecializedOnBall;
import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.ExtendedCarData;
import rlbotexample.output.BotOutput;
import util.controllers.PidController;
import util.debug.BezierDebugger;
import util.vector.Vector3;

import java.awt.*;
import java.util.ArrayList;

public class Normal1sV3 extends PanBot {

    private CarDestination desiredDestination;

    private SkillController dribbleController;
    private SkillController flickController;
    private Flip flipController;
    private SkillController driveToDestinationController;
    private DriveToDestination2Controller improvisedDriveToDestinationController;
    private SkillController shadowDefenseController;
    private SkillController refuelProximityBoostController;
    private KickoffSpecializedOnBall kickoffController;
    private DriveToPredictedBallBounceController driveToPredictedBallBounceController;
    private AerialSetupController aerialSetupController;
    private SkillController skillController;

    private PathHandler pathHandler;
    private PathHandler enemyNetPositionPath;
    private PathHandler playerNetPositionPath;
    private PathHandler ballPositionPath;

    private PidController playerPossessionPid;

    private boolean isRefueling;
    private boolean isAerialing;
    private boolean isInCriticalPosition;
    private int kickoffCallCounter;

    public Normal1sV3() {
        desiredDestination = new CarDestination();

        dribbleController = new Dribble(desiredDestination, this);
        flickController = new Flick(desiredDestination, this);
        flipController = new Flip(this);
        driveToDestinationController = new DriveToDestination(desiredDestination, this);
        improvisedDriveToDestinationController = new DriveToDestination2Controller(this);
        shadowDefenseController = new ShadowDefense(this);
        refuelProximityBoostController = new RefuelProximityBoost(this);
        kickoffController = new KickoffSpecializedOnBall(this);
        driveToPredictedBallBounceController = new DriveToPredictedBallBounceController(this);
        aerialSetupController = new AerialSetupController(this);
        skillController = driveToDestinationController;

        enemyNetPositionPath = new EnemyNetPositionPath(desiredDestination);
        playerNetPositionPath = new PlayerNetPositionPath(desiredDestination);
        ballPositionPath = new BallPositionPath(desiredDestination);
        pathHandler = ballPositionPath;

        playerPossessionPid = new PidController(1, 0, 10);

        isRefueling = false;
        isAerialing = false;
        kickoffCallCounter = 0;
    }

    // called every frame
    @Override
    public BotOutput processInput(DataPacket input, GameTickPacket packet) {
        int playerIndex = input.playerIndex;

        int opponentIndex = getOpponents(input).get(0).playerIndex;
        double playerPossessionRatio = PossessionEvaluator.possessionRatio(playerIndex, opponentIndex, input);
        double predictivePlayerPossessionRatio = playerPossessionPid.process(playerPossessionRatio, 0);
        final Vector3 allyNetPosition = new Vector3(0, -5200 * (input.team == 0 ? 1 : -1), 100);

        // do the thing

        // is it the kickoff...?
        if(input.ball.velocity.magnitude() < 0.1) {
            // destination on getNativeBallPrediction
            pathHandler = ballPositionPath;

            // drive to it
            skillController = kickoffController;

            if(kickoffCallCounter < 15) {
                output().jump(false);
            }
            kickoffCallCounter++;
        }
        else {
            // reset kickoff counter
            kickoffCallCounter = 0;

            // destination on enemy net
            pathHandler = enemyNetPositionPath;

            // if the ball is bouncing and we're not directly dribbling, we need to go get the next bounce
            if(input.car.position.minus(input.ball.position).magnitude() > 300 /*&& (Math.abs(input.ball.velocity.z) > 200 || input.ball.position.z > 160)*/) {
                driveToPredictedBallBounceController.setDestination(allyNetPosition.scaled(-1));
                skillController = driveToPredictedBallBounceController;

                if(input.ball.position.minus(input.car.position).normalized().dotProduct(input.car.velocity) > 700 && input.ball.position.minus(input.car.position).magnitude() > 1200) {
                    flipController.setDestination(input.ballPrediction.ballAtTime(input.car.position.minus(input.ball.position).magnitude()/input.car.velocity.minus(input.ball.velocity).magnitude()).position);
                    skillController = flipController;
                }
            }
            else {
                // simply dribble and refuel if no threat
                // destination on enemy net
                pathHandler = enemyNetPositionPath;

                skillController = flickController;

                // flick the getNativeBallPrediction if threat
                if (input.ballPrediction.timeOfCollisionBetweenCarAndBall(1-input.playerIndex) > 2) {
                    // destination on enemy net
                    pathHandler = enemyNetPositionPath;

                    skillController = dribbleController;
                    //System.out.println("dribble");
                }
                else {
                }

                if(input.car.position.minus(input.ball.position).magnitude() < 160 && input.car.position.minus(allyNetPosition.scaled(-1)).magnitude() < input.ball.velocity.magnitude()*3) {
                    // destination on enemy net
                    pathHandler = enemyNetPositionPath;

                    skillController = flickController;
                }
            }


            // find the threatening player
            ExtendedCarData closestCarToBall = input.allCars.get(0);
            for(ExtendedCarData car: input.allCars) {
                if(closestCarToBall.position.minus(input.ball.position).magnitude() > car.position.minus(input.ball.position).magnitude()) {
                    closestCarToBall = car;
                }
            }
            if(closestCarToBall != input.car && closestCarToBall.position.minus(input.ball.position).magnitude() < 160 && closestCarToBall.position.minus(input.ball.position).z < -50 && input.car.position.minus(input.ball.position).magnitude() > 300) {
                if(input.allCars.size() <= 2) {
                    skillController = shadowDefenseController;
                    isRefueling = false;
                    //System.out.println("shadowD");
                }
                else {
                    pathHandler = playerNetPositionPath;
                    skillController = driveToDestinationController;
                    isRefueling = true;
                }
            }

            // aerial handling
            if(input.ballPrediction.ballAtTime(0.5).position.z > 400 && input.ballPrediction.ballAtTime(0.5).velocity.z > 0 && input.car.boost * 20 > input.ballPrediction.ballAtTime(1).position.z && input.car.position.minus(input.ball.position).flatten().magnitude() < 1000) {
                isAerialing = true;
            }
            else if(input.ball.position.z < 150) {
                isAerialing = false;
            }
            if(isAerialing) {
                aerialSetupController.setBallDestination(new Vector3(0, 5500 * (input.team == 0 ? 1 : -1), 500));
                //skillController = aerialSetupController;
            }

            // defense or smth
            if(allyNetPosition.minus(input.car.position).dotProduct(input.car.position.minus(input.ball.position.plus(new Vector3(0, 100*(input.team == 0 ? 1 : -1), 0)))) < 0) {
                isInCriticalPosition = true;
                final Vector3 defenseDirection = allyNetPosition.minus(input.ball.position);
                improvisedDriveToDestinationController.setDestination(allyNetPosition);
                improvisedDriveToDestinationController.setSpeed(Math.max(input.ball.velocity.magnitude()*2, 1400));
                /*
                if(Math.abs(input.car.position.y) > 4800) {
                    improvisedDriveToDestinationController.setDestination(new Vector3(0, -5400 * (input.team == 0 ? 1 : -1), 100));
                    improvisedDriveToDestinationController.setSpeed(2300);
                }*/
            }
            else if(allyNetPosition.minus(input.car.position).dotProduct(input.car.position.minus(input.ballPrediction.ballAtTime(allyNetPosition.minus(input.car.position).magnitude()/20000).position)) > 0) {
                isInCriticalPosition = false;
            }
            if(isInCriticalPosition) {
                //skillController = improvisedDriveToDestinationController;
            }

            /*
            // obvious rush on the getNativeBallPrediction?
            Vector3 playerNetCenterPosition;
            if(input.team == 0) {
                playerNetCenterPosition = new Vector3(0, -5500, 50);
            }
            else {
                playerNetCenterPosition = new Vector3(0, 5500, 50);
            }
            if(input.getNativeBallPrediction.velocity.y * playerNetCenterPosition.y < 0) {

            }*/
        }

        // calculate next desired destination
        pathHandler.updateDestination(input);

        // do something about it
        skillController.setupAndUpdateOutputs(input);

        if(input.car.position.minus(input.ball.position).magnitude() < 300) {
            isRefueling = false;
        }

        if(isRefueling) {
            // refuels boost if there is a pad near by
            refuelProximityBoostController.setupAndUpdateOutputs(input);
            //System.out.println("refueling");
        }
        if(input.car.boost > 90) {
            isRefueling = false;
        }
        else if(input.car.boost < 10) {
            isRefueling = true;
        }

        // return the calculated bot output
        return super.output();
    }

    private java.util.List<ExtendedCarData> getOpponents(DataPacket input) {
        java.util.List<ExtendedCarData> opponents = new ArrayList<>();

        for(int i = 0; i < input.allCars.size(); i++) {
            if(input.allCars.get(i).team != input.car.team) {
                opponents.add(input.allCars.get(i));
            }
        }

        return opponents;
    }

    @Override
    public void updateGui(Renderer renderer, DataPacket input, double currentFps, double averageFps, long botExecutionTime) {
        Vector3 playerPosition = input.car.position;
        Vector3 destination = desiredDestination.getThrottleDestination();
        Vector3 steeringPosition = desiredDestination.getSteeringDestination();

        dribbleController.debug(renderer, input);
        shadowDefenseController.debug(renderer, input);

        super.updateGui(renderer, input, currentFps, averageFps, botExecutionTime);
        renderer.drawLine3d(Color.LIGHT_GRAY, playerPosition, destination);
        renderer.drawLine3d(Color.MAGENTA, playerPosition, steeringPosition);
        BezierDebugger.renderPath(desiredDestination.getPath(), Color.blue, renderer);
    }
}
