package util.machine_learning_models.generic_data_structure.generic_data;

import util.parameter_configuration.IOFile;

import java.io.File;

public class SafeLineIncrementFileParameter extends FileParameter implements GenericData {


    public SafeLineIncrementFileParameter(String rootedFileName) {
        super(rootedFileName);
    }

    int incrementThingy = 0;

    @Override
    public void set(double newData) {
        // update the new value
        setParsedData(newData);

        // change the specific parameter that we are interested in
        setUnparsedParameters(IOFile.getFileContent(getRootedFileName()));
        getUnparsedParameters().add(String.valueOf(newData));

        // update the real active files
        IOFile.deleteFile(getOriginalRootedFileName());
        IOFile.createFileWithContent(getOriginalRootedFileName(), getUnparsedParameters());
    }

    @Override
    public double get() {
        return getParsedData();
    }

    @Override
    public FileParameter createCopyInFolder(String rootedCopyFolderName) {
        File copy = new File(rootedCopyFolderName + "\\" + getNotRootedFileNameFromRootedFileName(getRootedFileName()));
        String rootedCopyFileName = copy.getPath();

        if(copy.exists()) {
            IOFile.deleteFile(rootedCopyFileName);
        }
        IOFile.createFileWithContent(rootedCopyFileName, getUnparsedParameters());

        return new SafeLineIncrementFileParameter(rootedCopyFileName);
    }

    @Override
    public GenericData copy() {
        SafeLineIncrementFileParameter safeLineIncrementFileParameter = new SafeLineIncrementFileParameter(getRootedFileName());
        safeLineIncrementFileParameter.setOriginalRootedFileName(getOriginalRootedFileName());
        safeLineIncrementFileParameter.setNumberOfTimesFileChanged(getNumberOfTimesFileChanged());
        return safeLineIncrementFileParameter;
    }

    private String getNotRootedFileNameFromRootedFileName(String rootedFileName) {
        String[] fragmentedFileName = rootedFileName.split("\\\\");
        return fragmentedFileName[fragmentedFileName.length-1];
    }
}
