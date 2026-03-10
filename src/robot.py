# src/robot.py
import math

class Robot:

    def __init__(self, x, y, angle, speed=3):
        self.x     = float(x)
        self.y     = float(y)
        self.angle = float(angle)  # en degrés
        self.speed = speed
        self.trace = []            # historique des positions

    def update(self, delta_angle):
        """
        Met à jour la position du robot.
        delta_angle : correction calculée par le contrôleur flou (degrés)
        """
        # 1. Tourner
        self.angle += delta_angle

        # 2. Avancer dans la nouvelle direction
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed

        # 3. Mémoriser la position pour tracer la trajectoire
        self.trace.append((self.x, self.y))
        if len(self.trace) > 500:
            self.trace.pop(0)

    def reset(self, x, y, angle):
        """Remet le robot à sa position de départ."""
        self.x     = float(x)
        self.y     = float(y)
        self.angle = float(angle)
        self.trace = []