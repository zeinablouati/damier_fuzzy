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


# ── Chemin 3 : 3 virages 45° + 1 virage 90°, espacés ────

def get_angles_path():
    """
    Chemin avec 3 virages à 45° et 1 virage à 90°, bien espacés.

    Tracé (grille 10×8) :

    S(1,1)
      ↘ diagonale SE
      (2,2),(3,3)
              ──────────────→ (6,3)   horizontal →  ← virage 45°
                                  ↓
                               (6,4)               ← virage 90° (H→V)
                               (6,5)
                               (6,6)
                                  ↘ diagonale SE   ← virage 45°
                                  (7,7),(8,8)
                                           ──→ F(10,8)  ← virage 45°

    Angles aux jonctions :
      45° : (3,3)  diagonale SE → horizontal        (espacé de 2 cases)
      90° : (6,3)  horizontal   → vertical ↓        (espacé de 3 cases)
      45° : (6,6)  vertical     → diagonale SE      (espacé de 3 cases)
      45° : (8,8)  diagonale SE → horizontal →      (espacé de 2 cases)
    """
    return (
        _diag(1, 1, 3, 3)         +   # (1,1)→(3,3)   diagonale  ↘
        _row(3, 6, 3)[1:]         +   # (3,3)→(6,3)   horizontal →  [virage 45°]
        _col(3, 6, 6)[1:]         +   # (6,3)→(6,6)   vertical   ↓  [virage 90° H→V]
        _diag(6, 6, 8, 8)[1:]    +   # (6,6)→(8,8)   diagonale  ↘  [virage 45°]
        _row(8, 10, 8)[1:]            # (8,8)→(10,8)  horizontal →  [virage 45°]
    )