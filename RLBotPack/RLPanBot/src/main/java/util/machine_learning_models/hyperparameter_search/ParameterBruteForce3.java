package util.machine_learning_models.hyperparameter_search;

import util.machine_learning_models.generic_data_structure.generic_data.GenericData;
import util.machine_learning_models.generic_data_structure.list.GenericDataList;

import java.util.ArrayList;
import java.util.List;

public class ParameterBruteForce3<D extends GenericData> {

    private static final int NUMBER_OF_FULL_SEARCH_TO_DO_BEFORE_CONSIDERED_FINISHED = 1000;
    private static final double EXPONENTIAL_RANDOM_SCALE_PROBABILITY = 0.5;

    private List<D> currentlyUsedParametersByBot;
    private List<SampleParameters> pointsOnRewardFunction;
    private int numberOfFullSearchDone;

    public ParameterBruteForce3(GenericDataList<D> dataRepresentation) {
        this.currentlyUsedParametersByBot = dataRepresentation.getDataHandlerList();
        this.pointsOnRewardFunction = new ArrayList<>();
        this.numberOfFullSearchDone = 0;
    }

    public void sendSearchResult(double evaluationResult) {
        if(pointsOnRewardFunction.size() > 0) {
            System.out.println("new cost / best cost: " + evaluationResult / pointsOnRewardFunction.get(0).getRewardValue());
        }
        addPointToRewardFunction(currentlyUsedParametersByBot, evaluationResult);
    }

    public void nextHypothesis() {
        // get a random point.
        // it is more likely to get the first one than to get the last one in the sorted array of hyperParameters.
        SampleParameters parameterToMutate = getPointFromExponentialRandom();

        // find a ratio for the search range depending on how long the search has been running.
        double rangeRatio = (pointsOnRewardFunction.indexOf(parameterToMutate) + 1)/(double)(pointsOnRewardFunction.size());

        rangeRatio = Math.pow(rangeRatio, 4);

        System.out.println("range ratio: " + rangeRatio);

        // get a mutated parameter list from the ratio.
        List<Double> mutatedParameters = parameterToMutate.makeChild(rangeRatio);

        // update the real bot's parameters
        for(int i = 0; i < mutatedParameters.size(); i++) {
            currentlyUsedParametersByBot.get(i).set(mutatedParameters.get(i));
        }

        // update the number of search done so far.
        numberOfFullSearchDone++;
    }

    public boolean isDoneSearching() {
        return numberOfFullSearchDone >= NUMBER_OF_FULL_SEARCH_TO_DO_BEFORE_CONSIDERED_FINISHED;
    }

    private void addPointToRewardFunction(List<D> hyperParameter, double evaluation) {
        List<Double> currentlyUsedParametersByBotInDouble = new ArrayList<>();

        // retrieve double value from GenericData and put the list in the reward function
        for(D data: hyperParameter) {
            currentlyUsedParametersByBotInDouble.add(data.get());
        }
        pointsOnRewardFunction.add(new SampleParameters(currentlyUsedParametersByBotInDouble, evaluation));

        pointsOnRewardFunction.sort((o1, o2) -> {
            if(o1.getRewardValue() < o2.getRewardValue()) {
                return 1;
            }
            else if(o1.getRewardValue() > o2.getRewardValue()) {
                return -1;
            }
            return 0;
        });
    }

    private SampleParameters getPointFromExponentialRandom() {
        // pointsOnRewardFunction list is considered sorted here

        double randomNumber = Math.random();
        int index = 0;

        while(randomNumber < EXPONENTIAL_RANDOM_SCALE_PROBABILITY
                && index < pointsOnRewardFunction.size() - 1) {
            randomNumber = Math.random();
            index++;
        }

        System.out.println("computed index: " + index);
        System.out.println("best evaluation: " + pointsOnRewardFunction.get(0).getRewardValue());

        return pointsOnRewardFunction.get(index);
    }
}
