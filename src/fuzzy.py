# src/fuzzy.py
class FuzzyController:
    def __init__(self):
        self.delta_range = 100
        self.zero_range  =  35
        self.OUT_N = -45.0
        self.OUT_Z =   0.0
        self.OUT_P = +45.0
        self.mu_N = self.mu_Z = self.mu_P = 0.0
        self.last_da = 0.0

    def calc_N(self, d):
        if d >= 0: return 0.0
        if d <= -self.delta_range: return 1.0
        return -d / self.delta_range

    def calc_Z(self, d):
        ad = abs(d)
        if ad >= self.zero_range: return 0.0
        return 1.0 - ad / self.zero_range

    def calc_P(self, d):
        if d <= 0: return 0.0
        if d >= self.delta_range: return 1.0
        return d / self.delta_range

    def compute(self, delta):
        mN, mZ, mP = self.calc_N(delta), self.calc_Z(delta), self.calc_P(delta)
        total = mN + mZ + mP
        if total == 0: return self.last_da
        self.mu_N, self.mu_Z, self.mu_P = mN, mZ, mP
        da = (mN*self.OUT_N + mZ*self.OUT_Z + mP*self.OUT_P) / total
        self.last_da = da
        return da

    def get_memberships(self):
        return {'N': self.mu_N, 'Z': self.mu_Z, 'P': self.mu_P}