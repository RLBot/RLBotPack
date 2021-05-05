package util.machine_learning_models.generic_data_structure.generic_data;

public interface GenericData {
    public void set(double newData);
    public double get();
    public GenericData copy();
}
