# src/simulation.py
import pygame
import sys
import logging
import os
from datetime import datetime
from src.robot   import Robot
from src.sensors import SensorBar
from src.fuzzy   import FuzzyController
from src.circuit import Circuit

# ── Logger fichier ────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
_log_file = f"logs/robot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    filename=_log_file,
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    encoding="utf-8",
)
robot_log = logging.getLogger("robot")

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
        robot_log.info("="*60)
        robot_log.info("INIT | circuit=%s | start=(%.0f,%.0f) | angle=%.0f°",
                       self.circuit.get_name(), sx, sy, sa)

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
        self.last_D = 0
        # ── Rotation 90° animée ───────────────────────────
        # None  = mode normal
        # dict  = {"dir": +1/-1, "remaining": degrés restants}
        self.turning   = None
        self.turn_step = 4      # degrés tournés par frame

        # ── Debug visuel (touche D) ───────────────────────
        self.debug_mode    = False
        self.debug_log     = []          # derniers événements (max 8)
        self.rollback_marks = []         # positions où rollback s'est déclenché
        self.debug_state   = "NORMAL"   # état courant affiché

        # ── Historique couleurs cases traversées ──────────
        self.cell_colors   = []          # liste de (r,g,b), max 16 cases
        self._last_cell    = (-1, -1)    # dernière case enregistrée (col, row)

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
                elif event.key == pygame.K_d:
                    self.debug_mode = not self.debug_mode
                    self.debug_log.clear()
                    self.rollback_marks.clear()

    # ─────────────────────────────────────────────────────
    def _reset(self):
        sx, sy, sa = self.circuit.get_start()
        self.robot.reset(sx, sy, sa)
        self.end_x, self.end_y = self.circuit.get_end()
        self.arrived = False
        self.paused  = True
        self.turning = None
        self.debug_log.clear()
        self.rollback_marks.clear()
        self.debug_state = "NORMAL"
        self.cell_colors  = []
        self._last_cell   = (-1, -1)
        robot_log.info("-"*60)
        robot_log.info("RESET | circuit=%s | start=(%.0f,%.0f) | angle=%.0f°",
                       self.circuit.get_name(), sx, sy, sa)

    # ─────────────────────────────────────────────────────
    def _update(self):
        import math
        pixels = self.circuit.get_pixel_array()

        # ── A. Rotation sur place en cours ───────────────────
        if self.turning is not None:
            self.debug_state = f"TURN {'G' if self.turning['dir']==-1 else 'D'} {self.turning['remaining']}°"
            step = min(self.turn_step, self.turning["remaining"])
            self.robot.angle += self.turning["dir"] * step
            self.turning["remaining"] -= step

            self.sensors.read(self.robot.x, self.robot.y,
                              self.robot.angle, pixels)

            bits_on = sum(self.sensors.bits)
            robot_log.debug(
                "TURN | dir=%+d | step=%.1f° | angle=%.1f° | remaining=%.1f° | bits=%d | bits_mask=%s",
                self.turning["dir"] if self.turning else 0,
                step, self.robot.angle,
                self.turning["remaining"] if self.turning else 0,
                bits_on,
                "".join(str(b) for b in self.sensors.bits)
            )

            if bits_on > 0:
                robot_log.info("TURN_OK | angle=%.1f° | bits=%d → ligne retrouvée, rotation arrêtée", self.robot.angle, bits_on)
                self._dblog(f"TURN OK  angle={self.robot.angle:.0f}°  bits={bits_on}")
                self.turning = None
            elif self.turning is not None and self.turning["remaining"] <= 0:
                robot_log.warning("TURN_FIN | angle=%.1f° | ligne toujours perdue après rotation complète", self.robot.angle)
                self._dblog(f"TURN FIN angle={self.robot.angle:.0f}°  LIGNE PERDUE")
                self.turning = None

            self.last_G, self.last_D = self.sensors.compute_GD()
            self.last_delta = self.sensors.get_delta()
            self.last_da    = 0.0
            return  # pas d'avancement pendant la rotation

        # ── B. Lire les capteurs ──────────────────────────────
        self.debug_state = "NORMAL"
        self.sensors.read(self.robot.x, self.robot.y,
                          self.robot.angle, pixels)

        # ── C. Ligne perdue → chercher la meilleure direction ─
        if sum(self.sensors.bits) == 0:
            self.debug_state = "LOST"
            robot_log.warning(
                "LOST | pos=(%.0f, %.0f) | angle=%.1f° | aucun capteur actif",
                self.robot.x, self.robot.y, self.robot.angle
            )
            self._dblog(f"LOST  pos=({self.robot.x:.0f},{self.robot.y:.0f})  a={self.robot.angle:.0f}°")
            best_dir   = None
            best_bits  = 0
            best_angle = 0

            for angle_test in range(5, 180, 5):
                # Tester à gauche
                self.sensors.read(self.robot.x, self.robot.y,
                                  self.robot.angle - angle_test, pixels)
                if sum(self.sensors.bits) > best_bits:
                    best_bits  = sum(self.sensors.bits)
                    best_dir   = -1
                    best_angle = angle_test

                # Tester à droite
                self.sensors.read(self.robot.x, self.robot.y,
                                  self.robot.angle + angle_test, pixels)
                if sum(self.sensors.bits) > best_bits:
                    best_bits  = sum(self.sensors.bits)
                    best_dir   = +1
                    best_angle = angle_test

            if best_dir is not None:
                self.turning = {"dir": best_dir, "remaining": best_angle}
                robot_log.info(
                    "SCAN | meilleure direction : %s | cible=%.0f° | bits=%d",
                    "GAUCHE" if best_dir == -1 else "DROITE", best_angle, best_bits
                )
                self._dblog(f"SCAN  dir={'G' if best_dir==-1 else 'D'}  cible={best_angle}°  bits={best_bits}")
            else:
                robot_log.error("SCAN | aucune direction trouvée dans 360° !")
                self._dblog("SCAN  aucune direction trouvée !")

            # Relire angle courant, ne pas avancer cette frame
            self.sensors.read(self.robot.x, self.robot.y,
                              self.robot.angle, pixels)
            self.last_G, self.last_D = self.sensors.compute_GD()
            self.last_delta = self.sensors.get_delta()
            self.last_da    = 0.0
            return

        # ── D. Mode normal : suivi de ligne fuzzy ────────────
        G, D  = self.sensors.compute_GD()
        delta = self.sensors.get_delta()

        # ── Détection de virage (coin) ────────────────────────
        # Si la ligne est COMPLETEMENT d'un seul côté (G≈0 ou D≈0),
        # c'est un coin → tourner 90° sur place (pas de fuzzy = pas d'arc)
        COIN_SEUIL = 8   # D ou G doit être > 8 pour déclencher un virage
        if G <= 1 and D > COIN_SEUIL and self.turning is None:
            robot_log.info("COIN_DROIT | G=%d D=%d delta=%d → virage 90° droite", G, D, delta)
            self._dblog(f"COIN D  G={G} D={D} → TURN 90°")
            self.turning = {"dir": +1, "remaining": 90}
            return
        elif D <= 1 and G > COIN_SEUIL and self.turning is None:
            robot_log.info("COIN_GAUCHE | G=%d D=%d delta=%d → virage 90° gauche", G, D, delta)
            self._dblog(f"COIN G  G={G} D={D} → TURN 90°")
            self.turning = {"dir": -1, "remaining": 90}
            return

        da = self.fuzzy.compute(delta)

        mu = self.fuzzy.get_memberships() if hasattr(self.fuzzy, "get_memberships") else {}
        robot_log.debug(
            "FUZZY | pos=(%.0f,%.0f) | angle=%.1f° | G=%d D=%d delta=%d"
            " | mu_N=%.2f mu_Z=%.2f mu_P=%.2f | da=%.2f°",
            self.robot.x, self.robot.y, self.robot.angle,
            G, D, delta,
            mu.get("N", 0), mu.get("Z", 0), mu.get("P", 0),
            da
        )

        pre_x, pre_y = self.robot.x, self.robot.y

        self.robot.update(da)
        # Clamp (pas de modulo) : le robot ne peut pas sortir de la zone
        self.robot.x = max(0, min(SIM_W - 1, self.robot.x))
        self.robot.y = max(0, min(SIM_H - 1, self.robot.y))

        # Rollback si ligne perdue après déplacement
        self.sensors.read(self.robot.x, self.robot.y,
                          self.robot.angle, pixels)
        if sum(self.sensors.bits) == 0:
            robot_log.warning(
                "ROLLBACK | da=%.1f° | pos avant=(%.0f,%.0f) | pos après=(%.0f,%.0f) | déplacement annulé",
                da, pre_x, pre_y, self.robot.x, self.robot.y
            )
            self._dblog(f"ROLLBACK da={da:.1f}°  ({pre_x:.0f},{pre_y:.0f})")
            if self.debug_mode:
                self.rollback_marks.append((int(pre_x), int(pre_y)))
                if len(self.rollback_marks) > 40:
                    self.rollback_marks.pop(0)
            self.robot.x = pre_x
            self.robot.y = pre_y
            if self.robot.trace:
                self.robot.trace.pop()

        # Détection arrivée
        dist = math.hypot(self.robot.x - self.end_x,
                          self.robot.y - self.end_y)
        if dist < self.ARRIVE_RADIUS:
            robot_log.info(
                "ARRIVEE | pos=(%.0f,%.0f) | dist=%.1f px | objectif atteint !",
                self.robot.x, self.robot.y, dist
            )
            self.arrived = True
            self.paused  = True

        self.last_G     = G
        self.last_D     = D
        self.last_delta = delta
        self.last_da    = da

        # ── Enregistrer la couleur de la case courante ────────
        col = int(self.robot.x) // 60
        row = int(self.robot.y) // 60
        if (col, row) != self._last_cell:
            self._last_cell = (col, row)
            is_black = (row + col) % 2 == 0
            color = (0, 0, 0) if is_black else (255, 255, 255)
            self.cell_colors.append(color)
            if len(self.cell_colors) > 16:
                self.cell_colors.pop(0)
            nom_couleur = "NOIR" if is_black else "BLANC"
            sequence = " → ".join("N" if c == (0,0,0) else "B" for c in self.cell_colors)
            robot_log.info(
                "CASE | col=%d row=%d | couleur=%-5s | séquence=[%s]",
                col, row, nom_couleur, sequence
            )
            print(f"CASE | col={col} row={row} | {nom_couleur:5s} | [{sequence}]")

    # ─────────────────────────────────────────────────────
    def _dblog(self, msg):
        """Ajoute un message au journal debug (max 8 lignes)."""
        if not self.debug_mode:
            return
        self.debug_log.append(msg)
        if len(self.debug_log) > 8:
            self.debug_log.pop(0)

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

        # Mode debug visuel
        if self.debug_mode:
            self._draw_debug()

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
    def _draw_debug(self):
        import math

        rx, ry = int(self.robot.x), int(self.robot.y)

        # 1. Couleur du robot selon l'état
        state_colors = {
            "NORMAL":  (  0, 255, 200),   # cyan
            "LOST":    (255,  50,  50),   # rouge
        }
        if self.debug_state.startswith("TURN"):
            body_color = (255, 220,   0)  # jaune pendant rotation
        else:
            body_color = state_colors.get(self.debug_state, C_WHITE)
        pygame.draw.circle(self.screen, body_color, (rx, ry), 13, 3)

        # 2. Arc de scan (180° de chaque côté) quand ligne perdue
        if self.debug_state == "LOST":
            base = self.robot.angle
            for a_off in range(0, 180, 10):
                for sign in (-1, +1):
                    a_rad = math.radians(base + sign * a_off)
                    ex = int(rx + math.cos(a_rad) * 35)
                    ey = int(ry + math.sin(a_rad) * 35)
                    pygame.draw.line(self.screen, (255, 100, 0, 80),
                                     (rx, ry), (ex, ey), 1)

        # 3. Flèche de direction cible pendant rotation
        if self.turning is not None:
            target_angle = self.robot.angle + self.turning["dir"] * self.turning["remaining"]
            a_rad = math.radians(target_angle)
            tx = int(rx + math.cos(a_rad) * 40)
            ty = int(ry + math.sin(a_rad) * 40)
            pygame.draw.line(self.screen, (255, 220, 0), (rx, ry), (tx, ty), 2)
            pygame.draw.circle(self.screen, (255, 220, 0), (tx, ty), 4)

        # 4. Croix rouges aux positions de rollback
        for (mx, my) in self.rollback_marks:
            pygame.draw.line(self.screen, (255, 0, 0),
                             (mx-5, my-5), (mx+5, my+5), 2)
            pygame.draw.line(self.screen, (255, 0, 0),
                             (mx+5, my-5), (mx-5, my+5), 2)

        # 5. Journal d'événements (coin bas-gauche)
        bg = pygame.Surface((380, 10 + len(self.debug_log) * 14), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.screen.blit(bg, (4, WIN_H - 14 * len(self.debug_log) - 14))
        for i, msg in enumerate(self.debug_log):
            color = (255, 80, 80) if "LOST" in msg or "ROLLBACK" in msg \
                    else (255, 220, 0) if "TURN" in msg \
                    else (180, 255, 180)
            s = self.font_sm.render(msg, True, color)
            self.screen.blit(s, (6, WIN_H - (len(self.debug_log) - i) * 14 - 6))

        # 6. Badge état courant (coin haut-gauche)
        badge_colors = {"NORMAL": (0,180,100), "LOST": (220,40,40)}
        bc = badge_colors.get(self.debug_state,
                              (200, 180, 0) if "TURN" in self.debug_state else (80,80,80))
        badge = self.font_md.render(f" DEBUG: {self.debug_state} ", True, (0, 0, 0))
        bw, bh = badge.get_size()
        pygame.draw.rect(self.screen, bc, (4, 4, bw + 4, bh + 4))
        self.screen.blit(badge, (6, 5))

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

        # ── Historique couleurs cases traversées ──────────
        title("[ CASES ]")
        if not self.cell_colors:
            s = self.font_sm.render("(aucune case parcourue)", True, C_GRAY)
            self.screen.blit(s, (x, y))
            y += 16
        else:
            sq  = 14   # taille d'un carré
            gap = 3
            cx  = x
            for color in self.cell_colors:
                pygame.draw.rect(self.screen, color,   (cx, y, sq, sq))
                pygame.draw.rect(self.screen, C_GRAY,  (cx, y, sq, sq), 1)
                cx += sq + gap
            y += sq + 6
        spacer()

        # ── Contrôles ─────────────────────────────────────
        title("[ CONTROLES ]")
        for txt in ["ESPACE  start/pause",
                    "R       reset",
                    "+/-     vitesse",
                    "S       capteurs",
                    "T       trace",
                    "D       debug",
                    "ESC     quitter"]:
            s = self.font_sm.render(txt, True, C_GRAY)
            self.screen.blit(s, (x, y))
            y += 16

        # ── Status ────────────────────────────────────────
        if self.arrived:
            status, color = "  ARRIVÉ !  ", (0, 255, 100)
        elif self.turning is not None:
            direction = "← GAUCHE" if self.turning["dir"] == -1 else "DROITE →"
            remaining = self.turning["remaining"]
            status = f"  TURN {direction} ({remaining}°)  "
            color  = C_VIOLET
        elif self.paused:
            status, color = "  PAUSE  ",    C_ORANGE
        else:
            status, color = "  RUN  ",      C_ACCENT
        surf = self.font_lg.render(status, True, color)
        self.screen.blit(surf, (x, WIN_H - 40))