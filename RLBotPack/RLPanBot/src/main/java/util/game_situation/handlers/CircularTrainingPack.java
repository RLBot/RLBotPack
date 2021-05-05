package util.game_situation.handlers;

import util.game_situation.GameSituation;

public class CircularTrainingPack extends GameSituationHandler {

    public CircularTrainingPack() {
        super();
    }

    @Override
    public GameSituation next() {
        GameSituation nextGameSituation = super.next();

        // reset if we reached the final gameSituation
        int indexOfCurrentGameSituation = getGameSituationList().indexOf(nextGameSituation);
        int maxIndexValue = getGameSituationList().size() - 1;
        if(indexOfCurrentGameSituation == maxIndexValue) {
            super.reset();
        }

        return nextGameSituation;
    }

    @Override
    public boolean hasNext() {
        // it's a circular training pack, it always has a next game situation
        return true;
    }

    @Override
    public boolean hasBeenCompleted() {
        return false;
    }
}
