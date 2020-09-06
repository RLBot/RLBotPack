import math
import unittest
from physics.math.vector3 import Vec3
from physics.math.matrix3 import Orientation3


class Vec3Tests(unittest.TestCase):
    """"Unittests for the Vec3 class."""

    """"Magic methods"""

    def test_constructor(self):
        Vec3(10, 15, 20)

    def test_get_item(self):
        vec = Vec3(10, 15, 20)

        self.assertEqual(vec[0], 10)
        self.assertEqual(vec[1], 15)
        self.assertEqual(vec[2], 20)

    def test_set_item(self):
        vec = Vec3(10, 15, 20)
        vec[0] = 5
        vec[1] = 10
        vec[2] = 0

        self.assertEqual(vec[0], 5)
        self.assertEqual(vec[1], 10)
        self.assertEqual(vec[2], 0)

    def test_str(self):
        vec = Vec3(10, 15, 20)
        self.assertEqual(str(vec), "X: 10, Y: 15, Z:20")

    def test_repr(self):
        vec = Vec3(10, 15, 20)
        self.assertEqual(str(vec), "X: 10, Y: 15, Z:20")

    def test_eq(self):
        vec_a = Vec3(10, 15, 20)
        vec_b = Vec3(10, 15, 20)
        vec_other = Vec3(10, 15, 25)
        self.assertEqual(vec_a, vec_b)
        self.assertNotEqual(vec_a, vec_other)
        self.assertNotEqual(vec_other, vec_b)

    def test_add(self):
        vec_a = Vec3(5, 5, 20)
        vec_b = Vec3(10, 15, 5)
        vec_other = Vec3(15, 20, 25)

        self.assertEqual(vec_a + vec_b, vec_other)
        self.assertEqual(vec_a + [10, 15, 5], vec_other)
        self.assertEqual(vec_a + 10, Vec3(15, 15, 30))
        self.assertNotEqual(vec_a + 10, vec_other)

    def test_radd(self):
        vec_a = Vec3(5, 5, 20)
        vec_b = Vec3(10, 15, 5)
        vec_other = Vec3(15, 20, 25)

        self.assertEqual(vec_b + vec_a, vec_other)
        self.assertEqual([10, 15, 5] + vec_a, vec_other)
        self.assertEqual(10 + vec_a, Vec3(15, 15, 30))
        self.assertNotEqual(10 + vec_a, vec_other)

    def test_sub(self):
        vec_a = Vec3(5, 5, 20)
        vec_b = Vec3(10, 15, 5)

        self.assertEqual(vec_a - vec_b, Vec3(-5, -10, 15))

    def test_neg(self):
        vec_a = Vec3(5, 5, 20)
        self.assertEqual(-vec_a, Vec3(-5, -5, -20))
        self.assertNotEqual(vec_a, Vec3(-5, -5, -20))

    def test_mul(self):
        vec_a = Vec3(5, 5, 20)
        vec_b = Vec3(10, 15, 5)
        self.assertEqual(vec_a * vec_b, 225)
        self.assertEqual(vec_a * 5, Vec3(25, 25, 100))

        mainvector = Vec3(10, 10, 10)
        vec1 = Vec3(1, 1, 1)
        vec2 = Vec3(0.5, 1, 1)
        vec3 = Vec3(-2, 2, 2)
        vec4 = Vec3(0, 1, 0)
        self.assertEqual(mainvector * vec1, 30)
        self.assertEqual(mainvector * vec2, 25)
        self.assertEqual(mainvector * vec3, 20)
        self.assertEqual(mainvector * vec4, 10)

    def test_rmul(self):
        vec_a = Vec3(5, 5, 20)
        vec_b = Vec3(10, 15, 5)
        self.assertEqual(vec_b * vec_a, 225)
        self.assertEqual(5 * vec_a, Vec3(25, 25, 100))

        mainvector = Vec3(10, 10, 10)
        vec1 = Vec3(1, 1, 1)
        vec2 = Vec3(0.5, 1, 1)
        vec3 = Vec3(-2, 2, 2)
        vec4 = Vec3(0, 1, 0)
        self.assertEqual(vec1 * mainvector, 30)
        self.assertEqual(vec2 * mainvector, 25)
        self.assertEqual(vec3 * mainvector, 20)
        self.assertEqual(vec4 * mainvector, 10)

    def test_truediv(self):
        # TODO:
        pass

    def test_rtruediv(self):
        # TODO:
        pass

    def test_len(self):
        vec3 = Vec3(0, 1, 2)
        self.assertEqual(len(vec3), 3)

    """Functions"""

    def test_magnitude(self):
        # TODO
        vector = Vec3(10, 15, 20).magnitude()
        self.assertEqual(vector, math.sqrt(725))
        self.assertEqual(Vec3(1, 1, 0.5).magnitude(), 1.5)

    def test_normalize(self):
        vector = Vec3(1, 1, 1).normalize()
        ans = 1 / math.sqrt(3)
        self.assertAlmostEqual(vector.normalize()[0], ans, 5)
        self.assertAlmostEqual(vector.normalize()[1], ans, 5)
        self.assertAlmostEqual(vector.normalize()[2], ans, 5)

    def test_cross(self):
        vec1 = Vec3(10, 15, 20)
        vec2 = Vec3(1, 1, 1)
        vec3 = Vec3(2, -5, 10)
        self.assertEqual(vec1.cross(vec2), Vec3(-5, 10, -5))
        self.assertEqual(vec1.cross(vec3), Vec3(250, -60, -80))

    def test_flatten(self):
        vec1 = Vec3(1, 1, 1)
        self.assertEqual(vec1.flatten(), Vec3(1, 1, 0))

    def test_angle_2d(self):
        vec1 = Vec3(1, 0, 0)
        vec2 = Vec3(1, 1, 0)
        vec3 = Vec3(1, -1, 0)
        self.assertAlmostEqual(vec1.angle_2d(vec2), 0.7854, 3)
        self.assertAlmostEqual(vec2.angle_2d(vec3), 1.5708, 3)

    def test_rotate_2d(self):
        # TODO
        pass

    def test_clamp(self):
        # TODO
        pass

    def test_element_wise_division(self):
        # TODO:
        pass

    def test_element_wise_multiplication(self):
        # TODO:
        pass

    def test_angle_3d(self):
        # TODO:
        pass

    def test_copy(self):
        # TODO:
        pass

    def test_render(self):
        # TODO:
        pass


class Orientation3Tests(unittest.TestCase):
    """"Unittests for the Vec3 class."""

    """"Magic methods"""

    def test_constructor(self):
        Orientation3(30, 60, 45)

    def test_get_item(self):
        ori = Orientation3(1, 0.4, 0.2)

        vec_0 = ori[0]
        vec_1 = ori[1]
        vec_2 = ori[2]

        self.assertAlmostEqual(vec_0[0], 0.4977, 3)
        self.assertAlmostEqual(vec_0[1], 0.2104, 3)
        self.assertAlmostEqual(vec_0[2], 0.8415, 3)
        self.assertAlmostEqual(vec_1[0], -0.2277, 3)
        self.assertAlmostEqual(vec_1[1], 0.9678, 3)
        self.assertAlmostEqual(vec_1[2], -0.1073, 3)
        self.assertAlmostEqual(vec_2[0], -0.837, 3)
        self.assertAlmostEqual(vec_2[1], -0.1382, 3)
        self.assertAlmostEqual(vec_2[2], 0.5295, 3)

    def test_mul(self):
        ori = Orientation3(1, 0, 0)

        vec = Vec3(1, 0, 0)

        res = ori * vec
        self.assertAlmostEqual(res[0], 0.5403, 3)
        self.assertAlmostEqual(res[1], 0, 3)
        self.assertAlmostEqual(res[2], -0.8415, 3)

        ori2 = Orientation3(1, 0.4, 0.2)
        vec2 = Vec3(7.65, 2.64, 3.50)

        res2 = ori2 * vec2

        self.assertAlmostEqual(res2[0], 7.3081, 3)
        self.assertAlmostEqual(res2[1], 0.4375, 3)
        self.assertAlmostEqual(res2[2], -4.9146, 3)

    def test_str(self):
        ori = Orientation3(1, 0.4, 0.2)
        str(ori)


if __name__ == '__main__':
    unittest.main()
