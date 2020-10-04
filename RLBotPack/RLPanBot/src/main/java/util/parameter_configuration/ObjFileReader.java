package util.parameter_configuration;

import util.shapes.meshes.Mesh3DBuilder;
import util.shapes.meshes.Mesh3D;
import util.vector.Vector3;
import util.vector.Vector3Int;

import java.util.Arrays;
import java.util.List;

public class ObjFileReader {

    public static final String MESHES_PATH = "src\\main\\resources\\maps";
    public static final String STANDARD_MAP_MESH_GEOMETRY_PATH = MESHES_PATH + "\\standard_map_mesh.obj";

    public static Mesh3D loadMeshFromFile(String fileName) {
        final List<String> fileContent = IOFile.getFileContent(fileName);

        final Mesh3DBuilder mesh3DBuilder = new Mesh3DBuilder();

        for(String fileLine: fileContent) {
            final List<String> lineParameters = getLineParameters(fileLine);
            if(isValidLineLength(lineParameters)) {
                if(isVertex(lineParameters)) {
                    final Vector3 vertex = parseVertex(lineParameters);
                    mesh3DBuilder.addVertex(vertex);
                }
                else if(isTriangle(lineParameters)) {
                    final Vector3Int vertexReferences = parseTriangle(lineParameters);
                    final int vertexIndex0 = vertexReferences.x;
                    final int vertexIndex1 = vertexReferences.y;
                    final int vertexIndex2 = vertexReferences.z;
                    mesh3DBuilder.addTriangle(vertexIndex0, vertexIndex1, vertexIndex2);
                }
            }
        }

        return mesh3DBuilder.build();
    }

    private static List<String> getLineParameters(final String fileLine) {
        return Arrays.asList(fileLine.split(" "));
    }

    private static boolean isValidLineLength(final List<String> lineParameters) {
        return lineParameters.size() == 4;
    }

    private static boolean isVertex(final List<String> lineParameters) {
        return lineParameters.get(0).equals("v");
    }

    private static boolean isTriangle(final List<String> lineParameters) {
        return lineParameters.get(0).equals("f");
    }

    private static Vector3 parseVertex(final List<String> lineParameters) {
        final double positionX = -Double.valueOf(lineParameters.get(2));
        final double positionY = Double.valueOf(lineParameters.get(1));
        final double positionZ = Double.valueOf(lineParameters.get(3));

        return new Vector3(positionX, positionY, positionZ);
    }

    private static Vector3Int parseTriangle(final List<String> lineParameters) {
        final int vertexReference0 = Integer.valueOf(lineParameters.get(1)) - 1;
        final int vertexReference1 = Integer.valueOf(lineParameters.get(2)) - 1;
        final int vertexReference2 = Integer.valueOf(lineParameters.get(3)) - 1;

        return new Vector3Int(vertexReference0, vertexReference1, vertexReference2);
    }
}
