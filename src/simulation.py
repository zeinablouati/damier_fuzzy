# src/simulation.py
import math
import pygame
import sys

from src.robot      import Robot
from src.sensors    import SensorBar
from src.fuzzy      import FuzzyController
from src.circuit    import Circuit, cell_center, CELL_SIZE
from src.pathfinder import START, END

WIN_W, WIN_H = 1050, 660
SIM_W, SIM_H =  750, 620
PANEL_X      =  760

C_BG     = ( 10,  10,  15)
C_ACCENT = (  0, 255, 200)
C_ORANGE = (255, 107,  53)
C_VIOLET = (162,  89, 255)
C_WHITE  = (255, 255, 255)
C_GRAY   = ( 80,  80, 100)
C_PANEL  = ( 18,  18,  28)
C_GREEN  = (  0, 220,  50)
C_RED    = (220,  30,  30)
C_YELLOW = (255, 230,   0)

ARRIVAL_DIST  = 25
ARRIVAL_GUARD = 60


class Simulation:

    def __init__(self, fps=60):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Damier Fuzzy — Suivi de ligne")
        self.clock  = pygame.time.Clock()
        self.fps    = fps

        # 'idle' | 'run' | 'arrived'
        self.state  = 'idle'
        self.paused = True

        self.show_sensors = True
        self.show_trace   = True

        self.circuit = Circuit(SIM_W, SIM_H)
        self.sensors = SensorBar(n_sensors=16, spread=35, distance=30)
        self.fuzzy   = FuzzyController()

        sx, sy, sa = self.circuit.get_start()
        self.robot  = Robot(sx, sy, sa, speed=4)

        self.font_sm = pygame.font.SysFont("monospace", 12)
        self.font_md = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_lg = pygame.font.SysFont("monospace", 17, bold=True)
        self.font_xl = pygame.font.SysFont("monospace", 20, bold=True)

        self.last_delta = 0
        self.last_da    = 0.0
        self.last_G     = 0
        self.last_D     = 0
        self.steps      = 0

    # ─────────────────────────────────────────────────────
    def run(self):
        while True:
            self._handle_events()
            if self.state == 'run' and not self.paused:
                self._update()
            self._draw()
            self.clock.tick(self.fps)

    # ─────────────────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                k = event.key
                if   k == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                elif k == pygame.K_c:      self._switch('court')
                elif k == pygame.K_l:      self._switch('long')
                elif k == pygame.K_a:      self._switch('angles')
                elif k == pygame.K_SPACE:
                    if   self.state == 'idle':    self.state = 'run'; self.paused = False
                    elif self.state == 'run':     self.paused = not self.paused
                    elif self.state == 'arrived': self._reset()
                elif k == pygame.K_r: self._reset()
                elif k in (pygame.K_PLUS, pygame.K_EQUALS):
                    self.robot.speed = min(10, self.robot.speed + 1)
                elif k == pygame.K_MINUS:
                    self.robot.speed = max(1, self.robot.speed - 1)
                elif k == pygame.K_s: self.show_sensors = not self.show_sensors
                elif k == pygame.K_t: self.show_trace   = not self.show_trace

    def _switch(self, mode):
        self.circuit.set_mode(mode)
        self._reset()

    def _reset(self):
        sx, sy, sa = self.circuit.get_start()
        self.robot.reset(sx, sy, sa)
        self.steps  = 0
        self.state  = 'idle'
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
        self.steps     += 1

        if self.steps > ARRIVAL_GUARD:
            ex, ey = self.circuit.get_end()
            if math.hypot(self.robot.x - ex, self.robot.y - ey) < ARRIVAL_DIST:
                self.state = 'arrived'; self.paused = True

    # ─────────────────────────────────────────────────────
    def _draw(self):
        self.screen.fill(C_BG)

        # ── Damier + les DEUX chemins ─────────────────────
        self.screen.blit(self.circuit.combined_surface, (0, 0))

        # ── Overlays colorés pour distinguer les chemins ──
        self._draw_path_overlays()

        # ── Marqueurs S / F ───────────────────────────────
        self._draw_markers()

        if self.show_trace and len(self.robot.trace) > 2:
            pygame.draw.lines(self.screen, (0, 180, 140),
                              False, self.robot.trace, 2)

        if self.show_sensors:
            self._draw_sensors()

        self._draw_robot()

        pygame.draw.line(self.screen, C_GRAY,
                         (PANEL_X-5, 0), (PANEL_X-5, WIN_H), 1)
        self._draw_panel()

        if self.state == 'idle':    self._draw_idle_banner()
        elif self.state == 'arrived': self._draw_arrival_banner()

        pygame.display.flip()

    # ─────────────────────────────────────────────────────
    def _draw_path_overlays(self):
        """
        Surligne les cases de chaque chemin avec une couleur.
        Chemin actif    : contour + remplissage net.
        Chemin inactif  : transparent, discret.
        Vert = court / Orange-rouge = long.
        """
        CS      = CELL_SIZE
        active  = self.circuit.active_mode
        overlay = pygame.Surface((SIM_W, SIM_H), pygame.SRCALPHA)

        for mode, color_fill, color_border in [
            ('angles', ( 30, 160, 220), ( 80, 210, 255)),
            ('long',   (255,  80,  30), (255, 140,  60)),
            ('court',  ( 20, 200,  80), ( 80, 255, 120)),
        ]:
            is_active = (mode == active)
            alpha_fill   = 55  if not is_active else 90
            alpha_border = 120 if not is_active else 220

            for c, r in self.circuit.paths[mode]:
                rect = (c*CS, r*CS, CS, CS)
                overlay.fill((*color_fill, alpha_fill), rect)
                # Contour uniquement pour le chemin actif
                if is_active:
                    pygame.draw.rect(overlay,
                                     (*color_border, alpha_border),
                                     rect, 3)

        self.screen.blit(overlay, (0, 0))

    # ─────────────────────────────────────────────────────
    def _draw_markers(self):
        sc, sr = START
        ec, er = END
        sx, sy = cell_center(sc, sr)
        ex, ey = cell_center(ec, er)

        for (px, py), label, col in [
            ((sx, sy), "S", C_GREEN),
            ((ex, ey), "F", C_RED),
        ]:
            pygame.draw.circle(self.screen, col,    (px, py), 16)
            pygame.draw.circle(self.screen, C_PANEL,(px, py), 16, 2)
            lbl = self.font_md.render(label, True, C_PANEL)
            self.screen.blit(lbl, (px - lbl.get_width()//2,
                                   py - lbl.get_height()//2))

    # ─────────────────────────────────────────────────────
    def _draw_robot(self):
        x, y = int(self.robot.x), int(self.robot.y)
        rad  = math.radians(self.robot.angle)
        fx, fy = math.cos(rad), math.sin(rad)

        pygame.draw.circle(self.screen, C_PANEL,  (x, y), 10)
        pygame.draw.circle(self.screen, C_ACCENT, (x, y), 10, 2)
        nx, ny = int(x + fx*14), int(y + fy*14)
        pygame.draw.line(self.screen, C_ACCENT, (x, y), (nx, ny), 3)
        pygame.draw.circle(self.screen, C_ORANGE, (nx, ny), 3)

    def _draw_sensors(self):
        for i, (sx, sy) in enumerate(self.sensors.positions):
            if 0 <= sx < SIM_W and 0 <= sy < SIM_H:
                col = C_ACCENT if self.sensors.bits[i] else C_ORANGE
                pygame.draw.circle(self.screen, col, (sx, sy), 3)

    # ─────────────────────────────────────────────────────
    def _draw_idle_banner(self):
        bw, bh = 600, 52
        ox = (SIM_W - bw) // 2
        oy = SIM_H - bh - 8

        ov = pygame.Surface((bw, bh), pygame.SRCALPHA)
        ov.fill((10, 10, 20, 220))
        self.screen.blit(ov, (ox, oy))

        active = self.circuit.active_mode
        nc = self.circuit.get_path_len('court')
        nl = self.circuit.get_path_len('long')
        na = self.circuit.get_path_len('angles')

        t = self.font_md.render("CHOISIR LE CHEMIN :", True, C_YELLOW)
        self.screen.blit(t, (ox + 10, oy + 6))

        c_col = C_GREEN       if active == 'court'  else C_GRAY
        l_col = (255,140, 60) if active == 'long'   else C_GRAY
        a_col = ( 80,210,255) if active == 'angles' else C_GRAY
        s_col = C_ACCENT

        for txt, col, dx in [
            (f"[C] Court {nc}c",  c_col,  10),
            (f"[L] Long {nl}c",   l_col, 180),
            (f"[A] Angl {na}c",   a_col, 350),
            ("ESPACE = go",       s_col, 480),
        ]:
            s = self.font_md.render(txt, True, col)
            self.screen.blit(s, (ox + dx, oy + 28))

    def _draw_arrival_banner(self):
        bw, bh = 560, 58
        ox = (SIM_W - bw) // 2
        oy = (SIM_H - bh) // 2

        ov = pygame.Surface((bw, bh), pygame.SRCALPHA)
        ov.fill((10, 10, 20, 220))
        self.screen.blit(ov, (ox, oy))

        mode  = self.circuit.active_mode.upper()
        col   = C_GREEN if self.circuit.active_mode == 'court' else (80,210,255) if self.circuit.active_mode == 'angles' else (255,140,60)
        msg1  = self.font_xl.render(
            f"ARRIVÉE !  chemin {mode} — {self.steps} pas", True, col)
        msg2  = self.font_md.render(
            "ESPACE = rejouer   |   C / L = changer", True, C_ACCENT)
        self.screen.blit(msg1, (ox + 10, oy +  6))
        self.screen.blit(msg2, (ox + 10, oy + 34))

    # ─────────────────────────────────────────────────────
    def _draw_panel(self):
        x = PANEL_X
        y = 20

        def title(txt):
            nonlocal y
            self.screen.blit(self.font_md.render(txt, True, C_ACCENT), (x, y)); y += 22
            pygame.draw.line(self.screen, C_GRAY, (x, y), (x+270, y), 1); y += 8

        def line(label, val, color=C_WHITE):
            nonlocal y
            self.screen.blit(self.font_sm.render(f"{label:<14}", True, C_GRAY), (x, y))
            self.screen.blit(self.font_sm.render(str(val), True, color), (x+130, y))
            y += 18

        def spacer():
            nonlocal y; y += 8

        title("[ CHEMIN ]")
        active = self.circuit.active_mode
        line("[C] Court",  f"{self.circuit.get_path_len('court')} cases",
             C_GREEN if active=='court' else C_GRAY)
        line("[L] Long",   f"{self.circuit.get_path_len('long')} cases",
             (255,140,60) if active=='long' else C_GRAY)
        line("[A] Angles", f"{self.circuit.get_path_len('angles')} cases",
             (80,210,255) if active=='angles' else C_GRAY)
        line("Actif", active.upper(),
             C_GREEN if active=='court' else (80,210,255) if active=='angles' else (255,140,60))
        spacer()

        title("[ ROBOT ]")
        line("X",     f"{self.robot.x:.1f}")
        line("Y",     f"{self.robot.y:.1f}")
        line("Angle", f"{self.robot.angle%360:.1f} °")
        line("Speed nom.", f"{self.robot.speed} px/pas")
        v_eff = getattr(self.robot, 'effective_speed', self.robot.speed)
        v_col = C_ACCENT if v_eff >= self.robot.speed * 0.8 else C_ORANGE
        line("Speed eff.", f"{v_eff:.1f} px/pas", v_col)
        line("Pas",   str(self.steps))
        spacer()

        title("[ CAPTEURS ]")
        line("G (gauche)", self.last_G,     C_ACCENT)
        line("D (droite)", self.last_D,     C_ORANGE)
        line("Delta D−G",  self.last_delta, C_WHITE)
        spacer()

        bx = x
        for i, b in enumerate(self.sensors.bits):
            if i == 8: bx += 6
            col = C_ACCENT if b else (40,40,60)
            pygame.draw.rect(self.screen, col,    (bx, y, 12, 18))
            pygame.draw.rect(self.screen, C_GRAY, (bx, y, 12, 18), 1)
            bx += 14
        y += 28; spacer()

        title("[ LOGIQUE FLOUE ]")
        mu = self.fuzzy.get_memberships()
        for label, key, col in [("N (gauche)","N",C_ORANGE),
                                  ("Z (centre)","Z",C_ACCENT),
                                  ("P (droite)","P",C_VIOLET)]:
            v = mu.get(key, 0.0)
            line(f"µ_{key}", f"{v:.2f}", col)
            pygame.draw.rect(self.screen,(30,30,50),(x,y,200,8))
            pygame.draw.rect(self.screen, col,      (x,y,int(v*200),8))
            y += 14
        spacer()
        line("da (sortie)", f"{self.last_da:.1f} °", C_VIOLET)
        spacer()

        title("[ CONTROLES ]")
        for txt in ["C       chemin court","L       chemin long",
                    "A       angles mix", "ESPACE  start/pause", "R       reset",
                    "+/-     vitesse",     "S       capteurs",
                    "T       trace",       "ESC     quitter"]:
            self.screen.blit(self.font_sm.render(txt, True, C_GRAY), (x, y)); y += 16

        if   self.state == 'arrived': status, col = "  ARRIVÉE !  ", C_GREEN
        elif self.paused:             status, col = "   PAUSE     ", C_ORANGE
        else:                         status, col = "   RUN       ", C_ACCENT
        self.screen.blit(self.font_lg.render(status, True, col), (x, WIN_H-40))