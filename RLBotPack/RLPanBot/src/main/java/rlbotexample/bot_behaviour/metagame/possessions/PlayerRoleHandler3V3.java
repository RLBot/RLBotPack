package rlbotexample.bot_behaviour.metagame.possessions;

import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.ExtendedCarData;

import java.util.ArrayList;
import java.util.List;

public class PlayerRoleHandler3V3 {

    private final ExtendedCarData offensive;
    private final ExtendedCarData backer;
    private final ExtendedCarData lasMan;

    public PlayerRoleHandler3V3(DataPacket input, int team) {
        final List<ExtendedCarData> carList = input.allCars;
        final List<ExtendedCarData> teamCarList = new ArrayList<>();

        // get all you team boii
        for(ExtendedCarData carData: carList) {
            if(carData.team == team) {
                teamCarList.add(carData);
            }
        }

        teamCarList.sort((o1, o2) -> (int) (1000 * PossessionEvaluator.possessionRatio(o2.playerIndex, o1.playerIndex, input)));

        offensive = teamCarList.get(0);
        backer = teamCarList.get(1);
        lasMan = teamCarList.get(2);
    }

    public ExtendedCarData getPlayerFromRole(PlayerRole playerRole) {
        if(playerRole == PlayerRole.OFFENSIVE) {
            return offensive;
        }
        else if(playerRole == PlayerRole.BACKER) {
            return backer;
        }
        else {
            return lasMan;
        }
    }

    public PlayerRole getPlayerRole(DataPacket input) {
        if(input.playerIndex == offensive.playerIndex) {
            return PlayerRole.OFFENSIVE;
        }
        else if(input.playerIndex == backer.playerIndex) {
            return PlayerRole.BACKER;
        }
        else {
            return PlayerRole.LAST_MAN;
        }
    }

}
