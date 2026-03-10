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
        1: ("Parcours 7 segments",      25,  10,   0,  725, 610),  # haut-gauche → bas-droite
        2: ("Spirale inversee",          25,  10,   0,  425, 310),  # spirale de l'extérieur vers le centre
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

    # ── Circuit 1 : Parcours en 7 segments ──────────────────

    def _draw_circuit1(self):
        """
        Chemin ouvert de S (haut-gauche) à A (bas-droite) :
          →4  ↓5  →4  ↓3  ←2  ↓4  →8
        pas = 50 px/carreau  (14×12 carreaux = 700×600 px)
        """
        s  = 50          # 1 carreau = 50 px
        x0 = 25          # marge gauche
        y0 = 10          # marge haute

        pts = [
            (x0,          y0),           # S  départ haut-gauche
            (x0 + 4*s,    y0),           # → 4
            (x0 + 4*s,    y0 + 5*s),     # ↓ 5
            (x0 + 8*s,    y0 + 5*s),     # → 4
            (x0 + 8*s,    y0 + 8*s),     # ↓ 3
            (x0 + 6*s,    y0 + 8*s),     # ← 2
            (x0 + 6*s,    y0 + 12*s),    # ↓ 4
            (x0 + 14*s,   y0 + 12*s),    # → 8  A arrivée bas-droite
        ]
        pygame.draw.lines(self.line_surface, LINE_COLOR, False, pts, LINE_WIDTH)

    # ── Circuit 2 : Double boucle (séparateur vertical) ──────

    def _draw_circuit2(self):
        """
        Spirale inversée (9 segments, 10 points) :
        départ haut-gauche → grande boucle extérieure → spirale vers le centre.
        pas = 50 px/carreau
        """
        pts = [
            ( 25,  10),   # S  départ haut-gauche
            (625,  10),   # → 12
            (625, 510),   # ↓ 10
            (125, 510),   # ← 10
            (125, 210),   # ↑  6
            (525, 210),   # →  8
            (525, 410),   # ↓  4
            (225, 410),   # ←  6
            (225, 310),   # ↑  2
            (425, 310),   # →  4  A arrivée
        ]
        pygame.draw.lines(self.line_surface, LINE_COLOR, False, pts, LINE_WIDTH)

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