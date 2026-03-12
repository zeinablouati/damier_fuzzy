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
        self.paused = True
        self.show_sensors = True
        self.show_trace   = True

        # ── Composants ────────────────────────────────────
        self.circuit = Circuit(SIM_W, SIM_H)

        # spread=60  → barre de 120 px (> chemin 40 px) : les capteurs
        #              débordent toujours des deux côtés du chemin
        # distance=30 → voit les coins 30 px à l'avance (10 pas à v=3)
        self.sensors = SensorBar(n_sensors=16, spread=60, distance=30)

        self.fuzzy = FuzzyController()

        sx, sy, sa = self.circuit.get_start()
        self.robot = Robot(sx, sy, sa, speed=3)

        # ── Polices ───────────────────────────────────────
        self.font_sm = pygame.font.SysFont("monospace", 12)
        self.font_md = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_lg = pygame.font.SysFont("monospace", 17, bold=True)

        # ── État affiché ──────────────────────────────────
        self.last_delta = 0
        self.last_da    = 0.0
        self.last_G     = 0
        self.last_D     = 0

    # ─────────────────────────────────────────────────────
    def run(self):
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

                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
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
        self.paused = True

    # ─────────────────────────────────────────────────────
    def _update(self):
        pixels = self.circuit.get_pixel_array()
        self.sensors.read(self.robot.x, self.robot.y,
                          self.robot.angle, pixels)

        G, D  = self.sensors.compute_GD()
        delta = self.sensors.get_delta()
        da    = self.fuzzy.compute(delta)

        self.robot.update(da)
        self.robot.x = self.robot.x % SIM_W
        self.robot.y = self.robot.y % SIM_H

        self.last_G     = G
        self.last_D     = D
        self.last_delta = delta
        self.last_da    = da

    # ─────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(C_BG)

        self.screen.blit(self.circuit.board_surface, (0, 0))
        self.screen.blit(self.circuit.line_surface,  (0, 0),
                         special_flags=pygame.BLEND_ADD)

        if self.show_trace and len(self.robot.trace) > 2:
            pygame.draw.lines(self.screen, (0, 180, 140),
                              False, self.robot.trace, 2)

        if self.show_sensors:
            self._draw_sensors()

        self._draw_robot()

        pygame.draw.line(self.screen, C_GRAY,
                         (PANEL_X - 5, 0), (PANEL_X - 5, WIN_H), 1)

        self._draw_panel()
        pygame.display.flip()

    # ─────────────────────────────────────────────────────
    def _draw_robot(self):
        import math
        x, y = int(self.robot.x), int(self.robot.y)
        rad  = math.radians(self.robot.angle)
        fx   = math.cos(rad)
        fy   = math.sin(rad)

        pygame.draw.circle(self.screen, C_PANEL,  (x, y), 10)
        pygame.draw.circle(self.screen, C_ACCENT, (x, y), 10, 2)

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
            self.screen.blit(s1, (x,       y))
            self.screen.blit(s2, (x + 130, y))
            y += 18

        def spacer():
            nonlocal y
            y += 10

        title("[ CIRCUIT ]")
        line("Nom",     self.circuit.get_name())
        line("Touches", "1 / 2")
        spacer()

        title("[ ROBOT ]")
        line("X",     f"{self.robot.x:.1f}")
        line("Y",     f"{self.robot.y:.1f}")
        line("Angle", f"{self.robot.angle % 360:.1f} °")
        line("Speed", f"{self.robot.speed} px/step")
        spacer()

        title("[ CAPTEURS ]")
        line("G (gauche)", self.last_G,     C_ACCENT)
        line("D (droite)", self.last_D,     C_ORANGE)
        line("Delta G-D",  self.last_delta, C_WHITE)
        spacer()

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

        title("[ LOGIQUE FLOUE ]")
        mu = self.fuzzy.get_memberships()

        for label, key, color in [("N (gauche)", "N", C_ORANGE),
                                   ("Z (droit)",  "Z", C_ACCENT),
                                   ("P (droite)", "P", C_VIOLET)]:
            val = mu.get(key, 0.0)
            line(f"mu_{key}", f"{val:.2f}", color)
            bar_w = int(val * 200)
            pygame.draw.rect(self.screen, (30, 30, 50), (x, y, 200, 8))
            pygame.draw.rect(self.screen, color,        (x, y, bar_w, 8))
            y += 14

        spacer()
        line("da (sortie)", f"{self.last_da:.1f} °", C_VIOLET)
        spacer()

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

        status = "  PAUSE  " if self.paused else "  RUN  "
        color  = C_ORANGE   if self.paused else C_ACCENT
        surf   = self.font_lg.render(status, True, color)
        self.screen.blit(surf, (x, WIN_H - 40))