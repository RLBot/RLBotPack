import math


class Vec3:
    def __init__(self, x: float or 'Vec3' = 0.0, y: float = 0.0, z: float = 0.0):
        if hasattr(x, 'x'):
            # We have been given a vector. Copy it
            self.x = float(x.x)
            self.y = float(x.y) if hasattr(x, 'y') else 0
            self.z = float(x.z) if hasattr(x, 'z') else 0
        else:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

    def __getitem__(self, item: int):
        return (self.x, self.y, self.z)[item]

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, scale: float) -> 'Vec3':
        return Vec3(self.x * scale, self.y * scale, self.z * scale)

    def __rmul__(self, scale: float) -> 'Vec3':
        return self * scale

    def __truediv__(self, scale: float) -> 'Vec3':
        scale = 1 / float(scale)
        return self * scale

    def __str__(self):
        return "Vec3(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"


class Mat33:
    def __init__(self, xx: float or Vec3 or 'Mat33' = 0.0, xy: float or Vec3 = 0.0, xz: float or Vec3 = 0.0,
                 yx: float = 0.0, yy: float = 0.0, yz: float = 0.0, zx: float = 0.0, zy: float = 0.0, zz: float = 0.0):
        """
        Mat33(xx, xy, xz, yx, yy, yz, zx, zy, zz)

        Mat33(mat)
        """

        if isinstance(xx, Mat33):
            self.data = xx.data.copy()
        else:
            self.data = [xx, xy, xz, yx, yy, yz, zx, zy, zz]

    xx = property(lambda self: self.get(0, 0), lambda self: self.set(0, 0), None)
    xy = property(lambda self: self.get(0, 1), lambda self: self.set(0, 1), None)
    xz = property(lambda self: self.get(0, 2), lambda self: self.set(0, 2), None)
    yx = property(lambda self: self.get(1, 0), lambda self: self.set(1, 0), None)
    yy = property(lambda self: self.get(1, 1), lambda self: self.set(1, 1), None)
    yz = property(lambda self: self.get(1, 2), lambda self: self.set(1, 2), None)
    zx = property(lambda self: self.get(2, 0), lambda self: self.set(2, 0), None)
    zy = property(lambda self: self.get(2, 1), lambda self: self.set(2, 1), None)
    zz = property(lambda self: self.get(2, 2), lambda self: self.set(2, 2), None)

    def __getitem__(self, item: int):
        return self.data[item]

    def __setitem__(self, key: int, value: float):
        self.data[key] = value

    def get(self, row: int, col: int) -> float:
        return self.data[row * 3 + col]

    def set(self, row: int, col: int, val: float):
        self.data[row * 3 + col] = val

    def __add__(self, other: 'Mat33') -> 'Mat33':
        mat = Mat33()
        for i in range(9):
            mat[i] = self[i] + other[i]
        return mat

    def __sub__(self, other: 'Mat33') -> 'Mat33':
        mat = Mat33()
        for i in range(9):
            mat[i] = self[i] - other[i]
        return mat

    def __neg__(self):
        mat = Mat33()
        for i in range(9):
            mat[i] = -self[i]
        return mat

    def __mul__(self, scale: float or 'Mat33') -> 'Mat33':
        mat = Mat33()
        if isinstance(scale, Mat33):
            for i in range(9):
                mat[i] = self[i] * scale[i]
        else:
            for i in range(9):
                mat[i] = self[i] * scale
        return mat

    def __rmul__(self, scale):
        return self * scale

    def __truediv__(self, scale: float) -> 'Mat33':
        scale = 1 / float(scale)
        return self * scale

    def __str__(self):
        return "Mat33(" + str(self.xx) + ", " + str(self.xy) + ", " + str(self.xz) + ", " \
               + str(self.yx) + ", " + str(self.yy) + ", " + str(self.yz) + ", " \
               + str(self.zx) + ", " + str(self.zy) + ", " + str(self.zz) + ")"

    def col(self, n: int) -> Vec3:
        return Vec3(self.get(0, n), self.get(1, n), self.get(2, n))

    def row(self, n: int) -> Vec3:
        return Vec3(self.get(n, 0), self.get(n, 1), self.get(n, 2))

    @staticmethod
    def of(v: float) -> 'Mat33':
        return Mat33(v, v, v, v, v, v, v, v, v)

    @staticmethod
    def from_rows(row_a: Vec3, row_b: Vec3, row_c: Vec3) -> 'Mat33':
        return Mat33(
            row_a.x, row_a.y, row_a.z,
            row_b.x, row_b.y, row_b.z,
            row_c.x, row_c.y, row_c.z
        )

    @staticmethod
    def from_columns(col_a: Vec3, col_b: Vec3, col_c: Vec3) -> 'Mat33':
        return Mat33(
            col_a.x, col_b.x, col_c.x,
            col_a.y, col_b.y, col_c.y,
            col_a.z, col_b.z, col_c.z
        )

    @staticmethod
    def identity():
        return Mat33(1, 0, 0, 0, 1, 0, 0, 0, 1)


def xy(vec: Vec3) -> Vec3:
    return Vec3(vec.x, vec.y, 0.0)


def norm(vec: Vec3) -> float:
    return math.sqrt(vec.x ** 2 + vec.y ** 2 + vec.z ** 2)


def normalize(vec: Vec3) -> Vec3:
    return vec / norm(vec)


def dot(mat1: Vec3 or Mat33, mat2: Vec3 or Mat33) -> float or Vec3 or Mat33:
    if isinstance(mat1, Mat33) and isinstance(mat2, Mat33):
        # Mat dot Mat -> Mat
        res = Mat33()
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    v = res.get(i, j) + mat1.get(i, k) * mat2.get(k, j)
                    res.set(i, j, v)
        return res

    elif isinstance(mat1, Mat33) and isinstance(mat2, Vec3):
        # Mat dot Vec -> Vec
        return Vec3(
            mat1.xx * mat2.x + mat1.xy * mat2.y + mat1.xz * mat2.z,
            mat1.yx * mat2.x + mat1.yy * mat2.y + mat1.yz * mat2.z,
            mat1.zx * mat2.x + mat1.zy * mat2.y + mat1.zz * mat2.z
        )

    elif isinstance(mat1, Vec3) and isinstance(mat2, Mat33):
        # Vec dot Mat -> Vec
        return Vec3(
            mat1.x * mat2.xx + mat1.y * mat2.yx + mat1.z * mat2.zx,
            mat1.x * mat2.xy + mat1.y * mat2.yy + mat1.z * mat2.zy,
            mat1.x * mat2.xz + mat1.y * mat2.yz + mat1.z * mat2.zz
        )

    else:
        # Vec dot Vec
        return mat1.x * mat2.x + mat1.y * mat2.y + mat1.z * mat2.z


def cross(vecA: Vec3, vecB: Vec3) -> Vec3:
    return Vec3(
        vecA.y * vecB.z - vecA.z * vecB.y,
        vecA.z * vecB.x - vecA.x * vecB.z,
        vecA.x * vecB.y - vecA.y * vecB.x
    )


def transpose(mat: Mat33) -> Mat33:
    matT = Mat33()
    for i in range(3):
        for j in range(3):
            matT.set(j, i, mat.get(i, j))
    return matT


def fnorm(mat: Mat33) -> float:
    sum = 0.0
    for i in range(9):
        sum += mat[i]
    return math.sqrt(sum)


def tr(mat: Mat33) -> float:
    return mat.xx + mat.yy + mat.zz


def det(mat: Mat33) -> float:
    return mat.get(0, 0) * mat.get(1, 1) * mat.get(2, 2) + mat.get(0, 1) * mat.get(1, 2) * mat.get(2, 0) + \
           mat.get(0, 2) * mat.get(1, 0) * mat.get(2, 1) - mat.get(0, 0) * mat.get(1, 2) * mat.get(2, 1) - \
           mat.get(0, 1) * mat.get(1, 0) * mat.get(2, 2) - mat.get(0, 2) * mat.get(1, 1) * mat.get(2, 0)


def inv(mat: Mat33) -> Mat33:
    invm = Mat33()

    invdet = 1.0 / det(mat)

    invm.set(0, 0, (mat.get(1, 1) * mat.get(2, 2) - mat.get(1, 2) * mat.get(2, 1)) * invdet)
    invm.set(0, 1, (mat.get(0, 2) * mat.get(2, 1) - mat.get(0, 1) * mat.get(2, 2)) * invdet)
    invm.set(0, 2, (mat.get(0, 1) * mat.get(1, 2) - mat.get(0, 2) * mat.get(1, 1)) * invdet)
    invm.set(1, 0, (mat.get(1, 2) * mat.get(2, 0) - mat.get(1, 0) * mat.get(2, 2)) * invdet)
    invm.set(1, 1, (mat.get(0, 0) * mat.get(2, 2) - mat.get(0, 2) * mat.get(2, 0)) * invdet)
    invm.set(1, 2, (mat.get(0, 2) * mat.get(1, 0) - mat.get(0, 0) * mat.get(1, 2)) * invdet)
    invm.set(2, 0, (mat.get(1, 0) * mat.get(2, 1) - mat.get(1, 1) * mat.get(2, 0)) * invdet)
    invm.set(2, 1, (mat.get(0, 1) * mat.get(2, 0) - mat.get(0, 0) * mat.get(2, 1)) * invdet)
    invm.set(2, 2, (mat.get(0, 0) * mat.get(1, 1) - mat.get(0, 1) * mat.get(1, 0)) * invdet)

    return invm

