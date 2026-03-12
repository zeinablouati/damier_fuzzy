# src/circuit.py
import pygame

# Couleurs damier
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)

LINE_COLOR = (255, 255, 255)
LINE_WIDTH = 40   # ← chemin large pour que le robot ait de la marge
CELL_SIZE  = 60


class Circuit:

    CIRCUITS = {
        1: ("Rectangle simple",  375, 80,  0),   # milieu segment haut, cap droite
        2: ("Serpentin 90°",     375, 100, 0),   # milieu segment haut, cap droite
    }

    def __init__(self, width=750, height=620):
        self.width  = width
        self.height = height

        self.board_surface = pygame.Surface((width, height))
        self.line_surface  = pygame.Surface((width, height))

        self.current_id = 1
        self.load(1)

    # ── Damier ───────────────────────────────────────────

    def _draw_board(self):
        cs = CELL_SIZE
        for row in range(self.height // cs + 1):
            for col in range(self.width  // cs + 1):
                color = BLACK if (row + col) % 2 == 0 else WHITE
                pygame.draw.rect(self.board_surface, color,
                                 (col*cs, row*cs, cs, cs))

    # ── Chargement ───────────────────────────────────────

    def load(self, circuit_id):
        self.current_id = circuit_id
        self._draw_board()
        self.line_surface.fill(BLACK)

        if circuit_id == 1:
            self._draw_circuit1()
        elif circuit_id == 2:
            self._draw_circuit2()

    # ── Méthode générique : chemin de segments droits ────

    def _draw_path(self, waypoints, closed=True):
        """
        Trace un chemin rectiligne (segments H/V uniquement).
        Les coins sont remplis par des disques pour éviter tout
        trou à 90°. Le robot voit ainsi un chemin continu.
        """
        pts = list(waypoints)
        if closed:
            pts = pts + [pts[0]]          # ferme la boucle

        # Segments
        for i in range(len(pts) - 1):
            pygame.draw.line(self.line_surface, LINE_COLOR,
                             pts[i], pts[i + 1], LINE_WIDTH)

        # Coins (disques = raccords parfaits à 90°)
        for p in waypoints:
            pygame.draw.circle(self.line_surface, LINE_COLOR,
                               (int(p[0]), int(p[1])), LINE_WIDTH // 2)

    # ── Circuit 1 : boucle rectangulaire ─────────────────

    def _draw_circuit1(self):
        """
        Rectangle simple avec uniquement des droites et
        4 virages à 90°. Le robot doit faire le tour.
        """
        waypoints = [
            (100, 80),
            (650, 80),
            (650, 540),
            (100, 540),
        ]
        self._draw_path(waypoints, closed=True)

    # ── Circuit 2 : serpentin à 90° ──────────────────────

    def _draw_circuit2(self):
        """
        Serpentin fermé : 4 lignes horizontales reliées par
        des connecteurs verticaux aux extrémités gauche/droite.
        Tous les virages sont à exactement 90°.

        Tracé :
          → y=100  (gauche→droite)
          ↓ droite
          ← y=260  (droite→gauche)
          ↓ gauche
          → y=420  (gauche→droite)
          ↓ droite
          ← y=540  (droite→gauche)
          ↑ gauche (retour au départ)
        """
        waypoints = [
            ( 60, 100),   # 0 – départ
            (690, 100),   # 1
            (690, 260),   # 2
            ( 60, 260),   # 3
            ( 60, 420),   # 4
            (690, 420),   # 5
            (690, 540),   # 6
            ( 60, 540),   # 7  → fermeture : (60,540)→(60,100)
        ]
        self._draw_path(waypoints, closed=True)

    # ── Utilitaires ──────────────────────────────────────

    def get_start(self):
        _, x, y, a = self.CIRCUITS[self.current_id]
        return x, y, a

    def get_pixel_array(self):
        return pygame.surfarray.array3d(self.line_surface)

    def get_name(self):
        name, _, _, _ = self.CIRCUITS[self.current_id]
        return name