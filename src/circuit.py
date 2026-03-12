# src/circuit.py
import pygame
import numpy as np
from collections import defaultdict

# ── Constantes ────────────────────────────────────────────
BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
LINE_COLOR = (255, 255, 255)   # couleur de la bande sur line_surface

CELL_SIZE  = 60   # taille d'une case du damier en pixels
BAND_WIDTH = 22   # largeur de la bande (~1/3 de la case)

# Grille : 12 colonnes x 10 lignes (12*60=720 < 750, 10*60=600 < 620)
GRID_COLS = 12
GRID_ROWS = 10


# ── Helpers de génération de chemin ──────────────────────

def _row(c0, c1, r):
    """Ligne horizontale de colonne c0 à c1 sur la ligne r."""
    step = 1 if c1 >= c0 else -1
    return [(c, r) for c in range(c0, c1 + step, step)]

def _col(r0, r1, c):
    """Ligne verticale de ligne r0 à r1 sur la colonne c."""
    step = 1 if r1 >= r0 else -1
    return [(c, r) for r in range(r0, r1 + step, step)]


class Circuit:
    """
    Principe (conforme au sujet) :
    ─────────────────────────────
    Le damier est un quadrillage noir/blanc.
    Le chemin passe par une séquence de cases (col, row).
    Dans chaque case traversée :
      • case NOIRE  → bande BLANCHE centrée
      • case BLANCHE → bande NOIRE  centrée
    La bande relie le centre de la case aux bords correspondant
    aux cases voisines dans le chemin (droite, gauche, haut, bas).
    Les coins sont donc des quarts de bandes perpendiculaires.

    line_surface  → toujours blanc sur noir (pour les capteurs binaires).
    combined_surface → alternance réelle N/B (pour l'affichage).
    """

    # (nom, pixel_x_départ, pixel_y_départ, angle_départ_deg)
    CIRCUITS = {
        1: ("Rectangle fermé",      150,  90, 0),   # 2e case de la ligne du haut
        2: ("Croisements",          150,  90, 0),
        3: ("Serpentin ouvert",     150,  90, 0),
    }

    # Point d'arrivée en pixels (None = boucle fermée = même que départ)
    ENDS = {
        1: None,
        2: None,
        3: (90, 510),   # centre de la case (1, 8)
    }

    def __init__(self, width=750, height=620):
        self.width  = width
        self.height = height

        self.board_surface    = pygame.Surface((width, height))
        self.line_surface     = pygame.Surface((width, height))
        self.combined_surface = pygame.Surface((width, height))

        self.current_id = 1
        self.load(1)

    # ── Damier ──────────────────────────────────────────────

    def _draw_board(self):
        CS = CELL_SIZE
        for row in range(self.height // CS + 1):
            for col in range(self.width  // CS + 1):
                color = BLACK if (col + row) % 2 == 0 else WHITE
                pygame.draw.rect(self.board_surface, color,
                                 (col * CS, row * CS, CS, CS))

    # ── Chargement ──────────────────────────────────────────

    def load(self, circuit_id):
        self.current_id = circuit_id
        self._draw_board()
        self.line_surface.fill(BLACK)

        if   circuit_id == 1: self._draw_circuit1()
        elif circuit_id == 2: self._draw_circuit2()
        elif circuit_id == 3: self._draw_circuit3()

        self._build_combined()

    # ── Surface combinée (alternance sans BLEND_XOR) ────────

    def _build_combined(self):
        """
        combined_surface = damier avec la ligne inversée.
        Pixels blancs de line_surface → inversés sur le damier.
        Calculé une seule fois par circuit.
        """
        board = pygame.surfarray.array3d(self.board_surface)
        line  = pygame.surfarray.array3d(self.line_surface)
        mask  = line[:, :, 0] > 128
        comb  = board.copy()
        comb[mask] = 255 - board[mask]
        pygame.surfarray.blit_array(self.combined_surface, comb)

    # ── Collecte des directions par case ────────────────────

    def _collect_directions(self, path, closed):
        """
        Pour chaque case du chemin, calcule vers quels bords
        la bande doit se prolonger (N / S / E / W).
        Retourne : dict (col, row) → set{'N','S','E','W'}
        """
        dirs = defaultdict(set)
        n = len(path)

        for i, (c, r) in enumerate(path):
            if closed:
                neighbors = [path[(i - 1) % n], path[(i + 1) % n]]
            else:
                neighbors = []
                if i > 0:     neighbors.append(path[i - 1])
                if i < n - 1: neighbors.append(path[i + 1])

            for nc, nr in neighbors:
                if   nc == c + 1: dirs[(c, r)].add('E')
                elif nc == c - 1: dirs[(c, r)].add('W')
                elif nr == r + 1: dirs[(c, r)].add('S')
                elif nr == r - 1: dirs[(c, r)].add('N')

        return dirs

    # ── Dessin d'une case du chemin ──────────────────────────

    def _draw_cell_band(self, c, r, directions):
        """
        Trace la bande dans la case (c, r) :
        - du centre de la case vers chaque bord concerné
        - disque central pour combler les coins
        La bande est TOUJOURS BLANCHE sur line_surface
        (l'alternance couleur est faite par numpy dans _build_combined).
        """
        CS = CELL_SIZE
        BW = BAND_WIDTH

        cx = c * CS + CS // 2   # centre pixel x
        cy = r * CS + CS // 2   # centre pixel y

        bords = {
            'N': (cx, r * CS),
            'S': (cx, (r + 1) * CS),
            'W': (c * CS, cy),
            'E': ((c + 1) * CS, cy),
        }

        for d in directions:
            ex, ey = bords[d]
            pygame.draw.line(self.line_surface, LINE_COLOR,
                             (cx, cy), (ex, ey), BW)

        # Disque central = raccord parfait quelle que soit la direction
        pygame.draw.circle(self.line_surface, LINE_COLOR, (cx, cy), BW // 2)

    # ── Tracé complet d'un chemin ────────────────────────────

    def _draw_path(self, *path_segments, closed=False):
        """
        Accepte un ou plusieurs segments de chemin (listes de cases).
        Les concatène, calcule les directions, puis dessine chaque case.
        Gère les croisements automatiquement (union des directions).
        """
        # Fusionner les directions de tous les segments
        all_dirs = defaultdict(set)

        for seg, seg_closed in path_segments:
            d = self._collect_directions(seg, seg_closed)
            for cell, dirs in d.items():
                all_dirs[cell] |= dirs

        # Dessiner chaque case une seule fois avec toutes ses directions
        for (c, r), dirs in all_dirs.items():
            self._draw_cell_band(c, r, dirs)

    # ── Circuit 1 : rectangle fermé ─────────────────────────

    def _draw_circuit1(self):
        """
        Boucle rectangulaire — 4 virages à 90°.
        Chemin : haut (→) + droite (↓) + bas (←) + gauche (↑)
        """
        path = (
            _row(1, 10, 1) +    # haut  →  cols 1..10, row 1
            _col(2,  8, 10) +   # droite ↓  col 10, rows 2..8
            _row(9,  1,  8) +   # bas   ←  cols 9..1, row 8
            _col(7,  2,  1)     # gauche ↑  col 1, rows 7..2
        )
        self._draw_path((path, True))

    # ── Circuit 2 : rectangle + croisements ─────────────────

    def _draw_circuit2(self):
        """
        Rectangle fermé + barre horizontale à row=4.
        Crée 2 croisements (col 1 et col 10).
        Au croisement : delta ≈ 0 → règle Z → tout droit.
        """
        rect = (
            _row(1, 10,  1) +
            _col(2,  8, 10) +
            _row(9,  1,  8) +
            _col(7,  2,  1)
        )
        # Barre de croisement (cols 2..9 : les coins 1 et 10 sont déjà dans rect)
        barre = _row(2, 9, 4)

        # Les cases (1,4) et (10,4) sont dans rect (N+S) ET dans barre (E ou W)
        # → _draw_path fusionne automatiquement les directions → croisement T
        self._draw_path((rect, True), (barre, False))

    # ── Circuit 3 : serpentin ouvert ────────────────────────

    def _draw_circuit3(self):
        """
        4 lignes horizontales reliées par des connecteurs verticaux.
        Chemin OUVERT : départ (1,1) → arrivée (1,8).
        Tous les virages à 90°.
        """
        path = (
            _row(1, 10,  1) +   # → row 1
            _col(2,  3, 10) +   # ↓ col 10, rows 2-3
            _row(9,  1,  3) +   # ← row 3
            _col(4,  6,  1) +   # ↓ col 1, rows 4-6
            _row(2, 10,  6) +   # → row 6
            _col(7,  8, 10) +   # ↓ col 10, rows 7-8
            _row(9,  1,  8)     # ← row 8
        )
        self._draw_path((path, False))

    # ── Accesseurs ──────────────────────────────────────────

    def get_start(self):
        _, x, y, a = self.CIRCUITS[self.current_id]
        return x, y, a

    def get_end(self):
        end = self.ENDS[self.current_id]
        if end is None:
            _, x, y, _ = self.CIRCUITS[self.current_id]
            return x, y
        return end

    def is_loop(self):
        return self.ENDS[self.current_id] is None

    def get_pixel_array(self):
        """line_surface (blanc/noir) — utilisée par les capteurs binaires."""
        return pygame.surfarray.array3d(self.line_surface)

    def get_name(self):
        name, _, _, _ = self.CIRCUITS[self.current_id]
        return name