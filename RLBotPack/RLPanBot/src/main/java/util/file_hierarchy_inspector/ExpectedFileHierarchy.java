package util.file_hierarchy_inspector;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class ExpectedFileHierarchy {

    private String hierarchyRoot;
    private List<ExpectedFileHierarchy> expectedFileHierarchyList;
    private List<String> expectedFileList;

    public ExpectedFileHierarchy(String hierarchyRoot) {
        this.hierarchyRoot = hierarchyRoot;
        this.expectedFileHierarchyList = new ArrayList<>();
        this.expectedFileList = new ArrayList<>();
    }

    public ExpectedFileHierarchy withFolder(ExpectedFileHierarchy folder) {
        expectedFileHierarchyList.add(folder);
        return this;
    }

    public ExpectedFileHierarchy withFile(String fileName) {
        expectedFileList.add("\\" + fileName);

        return this;
    }

    public boolean inspect() {
        boolean isInRule = true;

        // test the root folder
        File root = new File(hierarchyRoot);
        if(!root.exists()) {
            isInRule = false;
        }
        // test all files
        for(String fileName: expectedFileList) {
            File fileToTest = new File(hierarchyRoot + "\\" + fileName);
            if(!fileToTest.exists()) {
                isInRule = false;
            }
        }
        // test all folders (and all files and folders recursively)
        for(ExpectedFileHierarchy folder: expectedFileHierarchyList) {
            if(!folder.inspect()) {
                isInRule = false;
            }
        }

        return isInRule;
    }

    public ExpectedFileHierarchy getMissingFileHierarchy() {
        ExpectedFileHierarchy missingFileHierarchy = new ExpectedFileHierarchy(hierarchyRoot);

        // test all fileNames
        for(String fileName: expectedFileList) {
            File fileToTest = new File(hierarchyRoot + "\\" + fileName);
            if(!fileToTest.exists()) {
                missingFileHierarchy.withFile(fileName);
            }
        }
        // test all folderNames (and all file and folder names recursively)
        for(ExpectedFileHierarchy folder: expectedFileHierarchyList) {
            if(!folder.inspect()) {
                missingFileHierarchy.withFolder(new ExpectedFileHierarchy(folder.hierarchyRoot));
            }
        }

        return missingFileHierarchy;
    }

    @Override
    public String toString() {
        return "Expected file hierarchy:\n"
                + toString(0);
    }

    private String toString(int numberOfTabulations) {
        StringBuilder result;

        // put n tabulations if we're in the nth folder deep down from root
        StringBuilder tabulations = new StringBuilder();
        for(int i = 0; i < numberOfTabulations; i++) {
            tabulations.append("\t");
        }

        // add root folder name
        result = new StringBuilder(tabulations + hierarchyRoot + "\n");

        // add all file names
        for(String fileName: expectedFileList) {
            result.append("\t").append(tabulations).append(fileName).append("\n");
        }
        // test all files and folders recursively in the folders
        for(ExpectedFileHierarchy folder: expectedFileHierarchyList) {
            result.append(folder.toString(numberOfTabulations + 1));
        }

        return result.toString();
    }
}

