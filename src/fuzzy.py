# src/fuzzy.py

class FuzzyController:
    """
    Contrôleur flou à 3 prédicats : N, Z, P.
    Entrée  : delta = D − G  (capteurs droite − gauche)
    Sortie  : da    = variation d'angle en degrés/pas
    3 règles : SI delta est N → da est N (gauche)
               SI delta est Z → da est Z (tout droit)
               SI delta est P → da est P (droite)
    """

    def __init__(self):
        self.delta_range = 100
        self.zero_range  =  35
        self.OUT_N = -45.0
        self.OUT_Z =   0.0
        self.OUT_P = +45.0
        self.mu_N    = 0.0
        self.mu_Z    = 0.0
        self.mu_P    = 0.0
        self.last_da = 0.0

    def calc_N(self, delta):
        if delta >= 0: return 0.0
        if delta <= -self.delta_range: return 1.0
        return -delta / self.delta_range

    def calc_Z(self, delta):
        ad = abs(delta)
        if ad >= self.zero_range: return 0.0
        return 1.0 - ad / self.zero_range

    def calc_P(self, delta):
        if delta <= 0: return 0.0
        if delta >= self.delta_range: return 1.0
        return delta / self.delta_range

    def compute(self, delta):
        mN = self.calc_N(delta)
        mZ = self.calc_Z(delta)
        mP = self.calc_P(delta)
        total = mN + mZ + mP
        if total == 0:
            return self.last_da
        self.mu_N = mN
        self.mu_Z = mZ
        self.mu_P = mP
        da = (mN * self.OUT_N + mZ * self.OUT_Z + mP * self.OUT_P) / total
        self.last_da = da
        return da

    def get_memberships(self):
        return {'N': self.mu_N, 'Z': self.mu_Z, 'P': self.mu_P}