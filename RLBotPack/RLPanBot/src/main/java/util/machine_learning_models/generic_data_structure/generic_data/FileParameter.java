package util.machine_learning_models.generic_data_structure.generic_data;

import util.parameter_configuration.IOFile;

import java.util.List;

public abstract class FileParameter implements GenericData {

    private String originalRootedFileName;
    private String rootedFileName;
    private StringBuilder fileNameWithoutExtension;
    private String fileExtension;
    private List<String> unparsedParameters;
    private int numberOfTimesFileChanged;
    private double parsedData;
    private FileParameter linkedFileParameter;

    FileParameter(String rootedFileName) {
        // parse filename into variables
        this.originalRootedFileName = rootedFileName;
        this.rootedFileName = rootedFileName;
        this.fileNameWithoutExtension = new StringBuilder();
        String[] fragmentedFileName = rootedFileName.split("\\.");
        if(fragmentedFileName.length < 2) {
            this.fileNameWithoutExtension.append(fragmentedFileName[0]);
            this.fileExtension = "";
        }
        else {
            for(int i = 0; i < fragmentedFileName.length-1; i++) {
                this.fileNameWithoutExtension.append(fragmentedFileName[i]);
            }
            this.fileExtension = fragmentedFileName[fragmentedFileName.length-1];
        }
        this.numberOfTimesFileChanged = 0;
        unparsedParameters = IOFile.getFileContent(rootedFileName);
        parsedData = 0;
    }

    public void resynchronizeWith(FileParameter fileParameter) {
        if(fileParameter.getOriginalRootedFileName().equals(this.getOriginalRootedFileName())) {
            if(this.getNumberOfTimesFileChanged() > fileParameter.getNumberOfTimesFileChanged()) {
                fileParameter.setRootedFileName(this.getRootedFileName());
                fileParameter.setNumberOfTimesFileChanged(this.getNumberOfTimesFileChanged());
            }
            else {
                this.setRootedFileName(fileParameter.getRootedFileName());
                this.setNumberOfTimesFileChanged(fileParameter.getNumberOfTimesFileChanged());
            }
        }
    }

    public void linkWith(FileParameter fileParameter) {
        this.linkedFileParameter = fileParameter;
    }

    public FileParameter getLinkedFileParameter() {
        return linkedFileParameter;
    }

    public abstract FileParameter createCopyInFolder(String rootedCopyFolderName);

    public StringBuilder getFileNameWithoutExtension() {
        return fileNameWithoutExtension;
    }

    public void setFileNameWithoutExtension(StringBuilder fileNameWithoutExtension) {
        this.fileNameWithoutExtension = fileNameWithoutExtension;
    }

    public String getFileExtension() {
        return fileExtension;
    }

    public void setFileExtension(String fileExtension) {
        this.fileExtension = fileExtension;
    }

    public List<String> getUnparsedParameters() {
        return unparsedParameters;
    }

    public void setUnparsedParameters(List<String> unparsedParameters) {
        this.unparsedParameters = unparsedParameters;
    }

    public int getNumberOfTimesFileChanged() {
        return numberOfTimesFileChanged;
    }

    public void setNumberOfTimesFileChanged(int numberOfTimesFileChanged) {
        this.numberOfTimesFileChanged = numberOfTimesFileChanged;
    }

    public double getParsedData() {
        return parsedData;
    }

    public void setParsedData(double parsedData) {
        this.parsedData = parsedData;
    }

    public String getOriginalRootedFileName() {
        return originalRootedFileName;
    }

    public void setOriginalRootedFileName(String originalRootedFileName) {
        this.originalRootedFileName = originalRootedFileName;
    }

    public String getRootedFileName() {
        return rootedFileName;
    }

    public void setRootedFileName(String rootedFileName) {
        this.rootedFileName = rootedFileName;
    }
}
