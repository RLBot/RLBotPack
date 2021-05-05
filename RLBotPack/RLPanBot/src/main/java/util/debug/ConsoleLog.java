package util.debug;

import java.util.ArrayList;

public class ConsoleLog {

    private ArrayList<Object> loggableObjectList;
    private ArrayList<String> labelList;

    public ConsoleLog() {
        loggableObjectList = new ArrayList<>();
        labelList = new ArrayList<>();
    }

    public ConsoleLog with(String logLabel, Object obj) {
        labelList.add(logLabel + ": ");
        loggableObjectList.add(obj);

        return this;
    }

    public ConsoleLog with(String logLabel) {
        labelList.add(logLabel);
        loggableObjectList.add(null);

        return this;
    }

    @Override
    public String toString() {
        String result = "";

        for(int i = 0; i < labelList.size(); i++) {
            try {
                result += labelList.get(i) + ": " + loggableObjectList.get(i).toString() + '\n';
            }
            catch(Exception e) {
                result += labelList.get(i) + '\n';
            }
        }

        return result;
    }
}
