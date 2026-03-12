# src/circuit.py
import math
import pygame
import numpy as np
from collections import defaultdict
from src.pathfinder import (bfs_shortest, get_snake_path, get_diagonal_path,
                             START, END)

BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
LINE_COLOR = (255, 255, 255)

CELL_SIZE  = 60
BAND_WIDTH = 22


def cell_center(c, r):
    return c * CELL_SIZE + CELL_SIZE // 2, r * CELL_SIZE + CELL_SIZE // 2


# ── Direction → vecteur (dc, dr) ────────────────────────
DIR_VECTORS = {
    'N':  ( 0, -1), 'S':  ( 0,  1),
    'E':  ( 1,  0), 'W':  (-1,  0),
    'NE': ( 1, -1), 'SE': ( 1,  1),
    'SW': (-1,  1), 'NW': (-1, -1),
}

# ── Direction → point extrémité dans la case ────────────
def _band_endpoint(c, r, direction):
    """
    Pixel d'extrémité de la bande pour la direction donnée,
    depuis le centre de la case (c, r).
    H/V  → milieu du bord concerné.
    Diag → coin concerné.
    """
    CS  = CELL_SIZE
    cx, cy = cell_center(c, r)
    left   = c  * CS
    right  = (c+1) * CS
    top    = r  * CS
    bottom = (r+1) * CS
    mid_x  = cx
    mid_y  = cy

    return {
        'N':  (mid_x, top),
        'S':  (mid_x, bottom),
        'E':  (right,  mid_y),
        'W':  (left,   mid_y),
        'NE': (right,  top),
        'SE': (right,  bottom),
        'SW': (left,   bottom),
        'NW': (left,   top),
    }[direction]


class Circuit:
    """
    3 chemins :
      'court'    — BFS, ~17 cases, angles droits
      'long'     — 2 virages à 180° espacés, ~35 cases, coins arrondis
      'diagonal' — diagonales 45°, ~27 cases
    Les 3 sont dessinés ensemble sur combined_surface.
    Les capteurs lisent uniquement la surface du chemin actif.
    """

    def __init__(self, width=750, height=620):
        self.width  = width
        self.height = height

        self.board_surface    = pygame.Surface((width, height))
        self.combined_surface = pygame.Surface((width, height))

        self.line_surfaces = {
            'court':    pygame.Surface((width, height)),
            'long':     pygame.Surface((width, height)),
            'diagonal': pygame.Surface((width, height)),
        }

        self.paths = {
            'court':    bfs_shortest(),
            'long':     get_snake_path(),
            'diagonal': get_diagonal_path(),
        }
        self.active_mode = 'court'

        self._init()

    # ── Init ────────────────────────────────────────────────

    def _init(self):
        self._draw_board()
        for mode in ('court', 'long', 'diagonal'):
            self.line_surfaces[mode].fill(BLACK)

        self._draw_path_straight(self.line_surfaces['court'],
                                  self.paths['court'])
        self._draw_path_smooth(self.line_surfaces['long'],
                                self.paths['long'])
        self._draw_path_diagonal(self.line_surfaces['diagonal'],
                                  self.paths['diagonal'])
        self._build_combined()

    # ── Damier ──────────────────────────────────────────────

    def _draw_board(self):
        CS = CELL_SIZE
        for row in range(self.height // CS + 1):
            for col in range(self.width  // CS + 1):
                color = BLACK if (col + row) % 2 == 0 else WHITE
                pygame.draw.rect(self.board_surface, color,
                                 (col*CS, row*CS, CS, CS))

    # ── Combined surface (3 chemins inversés) ───────────────

    def _build_combined(self):
        board = pygame.surfarray.array3d(self.board_surface)
        mask  = np.zeros(board.shape[:2], dtype=bool)
        for surf in self.line_surfaces.values():
            arr   = pygame.surfarray.array3d(surf)
            mask |= arr[:, :, 0] > 128
        comb       = board.copy()
        comb[mask] = 255 - board[mask]
        pygame.surfarray.blit_array(self.combined_surface, comb)

    # ── Collecte des directions par case ────────────────────

    def _collect_dirs(self, path, closed=False):
        """
        Calcule pour chaque case ses directions de sortie.
        Supporte H, V et diagonales (dc=±1, dr=±1).
        """
        dirs = defaultdict(set)
        n = len(path)

        # Table inverse dc,dr → nom de direction
        inv = {v: k for k, v in DIR_VECTORS.items()}

        for i, (c, r) in enumerate(path):
            nbrs = []
            if closed:
                nbrs = [path[(i-1)%n], path[(i+1)%n]]
            else:
                if i > 0:     nbrs.append(path[i-1])
                if i < n-1:   nbrs.append(path[i+1])

            for nc, nr in nbrs:
                dc, dr = nc - c, nr - r
                # Normaliser pour les diagonales (dc,dr peut être ±1,±1)
                # (pour les segments droits dc ou dr = 0)
                key = (dc, dr)
                if key in inv:
                    dirs[(c, r)].add(inv[key])

        return dirs

    # ── CHEMIN COURT : bandes droites, angles 90° ───────────

    def _draw_cell_straight(self, surf, c, r, directions):
        cx, cy = cell_center(c, r)
        for d in directions:
            ep = _band_endpoint(c, r, d)
            pygame.draw.line(surf, LINE_COLOR, (cx, cy), ep, BAND_WIDTH)
        pygame.draw.circle(surf, LINE_COLOR, (cx, cy), BAND_WIDTH // 2)

    def _draw_path_straight(self, surf, path):
        for (c, r), dirs in self._collect_dirs(path).items():
            self._draw_cell_straight(surf, c, r, dirs)

    # ── CHEMIN LONG : coins arrondis pour les virages 90° ───

    def _draw_cell_smooth(self, surf, c, r, directions):
        CS = CELL_SIZE
        BW = BAND_WIDTH
        R  = CS // 2
        cx, cy = cell_center(c, r)
        d = frozenset(directions)

        if d == frozenset(['E', 'W']):
            pygame.draw.line(surf, LINE_COLOR, (cx-R, cy), (cx+R, cy), BW)
            return
        if d == frozenset(['N', 'S']):
            pygame.draw.line(surf, LINE_COLOR, (cx, cy-R), (cx, cy+R), BW)
            return

        corner_map = {
            frozenset(['E','S']): ((cx+R, cy+R), -math.pi/2, -math.pi),
            frozenset(['E','N']): ((cx+R, cy-R),  math.pi/2,  math.pi),
            frozenset(['W','S']): ((cx-R, cy+R), -math.pi/2,  0.0),
            frozenset(['W','N']): ((cx-R, cy-R),  math.pi/2,  0.0),
        }
        if d in corner_map:
            (acx, acy), a0, a1 = corner_map[d]
            pts = []
            for k in range(19):
                a = a0 + (a1 - a0) * k / 18
                pts.append((int(acx + R*math.cos(a)),
                             int(acy + R*math.sin(a))))
            pygame.draw.lines(surf, LINE_COLOR, False, pts, BW)
            return

        # Fallback T/croix
        for dd in directions:
            ep = _band_endpoint(c, r, dd)
            pygame.draw.line(surf, LINE_COLOR, (cx, cy), ep, BW)
        pygame.draw.circle(surf, LINE_COLOR, (cx, cy), BW // 2)

    def _draw_path_smooth(self, surf, path):
        for (c, r), dirs in self._collect_dirs(path).items():
            self._draw_cell_smooth(surf, c, r, dirs)

    # ── CHEMIN DIAGONAL : bandes à 45° ──────────────────────

    def _draw_cell_diagonal(self, surf, c, r, directions):
        """
        Trace les bandes dans la case en gérant les 8 directions.
        Pour les cases traversées en diagonale pure (ex: NW→SE),
        la bande va d'un coin à l'autre en passant par le centre.
        Pour les jonctions droit→diagonal, la bande relie le bord
        au coin concerné en passant par le centre.
        """
        cx, cy = cell_center(c, r)
        BW = BAND_WIDTH

        d = frozenset(directions)

        # ── Passage diagonal pur (coin à coin) ──────────────
        diag_pairs = {
            frozenset(['NW', 'SE']): ('NW', 'SE'),
            frozenset(['NE', 'SW']): ('NE', 'SW'),
        }
        if d in diag_pairs:
            d1, d2 = diag_pairs[d]
            ep1 = _band_endpoint(c, r, d1)
            ep2 = _band_endpoint(c, r, d2)
            pygame.draw.line(surf, LINE_COLOR, ep1, ep2, BW)
            pygame.draw.circle(surf, LINE_COLOR, (cx, cy), BW // 2)
            return

        # ── Cas général : une ligne par direction ────────────
        # (jonctions droit→diagonal ou jonctions multiples)
        for dd in directions:
            ep = _band_endpoint(c, r, dd)
            pygame.draw.line(surf, LINE_COLOR, (cx, cy), ep, BW)
        pygame.draw.circle(surf, LINE_COLOR, (cx, cy), BW // 2)

    def _draw_path_diagonal(self, surf, path):
        for (c, r), dirs in self._collect_dirs(path).items():
            self._draw_cell_diagonal(surf, c, r, dirs)

    # ── Changement de chemin actif ──────────────────────────

    def set_mode(self, mode):
        self.active_mode = mode

    # ── Accesseurs ──────────────────────────────────────────

    def get_start(self):
        c, r = START
        px, py = cell_center(c, r)
        return px, py, 0

    def get_end(self):
        return cell_center(*END)

    def get_path_len(self, mode=None):
        return len(self.paths[mode or self.active_mode])

    def get_pixel_array(self):
        return pygame.surfarray.array3d(self.line_surfaces[self.active_mode])

    def get_name(self):
        return {'court': 'Court', 'long': 'Long',
                'diagonal': 'Diagonal 45°'}[self.active_mode]