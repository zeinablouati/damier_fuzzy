# main.py
# Point d'entrée du programme.
# Lancer avec : python main.py

from src.simulation import Simulation

if __name__ == "__main__":
    sim = Simulation(fps=60)
    sim.run()