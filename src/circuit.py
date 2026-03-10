# src/circuit.py
import math
import numpy as np
import pygame

# Couleurs damier — noir et blanc purs comme le prof
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)

LINE_COLOR = (255, 255, 255)   # blanc — XOR avec damier crée blanc/noir alternant
LINE_WIDTH = 18

CELL_SIZE = 60   # cases plus grandes comme le prof


class Circuit:

    # (nom, start_x, start_y, start_angle, end_x, end_y)
    CIRCUITS = {
        1: ("Rectangle 10x6",          375, 130,   0,  375, 490),  # bord haut → bord bas
        2: ("Double boucle (vertical)", 255, 130,   0,  495, 490),  # fig-8 : séparateur vertical
        3: ("Double boucle (horiz.)",   375, 130,   0,  375, 490),  # 2 boucles haut/bas
    }

    def __init__(self, width=750, height=620):
        self.width  = width
        self.height = height

        self.board_surface   = pygame.Surface((width, height))
        self.line_surface    = pygame.Surface((width, height))
        self.display_surface = pygame.Surface((width, height))  # XOR pré-calculé

        self.current_id = 1
        self.load(1)

    # ── Damier ───────────────────────────────────────────

    def _draw_board(self):
        """Damier noir/blanc pur comme le prof."""
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
        self.line_surface.fill((0, 0, 0))  # fond noir

        if circuit_id == 1:
            self._draw_circuit1()
        elif circuit_id == 2:
            self._draw_circuit2()
        elif circuit_id == 3:
            self._draw_circuit3()

        # XOR(damier, ligne) → blanc sur noir = blanc, blanc sur blanc = noir
        board_arr = pygame.surfarray.array3d(self.board_surface)
        line_arr  = pygame.surfarray.array3d(self.line_surface)
        xor_arr   = np.bitwise_xor(board_arr, line_arr)
        pygame.surfarray.blit_array(self.display_surface, xor_arr)

    # ── Circuit 1 : Grand rectangle 10×6 ────────────────────

    def _draw_circuit1(self):
        """Rectangle 10 carreaux × 6 carreaux = 600×360 px, centré."""
        cs = CELL_SIZE
        x0 = (self.width  - 10 * cs) // 2   # 75
        y0 = (self.height -  6 * cs) // 2   # 130
        x1 = x0 + 10 * cs                    # 675
        y1 = y0 +  6 * cs                    # 490
        pygame.draw.lines(self.line_surface, LINE_COLOR, True,
                          [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                          LINE_WIDTH)

    # ── Circuit 2 : Double boucle (séparateur vertical) ──────

    def _draw_circuit2(self):
        """
        Rectangle 8×6 + divison verticale centrale → figure-8 avec 2 croisements.
        Le robot doit choisir la bonne boucle (gauche ou droite) aux croisements.
        """
        cs = CELL_SIZE
        x0   = (self.width  - 8 * cs) // 2   # 135
        y0   = (self.height - 6 * cs) // 2   # 130
        x1   = x0 + 8 * cs                    # 615
        y1   = y0 + 6 * cs                    # 490
        x_mid = (x0 + x1) // 2               # 375

        # Périmètre extérieur
        pygame.draw.lines(self.line_surface, LINE_COLOR, True,
                          [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                          LINE_WIDTH)
        # Séparateur vertical central → 2 croisements haut et bas
        pygame.draw.line(self.line_surface, LINE_COLOR,
                         (x_mid, y0), (x_mid, y1), LINE_WIDTH)

    # ── Circuit 3 : Double boucle (séparateur horizontal) ────

    def _draw_circuit3(self):
        """
        Rectangle 8×6 + division horizontale centrale → 2 boucles haut/bas.
        Le robot navigue en haut puis en bas (ou inversement).
        """
        cs = CELL_SIZE
        x0   = (self.width  - 8 * cs) // 2   # 135
        y0   = (self.height - 6 * cs) // 2   # 130
        x1   = x0 + 8 * cs                    # 615
        y1   = y0 + 6 * cs                    # 490
        y_mid = (y0 + y1) // 2               # 310

        # Périmètre extérieur
        pygame.draw.lines(self.line_surface, LINE_COLOR, True,
                          [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                          LINE_WIDTH)
        # Séparateur horizontal central → 2 croisements gauche et droite
        pygame.draw.line(self.line_surface, LINE_COLOR,
                         (x0, y_mid), (x1, y_mid), LINE_WIDTH)

    # ── Utilitaires ──────────────────────────────────────

    def get_start(self):
        _, sx, sy, sa, _, _ = self.CIRCUITS[self.current_id]
        return sx, sy, sa

    def get_end(self):
        _, _, _, _, ex, ey = self.CIRCUITS[self.current_id]
        return ex, ey

    def get_pixel_array(self):
        return pygame.surfarray.array3d(self.line_surface)

    def get_name(self):
        name, _, _, _, _, _ = self.CIRCUITS[self.current_id]
        return name