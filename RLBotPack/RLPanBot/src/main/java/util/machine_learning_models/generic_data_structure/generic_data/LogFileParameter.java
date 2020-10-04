package util.machine_learning_models.generic_data_structure.generic_data;

import util.parameter_configuration.IOFile;

import java.io.File;

public class LogFileParameter extends FileParameter implements GenericData {

    private int lineNumberOfParameterInFile;

    public LogFileParameter(String rootedFileName, int lineNumberOfParameterInFile) {
        super(rootedFileName);
        this.lineNumberOfParameterInFile = lineNumberOfParameterInFile;
        setParsedData(Double.valueOf(getUnparsedParameters().get(this.lineNumberOfParameterInFile)));
    }

    @Override
    public void set(double newData) {
        // update the new value
        setParsedData(newData);

        // change the specific parameter that we are interested in
        setUnparsedParameters(IOFile.getFileContent(getRootedFileName()));
        getUnparsedParameters().set(lineNumberOfParameterInFile, String.valueOf(newData));

        // modify the file with the new parameter (create a new file with slightly changed name and new parameter)
        changeSlightlyFileName();

        if(getLinkedFileParameter() != null) {
            getLinkedFileParameter().resynchronizeWith(this);
        }

        IOFile.createFileWithContent(getRootedFileName(), getUnparsedParameters());

        // update the real active files that the bot uses too
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

        return new LogFileParameter(rootedCopyFileName, lineNumberOfParameterInFile);
    }

    @Override
    public GenericData copy() {
        LogFileParameter logFileParameter = new LogFileParameter(getRootedFileName(), lineNumberOfParameterInFile);
        logFileParameter.setOriginalRootedFileName(getOriginalRootedFileName());
        return logFileParameter;
    }

    private void changeSlightlyFileName() {
        // add a number at the end of the file so we can know which iteration it's at
        setRootedFileName(getFileNameWithoutExtension() + "_" + getNumberOfTimesFileChanged() + "." + getFileExtension());
        setNumberOfTimesFileChanged(getNumberOfTimesFileChanged() + 1);
    }

    private String getNotRootedFileNameFromRootedFileName(String rootedFileName) {
        String[] fragmentedFileName = rootedFileName.split("\\\\");
        return fragmentedFileName[fragmentedFileName.length-1];
    }
}
