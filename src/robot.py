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

        Ordre : avancer D'ABORD dans la direction actuelle, PUIS mettre
        à jour l'angle. Cela évite l'arc de dépassement (le robot ne
        part pas déjà dans la nouvelle direction avant d'avoir bougé).
        """
        # 1. Avancer dans la direction COURANTE (avant toute rotation)
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed

        # 2. Mettre à jour l'angle pour la frame suivante
        self.angle += delta_angle

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