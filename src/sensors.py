# src/sensors.py
import math

class SensorBar:

    def __init__(self, n_sensors=16, spread=24, distance=22):
        self.n         = n_sensors
        self.half      = n_sensors // 2
        self.spread    = spread
        self.distance  = distance
        self.bits      = [0] * n_sensors
        self.positions = []

    def read(self, robot_x, robot_y, robot_angle, pixel_array):
        rad = math.radians(robot_angle)
        fx =  math.cos(rad)
        fy =  math.sin(rad)
        rx = -math.sin(rad)
        ry =  math.cos(rad)

        cx = robot_x + fx * self.distance
        cy = robot_y + fy * self.distance

        W = pixel_array.shape[0]
        H = pixel_array.shape[1]

        self.bits = []
        self.positions = []

        for i in range(self.n):
            t = (i / (self.n - 1) - 0.5) * 2 * self.spread
            sx = int(round(cx + rx * t))
            sy = int(round(cy + ry * t))
            self.positions.append((sx, sy))

            if 0 <= sx < W and 0 <= sy < H:
                r = int(pixel_array[sx, sy, 0])
                g = int(pixel_array[sx, sy, 1])
                b = int(pixel_array[sx, sy, 2])
                self.bits.append(1 if max(r, g, b) > 128 else 0)
            else:
                self.bits.append(0)

    def compute_GD(self):
        G = 0
        for i in range(self.half):
            weight = 1 << (self.half - 1 - i)
            G += self.bits[i] * weight

        D = 0
        for i in range(self.half):
            weight = 1 << i
            D += self.bits[self.half + i] * weight

        return G, D

    def get_delta(self):
        G, D = self.compute_GD()
        return D - G   # positif = ligne à droite → P → virer droite; négatif = ligne à gauche → N → virer gauche