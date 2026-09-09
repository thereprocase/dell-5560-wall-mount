"""Numerical checks for physical-time tracer transport (FreeCAD Python)."""
import unittest
import numpy as np
from render_revh_tracers import Slice, Cloud, PARTICLES, MAX_STEP, rk2_step


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.points = np.array([[0., 0.], [10., 0.], [10., 10.], [0., 10.]])
        self.section = Slice(self.points, np.array([[0, 1, 2], [0, 2, 3]]))

    def test_constant_velocity_uses_physical_units(self):
        positions = np.array([[2., 3.], [4., 5.]])
        field = np.tile([2., -1.], (4, 1))
        result = rk2_step(positions, lambda p, f: self.section.values(p, field), .001)
        np.testing.assert_allclose(result, positions + [2., -1.], atol=1e-12)

    def test_linear_spatial_interpolation(self):
        positions = np.array([[2., 3.], [4., 5.]])
        field = self.points * [.1, .2]
        np.testing.assert_allclose(self.section.values(positions, field), positions * [.1, .2])
        self.assertTrue(np.isnan(self.section.values(np.array([[11., 4.]]), field)).all())

    def test_time_varying_velocity_uses_midpoint(self):
        positions = np.array([[2., 3.]])
        dt = .001
        def velocity(p, fraction):
            return np.tile([1. + 100. * fraction * dt, 0.], (len(p), 1))
        result = rk2_step(positions, velocity, dt)
        np.testing.assert_allclose(result, positions + [1.05, 0.], atol=1e-12)

    def test_solid_body_rotation(self):
        omega = 100.
        field = np.column_stack((-(self.points[:, 1] - 5) * omega / 1000,
                                  (self.points[:, 0] - 5) * omega / 1000))
        position = np.array([[7., 5.]])
        for _ in range(100):
            position = rk2_step(position, lambda p, f: self.section.values(p, field), 1e-5)
        expected = [[5 + 2 * np.cos(.1), 5 + 2 * np.sin(.1)]]
        np.testing.assert_allclose(position, expected, atol=1e-6)

    def test_particles_are_reseeded_at_a_solid_gap(self):
        points = np.array([[0., 0.], [5., 0.], [5., 10.], [0., 10.],
                           [5.2, 0.], [10., 0.], [10., 10.], [5.2, 10.]])
        section = Slice(points, np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]]))
        cloud = Cloud(section, (0., 10., 0., 10.), seed=42)
        cloud.positions[:] = [4.99, 5.]
        cloud.history[:] = cloud.positions
        field = np.tile([5., 0.], (8, 1))
        cloud.step(field, field, 0., .5, MAX_STEP)
        self.assertEqual(cloud.respawned, PARTICLES)
        self.assertTrue(np.isnan(cloud.history).all())
        self.assertTrue(np.all(section.locate(cloud.positions) >= 0))


if __name__ == '__main__':
    unittest.main()
