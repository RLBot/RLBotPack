package util.file_hierarchy_inspector;

public class UnexpectedFileHierarchy extends RuntimeException {

    private ExpectedFileHierarchy missingFileHierarchy;

    public UnexpectedFileHierarchy(ExpectedFileHierarchy expectedFileTree) {
        this.missingFileHierarchy = expectedFileTree;
    }

    @Override
    public void printStackTrace() {
        System.out.println("expected file tree is:\n" + missingFileHierarchy + "\n\n" + "Missing elements are:\n" + missingFileHierarchy.getMissingFileHierarchy());
    }

}
