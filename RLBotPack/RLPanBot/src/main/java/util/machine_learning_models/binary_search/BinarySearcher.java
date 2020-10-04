package util.machine_learning_models.binary_search;

import util.machine_learning_models.generic_data_structure.generic_data.GenericData;

public class BinarySearcher {

    private static final double DEFAULT_SEARCH_RANGE = 1500;
    private static final double DEFAULT_RESTART_SEARCH_NARROWING_COEFFICIENT = 1.2;
    private static final double DEFAULT_PRECISION_FRACTION_FROM_STARTING_RANGE = 10;

    private GenericData parameterToOptimize;
    private GenericData bestParameter;
    private double searchRange;
    private double searchRangeAtRestart;
    private double bestHypothesis;
    private double evaluationOfLeftSearch;
    private double evaluationOfRightSearch;
    private double currentBestEvaluation;
    private SearchState currentSearchPosition;

    public BinarySearcher(GenericData dataHandler) {
        this.parameterToOptimize = dataHandler;
        this.bestParameter = dataHandler.copy();
        this.bestHypothesis = DEFAULT_SEARCH_RANGE;
        this.searchRange = DEFAULT_SEARCH_RANGE;
        this.searchRangeAtRestart = DEFAULT_SEARCH_RANGE/2;
        this.currentBestEvaluation = Double.MIN_VALUE;
        this.evaluationOfLeftSearch = 0;
        this.evaluationOfRightSearch = 0;
        this.currentSearchPosition = SearchState.START;
    }

    public void confrontHypothesis(double resultFromHypothesis) {
        // if we're doing our first search round (a search round is a topple: left and right both needs to
        // be searched before we can conclude anything)
        //
        if(currentSearchPosition == SearchState.LEFT) {
            evaluationOfLeftSearch = resultFromHypothesis;
        }
        else if(currentSearchPosition == SearchState.RIGHT) {
            evaluationOfRightSearch = resultFromHypothesis;
        }
        else if(currentSearchPosition == SearchState.START) {
            currentBestEvaluation = resultFromHypothesis;
        }
        else if(currentSearchPosition == SearchState.RESTART) {}
    }

    public void nextHypothesis() {
        // if we were testing the left hypothesis,
        // then we're now going to test the right one. We'll
        // also update the best hypothesis, as we now have both
        // the right and the left test that have been done thoroughly.

        // if we were testing the right one, then we're now going to
        // test the right one.

        if(currentSearchPosition == SearchState.LEFT) {
            // yes, this is very bad the first time we call this function.
            // Why? Because it directly starts by applying the hypothesis, before even evaluating it.

            // this is due to the fact that the code needs to guess the left value,
            // then do the training pack...
            // then do the right value,
            // then do the training pack again...
            // (yes this class tries to be general, but it has to work with
            // the current code it was originally designed for...)

            // and THEN, in the SAME nextHypothesis() call that searches back to the left hypothesis
            // (just before we update to the left), we need to update the current best value, so the
            // next left hypothesis (which is bestHypothesis + searchRange...) is a narrower one.

            // And so, it is bad at first, but it lets us do the rest of the execution very beautifully.
            // If anyone has a better idea than what I had, I'm very open to discussion :).

            if(currentBestEvaluation < evaluationOfLeftSearch || currentBestEvaluation < evaluationOfRightSearch) {
                if(evaluationOfLeftSearch > evaluationOfRightSearch) {
                    currentBestEvaluation = evaluationOfLeftSearch;
                    bestHypothesis -= searchRange;
                }
                else {
                    currentBestEvaluation = evaluationOfRightSearch;
                    bestHypothesis += searchRange;
                }
                bestParameter = parameterToOptimize.copy();
            }
            searchRange /= 2;
            // update
            double nextHypothesis = bestHypothesis + searchRange;
            parameterToOptimize.set(nextHypothesis);
            currentSearchPosition = SearchState.RIGHT;
        }
        else if(currentSearchPosition == SearchState.RIGHT) {
            double nextHypothesis = bestHypothesis - searchRange;
            parameterToOptimize.set(nextHypothesis);
            currentSearchPosition = SearchState.LEFT;
        }
        else if(currentSearchPosition == SearchState.START || currentSearchPosition == SearchState.RESTART) {
            searchRange /= 2;
            // update
            double nextHypothesis = bestHypothesis + searchRange;
            parameterToOptimize.set(nextHypothesis);
            currentSearchPosition = SearchState.RIGHT;
        }
    }

    public double getCurrentBestEvaluation() {
        return currentBestEvaluation;
    }

    public void setBestEvaluationAsOfYet(double newBestEvaluation) {
        currentBestEvaluation = newBestEvaluation;

        // notify that we just started.
        currentSearchPosition = SearchState.RESTART;
    }

    public void endSearch() {
        // returns the best evaluation value we got as of yet

        // make sure that the best data is the data on which the other binary searches
        // are operating
        parameterToOptimize.set(bestParameter.get());
    }

    public boolean isDoneSearching() {
        return searchRange < getDesiredPrecision();
    }

    public void setBestHypothesis(double bestHypothesis) {
        this.bestHypothesis = bestHypothesis;
    }

    public void setSearchRange(double newSearchRange) {
        searchRange = newSearchRange;
        searchRangeAtRestart = searchRange/DEFAULT_RESTART_SEARCH_NARROWING_COEFFICIENT;
    }

    public void resetSearchRange(double newSearchRangeFactor) {
        searchRange = searchRangeAtRestart * newSearchRangeFactor;

        // notify that we just started.
        currentSearchPosition = SearchState.RESTART;
    }

    private double getDesiredPrecision() {
        return searchRangeAtRestart/DEFAULT_PRECISION_FRACTION_FROM_STARTING_RANGE;
    }

}
