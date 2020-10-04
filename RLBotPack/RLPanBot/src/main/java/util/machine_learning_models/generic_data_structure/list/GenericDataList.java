package util.machine_learning_models.generic_data_structure.list;

import util.machine_learning_models.generic_data_structure.generic_data.GenericData;

import java.util.List;

public abstract class GenericDataList<D extends GenericData> {

    private List<D> dataHandlerList;

    public GenericDataList(List<D> dataHandlerList) {
        this.dataHandlerList = dataHandlerList;
    }

    public List<D> getDataHandlerList() {
        return dataHandlerList;
    }

    public void setDataHandlerList(List<D> dataHandlerList) {
        this.dataHandlerList = dataHandlerList;
    }
}
