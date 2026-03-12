# src/pathfinder.py
from collections import deque

GRID_COLS = 10
GRID_ROWS =  8
START     = (1, 1)
END       = (10, 8)

# 4-connexité pour BFS
DIRS4 = [(1,0),(-1,0),(0,1),(0,-1)]

def _nbrs(c, r):
    for dc, dr in DIRS4:
        nc, nr = c+dc, r+dr
        if 1 <= nc <= GRID_COLS and 1 <= nr <= GRID_ROWS:
            yield nc, nr


# ── Helpers ──────────────────────────────────────────────

def _row(c0, c1, r):
    s = 1 if c1 >= c0 else -1
    return [(c, r) for c in range(c0, c1+s, s)]

def _col(r0, r1, c):
    s = 1 if r1 >= r0 else -1
    return [(c, r) for r in range(r0, r1+s, s)]

def _diag(c0, r0, c1, r1):
    """
    Segment diagonal de (c0,r0) à (c1,r1).
    Seuls les vrais diagonaux 45° sont autorisés : |dc| == |dr|.
    """
    dc = 1 if c1 > c0 else -1
    dr = 1 if r1 > r0 else -1
    steps = abs(c1 - c0)
    return [(c0 + dc*i, r0 + dr*i) for i in range(steps + 1)]


# ── Chemin 1 : le plus court (BFS) ───────────────────────

def bfs_shortest(start=START, end=END):
    """Chemin le plus court S→F par BFS (4-connexité)."""
    prev  = {start: None}
    queue = deque([start])
    while queue:
        c, r = queue.popleft()
        for nc, nr in _nbrs(c, r):
            if (nc, nr) not in prev:
                prev[(nc, nr)] = (c, r)
                if (nc, nr) == end:
                    path, cur = [], end
                    while cur:
                        path.append(cur); cur = prev[cur]
                    return list(reversed(path))
                queue.append((nc, nr))
    return [start, end]


# ── Chemin 2 : long, 2 virages espacés ───────────────────

def get_snake_path():
    """
    3 segments horizontaux avec 2 virages à 180° très espacés.

    S(1,1) ──────────────────→ (10,1)
                                   │ 1er virage ↓ (5 rangées)
    (1,6) ←────────────────── (10,6)
       │ 2e virage ↓ (2 rangées)
    (1,8) ──────────────────→ F(10,8)
    """
    return (
        _row( 1, 10,  1)          +
        _col( 1,  6, 10)[1:]      +
        _row( 9,  1,  6)          +
        _col( 6,  8,  1)[1:]      +
        _row( 2, 10,  8)
    )


# ── Chemin 3 : complexe avec diagonales 45° ──────────────

def get_diagonal_path():
    """
    Chemin complexe mêlant segments droits H/V et diagonales à 45°.

    Tracé (grille 10×8) :

    S(1,1) → droite → (3,1)
                         ↘ diagonale SE
                           (4,2),(5,3),(6,4),(7,5)
                                              → droite → (10,5)
                                                            ↙ diagonale SW
                                                              (9,6),(8,7)
                                                                    → droite → (10,7)
                                                                                  ↓
                                                                               F(10,8)

    Angles présents :
      - 2 diagonales à 45° (SE et SW)
      - raccordements droite→diagonale et diagonale→droite
      - descente verticale finale
    """
    return (
        _row(1, 3, 1)              +   # (1,1)→(3,1)   horizontal →
        _diag(3, 1, 7, 5)[1:]     +   # (3,1)→(7,5)   diagonale  ↘  45°
        _row(7, 11, 5)[1:]        +   # (7,5)→(10,5)  horizontal →
        _diag(11, 5, 8, 7)[1:]   +   # (10,5)→(8,7)  diagonale  ↙  45°
        _row(8, 10, 7)[1:]        +   # (8,7)→(10,7)  horizontal →
        _col(7, 8, 10)[1:]            # (10,7)→(10,8) vertical   ↓
    )