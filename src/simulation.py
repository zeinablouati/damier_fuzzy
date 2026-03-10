# src/simulation.py
import pygame
import sys
from src.robot   import Robot
from src.sensors import SensorBar
from src.fuzzy   import FuzzyController
from src.circuit import Circuit

# ── Dimensions ────────────────────────────────────────────
WIN_W,  WIN_H  = 1050, 660
SIM_W,  SIM_H  =  750, 620   # zone simulation (gauche)
PANEL_X        =  760         # panneau info (droite)

# ── Couleurs ──────────────────────────────────────────────
C_BG       = ( 10,  10,  15)
C_ACCENT   = (  0, 255, 200)  # cyan
C_ORANGE   = (255, 107,  53)  # orange
C_VIOLET   = (162,  89, 255)  # violet
C_WHITE    = (255, 255, 255)
C_GRAY     = ( 80,  80, 100)
C_PANEL    = ( 18,  18,  28)


class Simulation:

    def __init__(self, fps=60):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Damier Fuzzy — Suivi de ligne")
        self.clock  = pygame.time.Clock()
        self.fps    = fps
        self.paused = True          # démarre en pause
        self.show_sensors = True
        self.show_trace   = True

        # ── Composants ────────────────────────────────────
        self.circuit = Circuit(SIM_W, SIM_H)
        self.sensors = SensorBar(n_sensors=16, spread=50, distance=25)
        self.fuzzy   = FuzzyController()

        sx, sy, sa   = self.circuit.get_start()
        self.robot   = Robot(sx, sy, sa, speed=3)

        # ── Polices ───────────────────────────────────────
        self.font_sm = pygame.font.SysFont("monospace", 12)
        self.font_md = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_lg = pygame.font.SysFont("monospace", 17, bold=True)

        # ── Point d'arrivée ───────────────────────────────
        self.end_x, self.end_y = self.circuit.get_end()
        self.arrived = False
        self.ARRIVE_RADIUS = 30   # pixels de tolérance

        # ── Etat affiché ──────────────────────────────────
        self.last_delta = 0
        self.last_da    = 0.0
        self.last_G     = 0
        self.last_D     = 0

    # ─────────────────────────────────────────────────────
    def run(self):
        """Boucle principale."""
        while True:
            self._handle_events()
            if not self.paused:
                self._update()
            self._draw()
            self.clock.tick(self.fps)

    # ─────────────────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused

                elif event.key == pygame.K_r:
                    self._reset()

                elif event.key == pygame.K_1:
                    self.circuit.load(1); self._reset()
                elif event.key == pygame.K_2:
                    self.circuit.load(2); self._reset()
                elif event.key == pygame.K_3:
                    self.circuit.load(3); self._reset()
            

                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.robot.speed = min(10, self.robot.speed + 1)
                elif event.key == pygame.K_MINUS:
                    self.robot.speed = max(1,  self.robot.speed - 1)

                elif event.key == pygame.K_s:
                    self.show_sensors = not self.show_sensors
                elif event.key == pygame.K_t:
                    self.show_trace = not self.show_trace

    # ─────────────────────────────────────────────────────
    def _reset(self):
        sx, sy, sa = self.circuit.get_start()
        self.robot.reset(sx, sy, sa)
        self.end_x, self.end_y = self.circuit.get_end()
        self.arrived = False
        self.paused  = True

    # ─────────────────────────────────────────────────────
    def _update(self):
        """Un pas de simulation."""
        import math

        pixels = self.circuit.get_pixel_array()

        # 1. Lire les capteurs avec l'angle courant
        self.sensors.read(self.robot.x, self.robot.y,
                          self.robot.angle, pixels)

        # 2. Recherche 90° si ligne perdue
        #    "si il trouve pas → saute de 90° à gauche ou droite"
        if sum(self.sensors.bits) == 0:
            # Essai à gauche (-90°)
            self.sensors.read(self.robot.x, self.robot.y,
                              self.robot.angle - 90, pixels)
            if sum(self.sensors.bits) > 0:
                self.robot.angle -= 90          # virer gauche : ligne trouvée
            else:
                # Essai à droite (+90°)
                self.sensors.read(self.robot.x, self.robot.y,
                                  self.robot.angle + 90, pixels)
                if sum(self.sensors.bits) > 0:
                    self.robot.angle += 90      # virer droite : ligne trouvée
                else:
                    # Aucune direction → relire à l'angle initial
                    self.sensors.read(self.robot.x, self.robot.y,
                                      self.robot.angle, pixels)

        # 3. Calculer G, D, delta
        G, D = self.sensors.compute_GD()
        delta = self.sensors.get_delta()

        # 4. Contrôleur flou → variation d'angle
        da = self.fuzzy.compute(delta)

        # 5. Sauvegarder la position avant déplacement
        pre_x, pre_y = self.robot.x, self.robot.y

        # 6. Déplacer le robot
        self.robot.update(da)
        self.robot.x = self.robot.x % SIM_W
        self.robot.y = self.robot.y % SIM_H

        # 7. Contrainte : jamais hors circuit (rollback si aucun capteur actif)
        self.sensors.read(self.robot.x, self.robot.y, self.robot.angle, pixels)
        if sum(self.sensors.bits) == 0:
            self.robot.x = pre_x
            self.robot.y = pre_y
            if self.robot.trace:
                self.robot.trace.pop()

        # 9. Détection d'arrivée
        dist = math.hypot(self.robot.x - self.end_x,
                          self.robot.y - self.end_y)
        if dist < self.ARRIVE_RADIUS:
            self.arrived = True
            self.paused  = True

        # 10. Mémoriser pour affichage
        self.last_G     = G
        self.last_D     = D
        self.last_delta = delta
        self.last_da    = da

    # ─────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(C_BG)

        # ── Zone simulation ───────────────────────────────
        # Damier + ligne XOR pré-calculé (blanc/noir alternant comme le prof)
        self.screen.blit(self.circuit.display_surface, (0, 0))

        # Trajectoire
        if self.show_trace and len(self.robot.trace) > 2:
            pygame.draw.lines(self.screen, (0, 180, 140),
                              False, self.robot.trace, 2)

        # Marqueur DÉPART (vert)
        sx, sy, _ = self.circuit.get_start()
        pygame.draw.circle(self.screen, (0, 220,  60), (sx, sy), 14)
        pygame.draw.circle(self.screen, C_WHITE,       (sx, sy), 14, 2)
        lbl = self.font_sm.render("S", True, (0, 0, 0))
        self.screen.blit(lbl, (sx - lbl.get_width()//2, sy - lbl.get_height()//2))

        # Marqueur ARRIVÉE (rouge)
        ex, ey = self.end_x, self.end_y
        pygame.draw.circle(self.screen, (220,  40,  40), (ex, ey), 14)
        pygame.draw.circle(self.screen, C_WHITE,         (ex, ey), 14, 2)
        lbl = self.font_sm.render("A", True, (255, 255, 255))
        self.screen.blit(lbl, (ex - lbl.get_width()//2, ey - lbl.get_height()//2))

        # Zone d'arrivée (cercle pointillé)
        pygame.draw.circle(self.screen, (220, 40, 40),
                           (ex, ey), self.ARRIVE_RADIUS, 1)

        # Capteurs
        if self.show_sensors:
            self._draw_sensors()

        # Robot
        self._draw_robot()

        # Message ARRIVÉ
        if self.arrived:
            overlay = pygame.Surface((400, 80), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (SIM_W//2 - 200, SIM_H//2 - 40))
            msg = self.font_lg.render("ARRIVÉ !  (R pour rejouer)", True, (0, 255, 100))
            self.screen.blit(msg, (SIM_W//2 - msg.get_width()//2, SIM_H//2 - 12))

        # Séparateur
        pygame.draw.line(self.screen, C_GRAY,
                         (PANEL_X - 5, 0), (PANEL_X - 5, WIN_H), 1)

        # ── Panneau info ──────────────────────────────────
        self._draw_panel()

        pygame.display.flip()

    # ─────────────────────────────────────────────────────
    def _draw_robot(self):
        import math
        x, y  = int(self.robot.x), int(self.robot.y)
        rad   = math.radians(self.robot.angle)
        fx    = math.cos(rad)
        fy    = math.sin(rad)

        # Corps
        pygame.draw.circle(self.screen, C_PANEL,  (x, y), 10)
        pygame.draw.circle(self.screen, C_ACCENT, (x, y), 10, 2)

        # Nez (direction)
        nx = int(x + fx * 14)
        ny = int(y + fy * 14)
        pygame.draw.line(self.screen, C_ACCENT, (x, y), (nx, ny), 3)
        pygame.draw.circle(self.screen, C_ORANGE, (nx, ny), 3)

    # ─────────────────────────────────────────────────────
    def _draw_sensors(self):
        for i, (sx, sy) in enumerate(self.sensors.positions):
            if 0 <= sx < SIM_W and 0 <= sy < SIM_H:
                color = C_ACCENT if self.sensors.bits[i] == 1 else C_ORANGE
                pygame.draw.circle(self.screen, color, (sx, sy), 3)

    # ─────────────────────────────────────────────────────
    def _draw_panel(self):
        x = PANEL_X
        y = 20

        def title(txt):
            nonlocal y
            surf = self.font_md.render(txt, True, C_ACCENT)
            self.screen.blit(surf, (x, y))
            y += 22
            pygame.draw.line(self.screen, C_GRAY, (x, y), (x+270, y), 1)
            y += 8

        def line(label, val, color=C_WHITE):
            nonlocal y
            s1 = self.font_sm.render(f"{label:<14}", True, C_GRAY)
            s2 = self.font_sm.render(str(val),        True, color)
            self.screen.blit(s1, (x,      y))
            self.screen.blit(s2, (x + 130, y))
            y += 18

        def spacer():
            nonlocal y
            y += 10

        # ── Circuit ───────────────────────────────────────
        title("[ CIRCUIT ]")
        line("Nom",     self.circuit.get_name())
        line("Touches", "1 / 2 / 3")
        spacer()

        # ── Robot ─────────────────────────────────────────
        title("[ ROBOT ]")
        line("X",     f"{self.robot.x:.1f}")
        line("Y",     f"{self.robot.y:.1f}")
        line("Angle", f"{self.robot.angle % 360:.1f} °")
        line("Speed", f"{self.robot.speed} px/step")
        spacer()

        # ── Capteurs ──────────────────────────────────────
        title("[ CAPTEURS ]")
        line("G (gauche)", self.last_G,     C_ACCENT)
        line("D (droite)", self.last_D,     C_ORANGE)
        line("Delta G-D",  self.last_delta, C_WHITE)
        spacer()

        # Bits visuels
        bx = x
        for i, b in enumerate(self.sensors.bits):
            if i == 8:
                bx += 6
            color = C_ACCENT if b else (40, 40, 60)
            pygame.draw.rect(self.screen, color, (bx, y, 12, 18))
            pygame.draw.rect(self.screen, C_GRAY, (bx, y, 12, 18), 1)
            bx += 14
        y += 28

        spacer()

        # ── Logique Floue ─────────────────────────────────
        title("[ LOGIQUE FLOUE ]")
        mu = self.fuzzy.get_memberships() if hasattr(self.fuzzy, 'get_memberships') else {}

        for label, key, color in [("N (gauche)", "N", C_ORANGE),
                                   ("Z (droit)",  "Z", C_ACCENT),
                                   ("P (droite)", "P", C_VIOLET)]:
            val = mu.get(key, 0.0)
            line(f"mu_{key}", f"{val:.2f}", color)
            # Barre
            bar_w = int(val * 200)
            pygame.draw.rect(self.screen, (30, 30, 50), (x, y, 200, 8))
            pygame.draw.rect(self.screen, color,        (x, y, bar_w, 8))
            y += 14

        spacer()
        line("da (sortie)", f"{self.last_da:.1f} °", C_VIOLET)
        spacer()

        # ── Contrôles ─────────────────────────────────────
        title("[ CONTROLES ]")
        for txt in ["ESPACE  start/pause",
                    "R       reset",
                    "+/-     vitesse",
                    "S       capteurs",
                    "T       trace",
                    "ESC     quitter"]:
            s = self.font_sm.render(txt, True, C_GRAY)
            self.screen.blit(s, (x, y))
            y += 16

        # ── Status ────────────────────────────────────────
        if self.arrived:
            status, color = "  ARRIVÉ !  ", (0, 255, 100)
        elif self.paused:
            status, color = "  PAUSE  ",    C_ORANGE
        else:
            status, color = "  RUN  ",      C_ACCENT
        surf = self.font_lg.render(status, True, color)
        self.screen.blit(surf, (x, WIN_H - 40))