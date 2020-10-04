package util.machine_learning_models.hyperparameter_search;

import util.machine_learning_models.generic_data_structure.generic_data.GenericData;
import util.machine_learning_models.generic_data_structure.list.GenericDataList;

import java.util.ArrayList;
import java.util.List;

public class HyperParameterBruteForce2<D extends GenericData> {

    private static final int NUMBER_OF_FULL_SEARCH_TO_DO_BEFORE_CONSIDERED_FINISHED = 1000;

    private List<D> hyperParameter;
    private List<List<Double>> rewardFunctionHyperParameters;
    private List<Double> rewardFunctionOutput;
    private int numberOfFullSearchDone;
    private SearchState searchState;

    public HyperParameterBruteForce2(GenericDataList<D> dataRepresentation) {
        this.hyperParameter = dataRepresentation.getDataHandlerList();
        this.rewardFunctionHyperParameters = new ArrayList<>();
        this.rewardFunctionOutput = new ArrayList<>();
        this.numberOfFullSearchDone = 0;
        this.searchState = SearchState.GLOBAL_SEARCH;
    }

    public void sendSearchResult(double evaluationResult) {
        addPointToRewardFunction(hyperParameter, evaluationResult);
    }

    public void nextHypothesis() {
        if(searchState == SearchState.GLOBAL_SEARCH) {
            weightedRandomizeHyperParameter(getRandomPointInRewardFunction());
            searchState = SearchState.CLOSE_TO_GLOBAL_MAX_SEARCH;
        }
        else if(searchState == SearchState.CLOSE_TO_GLOBAL_MAX_SEARCH) {
            List<Double> bestPoint = getBestPointInRewardFunction();
            biasedWeightedRandomizeHyperParameter(bestPoint, getClosest(bestPoint));
            searchState = SearchState.GLOBAL_SEARCH;
        }
        numberOfFullSearchDone++;
    }

    public boolean isDoneSearching() {
        return numberOfFullSearchDone >= NUMBER_OF_FULL_SEARCH_TO_DO_BEFORE_CONSIDERED_FINISHED;
    }

    private void addPointToRewardFunction(List<D> hyperParameter, double evaluation) {
        rewardFunctionHyperParameters.add(new ArrayList<>());
        for(D parameter: hyperParameter) {
            rewardFunctionHyperParameters.get(rewardFunctionHyperParameters.size()-1).add(parameter.get());
        }
        rewardFunctionOutput.add(evaluation);
    }

    private void weightedRandomizeHyperParameter(List<Double> hyperParameter) {
        List<Double> randomNumberList = new ArrayList<>();

        for(int i = 0; i < hyperParameter.size(); i++) {
            randomNumberList.add((Math.random()-0.5)*2);
        }
        for(int i = 0; i < hyperParameter.size(); i++) {
            double newParameterValue = hyperParameter.get(i) * randomNumberList.get(i);
            this.hyperParameter.get(i).set(newParameterValue);
        }
    }

    private List<Double> getRandomPointInRewardFunction() {
        double randomValue = Math.random();

        randomValue *= rewardFunctionHyperParameters.size();

        return rewardFunctionHyperParameters.get((int)randomValue);
    }

    private List<Double> getBestPointInRewardFunction() {
        int index = 0;
        int lastBestIndex = 0;
        double lastBestReward = Double.MAX_VALUE;

        for (Double aDouble : rewardFunctionOutput) {
            if(aDouble < lastBestReward) {
                lastBestReward = aDouble;
                lastBestIndex = index;
                index++;
            }
        }

        return rewardFunctionHyperParameters.get(lastBestIndex);
    }

    private void biasedWeightedRandomizeHyperParameter(List<Double> hyperParameter, List<Double> closestParameter) {
        List<Double> randomNumberList = new ArrayList<>();

        for(int i = 0; i < hyperParameter.size(); i++) {
            randomNumberList.add((Math.random()-0.5)*2);
        }
        for(int i = 0; i < hyperParameter.size(); i++) {
            double newParameterValue = hyperParameter.get(i) +
                    ((hyperParameter.get(i)-closestParameter.get(i)) * randomNumberList.get(i));
            this.hyperParameter.get(i).set(newParameterValue);
        }
    }

    private List<Double> getClosest(List<Double> hyperParameter) {
        double closestLogarithmicDistanceSquaredYet = Double.MAX_VALUE;
        double newLogarithmicDistanceSquared;
        List<Double> result = rewardFunctionHyperParameters.get(0);

        for (List<Double> rewardFunctionHyperParameter : rewardFunctionHyperParameters) {
            newLogarithmicDistanceSquared = 0;
            for (int j = 0; j < rewardFunctionHyperParameter.size(); j++) {
                double newLogarithmicDistance;
                newLogarithmicDistance = Math.log(Math.abs(rewardFunctionHyperParameter.get(j) - hyperParameter.get(j)));
                newLogarithmicDistanceSquared += newLogarithmicDistance * newLogarithmicDistance;
            }
            if (closestLogarithmicDistanceSquaredYet > newLogarithmicDistanceSquared
            && newLogarithmicDistanceSquared > 0.00001) {
                result = rewardFunctionHyperParameters.get(0);
            }
        }

        for(int i = 0; i < hyperParameter.size(); i++) {
            result.set(i, Math.abs(hyperParameter.get(i) - result.get(i)));
        }

        return result;
    }
}
