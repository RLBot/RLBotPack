package rlbotexample.bot_behaviour.metagame.possessions;

import rlbotexample.input.dynamic_data.DataPacket;
import rlbotexample.input.dynamic_data.ExtendedCarData;

import java.util.ArrayList;
import java.util.List;

public class PlayerRoleHandler2V2 {

    private final ExtendedCarData offensive;
    private final ExtendedCarData lasMan;

    public PlayerRoleHandler2V2(DataPacket input) {
        final List<ExtendedCarData> carList = input.allCars;
        final List<ExtendedCarData> teamCarList = new ArrayList<>();
        final int teamIndex = input.team;

        // get all you team
        for(ExtendedCarData carData: carList) {
            if(carData.team == teamIndex) {
                teamCarList.add(carData);
            }
        }

        teamCarList.sort((o1, o2) -> (int) (1000 * PossessionEvaluator.possessionRatio(o2.playerIndex, o1.playerIndex, input)));

        offensive = teamCarList.get(0);
        lasMan = teamCarList.get(1);
    }

    public ExtendedCarData getPlayerFromRole(PlayerRole playerRole) {
        if(playerRole == PlayerRole.OFFENSIVE) {
            return offensive;
        }
        else if(playerRole == PlayerRole.LAST_MAN) {
            return lasMan;
        }
        else {
            throw new IllegalArgumentException();
        }
    }

    public PlayerRole getPlayerRole(DataPacket input) {
        if(input.playerIndex == offensive.playerIndex) {
            return PlayerRole.OFFENSIVE;
        }
        else {
            return PlayerRole.LAST_MAN;
        }
    }

}
