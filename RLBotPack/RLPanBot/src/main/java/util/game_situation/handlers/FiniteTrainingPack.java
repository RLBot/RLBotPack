package util.game_situation.handlers;

import util.game_situation.GameSituation;

public class FiniteTrainingPack extends GameSituationHandler {

    public FiniteTrainingPack() {
        super();
    }

    @Override
    public boolean hasNext() {
        return getNextGameSituationIndex() < getGameSituationList().size();
    }

    @Override
    public boolean hasBeenCompleted() {
        GameSituation currentGameSituation = getGameSituationList().get(getNextGameSituationIndex()-1);
        return (!hasNext()) && currentGameSituation.isGameStateElapsed();
    }
}
