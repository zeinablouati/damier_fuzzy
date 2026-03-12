# src/fuzzy.py

class FuzzyController:

    def __init__(self):
        # delta_range=255 : couvre la plage max de D (0..255) sans saturation
        self.delta_range = 255
        # zero_range=30 : zone neutre plus étroite → réaction plus précise
        self.zero_range  = 30
        # OUT_N/P réduits à ±15° : virages plus doux, moins de dépassement
        self.OUT_N = -15.0
        self.OUT_Z =   0.0
        self.OUT_P = +15.0
        self.mu_N  =  0.0
        self.mu_Z  =  0.0
        self.mu_P  =  0.0
        self.last_da = 0.0

    def calc_N(self, delta):
        """Négatif : ligne à gauche"""
        if delta >= 0:
            return 0.0
        if delta <= -self.delta_range:
            return 1.0
        return -delta / self.delta_range

    def calc_Z(self, delta):
        """Zéro : ligne centrée"""
        ad = abs(delta)
        if ad >= self.zero_range:
            return 0.0
        return 1.0 - ad / self.zero_range

    def calc_P(self, delta):
        """Positif : ligne à droite"""
        if delta <= 0:
            return 0.0
        if delta >= self.delta_range:
            return 1.0
        return delta / self.delta_range

    def compute(self, delta):
        mN = self.calc_N(delta)
        mZ = self.calc_Z(delta)
        mP = self.calc_P(delta)

        total = mN + mZ + mP

        # Aucun capteur actif (ne devrait plus arriver grâce à la recherche 90°)
        if total == 0:
            return 0.0

        self.mu_N = mN
        self.mu_Z = mZ
        self.mu_P = mP

        da_raw = (mN * self.OUT_N + mZ * self.OUT_Z + mP * self.OUT_P) / total

        # Léger amortissement pour éviter les oscillations
        da = 0.8 * da_raw + 0.2 * self.last_da
        self.last_da = da
        return da

    def get_memberships(self):
        return {'N': self.mu_N, 'Z': self.mu_Z, 'P': self.mu_P}