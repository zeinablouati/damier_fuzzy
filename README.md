# Damier Fuzzy — Suivi de ligne par logique floue

Simulation d'un robot autonome qui suit une ligne tracée sur un damier noir/blanc,
guidé par un contrôleur à logique floue.

---

## Lancer le projet

```bash
pip install -r requirements.txt
python main.py
```

---

## Description du projet

Le robot se déplace sur un **damier noir et blanc** (cases de 60 px).
Une ligne est tracée sur ce damier ; elle apparaît **blanche sur fond noir** et
**noire sur fond blanc** grâce à un effet XOR (la ligne reste toujours visible
quelle que soit la couleur de la case sous-jacente).

Le robot doit suivre cette ligne depuis un **point de départ S** jusqu'à un
**point d'arrivée A**, sans jamais quitter le tracé.

---

## Architecture des fichiers

```
damier_fuzzy/
├── main.py              # Point d'entrée
├── requirements.txt
├── README.md
└── src/
    ├── circuit.py       # Dessin du damier, des circuits et effet XOR
    ├── robot.py         # Position, angle, vitesse, trajectoire
    ├── sensors.py       # Barre de 16 capteurs binaires
    ├── fuzzy.py         # Contrôleur à logique floue
    └── simulation.py    # Boucle principale, affichage, panneau info
```

---

## Circuits disponibles

| Touche | Nom                   | Description                                      |
|--------|-----------------------|--------------------------------------------------|
| `1`    | Parcours 7 segments   | Chemin ouvert en L/S : 7 segments orthogonaux    |
| `2`    | Spirale inversée      | 9 segments en spirale de l'extérieur vers le centre |
| `3`    | Double boucle         | Rectangle avec séparateur horizontal (2 boucles) |

---

## Règles de fonctionnement du robot

### 1. Détection de la ligne — 16 capteurs binaires

Le robot possède une **barre de 16 capteurs** placée 25 px devant lui,
perpendiculairement à sa direction.

- Chaque capteur lit le pixel sous sa position.
- Il vaut **1** si la luminosité du pixel est > 128 (ligne détectée), **0** sinon.
- Les 8 capteurs de **gauche** forment un nombre `G` (poids fort à l'extérieur gauche).
- Les 8 capteurs de **droite** forment un nombre `D` (poids fort à l'extérieur droite).

```
capteurs :  [G7 G6 G5 G4 G3 G2 G1 G0 | D0 D1 D2 D3 D4 D5 D6 D7]
                gauche (8 bits)           droite (8 bits)
```

### 2. Calcul de l'erreur (delta)

```
delta = D - G
```

| Valeur de delta | Signification          |
|-----------------|------------------------|
| delta < 0       | Ligne à **gauche**     |
| delta ≈ 0       | Ligne **centrée**      |
| delta > 0       | Ligne à **droite**     |

---

### 3. Contrôleur à logique floue

Le delta est transformé en correction d'angle `da` par trois règles floues :

#### Fonctions d'appartenance (fuzzification)

| Prédicat | Condition        | Interprétation       |
|----------|------------------|----------------------|
| **N**    | delta négatif    | Ligne à gauche       |
| **Z**    | delta ≈ 0        | Ligne centrée        |
| **P**    | delta positif    | Ligne à droite       |

```
mu_N(delta) = -delta / 120      si delta ∈ [-120, 0]
mu_Z(delta) = 1 - |delta| / 60  si |delta| < 60
mu_P(delta) =  delta / 120      si delta ∈ [0, +120]
```

#### Règles floues (inférence Mamdani)

```
SI delta est N  →  tourner à GAUCHE   (da = -35°)
SI delta est Z  →  aller TOUT DROIT   (da =   0°)
SI delta est P  →  tourner à DROITE   (da = +35°)
```

#### Défuzzification (centre de gravité)

```
da_brut = (mu_N × (-35) + mu_Z × 0 + mu_P × (+35)) / (mu_N + mu_Z + mu_P)
```

#### Lissage anti-oscillation

```
da = 0.8 × da_brut + 0.2 × da_précédent
```

Ce filtre évite les zigzags trop brusques sur les lignes droites.

---

### 4. Recherche à 90° si la ligne est perdue

Si **aucun capteur** ne détecte la ligne (tous à 0) :

1. Essai à **gauche** : lire les capteurs avec `angle − 90°`
   - Si ligne trouvée → tourner de −90° et continuer.
2. Sinon, essai à **droite** : lire les capteurs avec `angle + 90°`
   - Si ligne trouvée → tourner de +90° et continuer.
3. Si toujours rien → garder l'angle actuel (le robot reste sur place).

Cette règle permet de négocier **tous les virages à angle droit** des circuits.

---

### 5. Contrainte : ne jamais quitter le circuit (rollback)

Après chaque déplacement :

- Les capteurs relisent la nouvelle position.
- Si **aucun capteur** n'est actif → le déplacement est **annulé** (retour à la position précédente).
- Le robot ne peut donc **jamais sortir du tracé**.

---

### 6. Détection d'arrivée

Quand la distance entre le robot et le point **A** est inférieure à **30 px**,
la simulation se met en pause et affiche « ARRIVÉ ! ».

---

## Contrôles clavier

| Touche      | Action                        |
|-------------|-------------------------------|
| `ESPACE`    | Démarrer / Pause              |
| `R`         | Réinitialiser (retour en S)   |
| `1` `2` `3` | Changer de circuit            |
| `+` / `-`   | Augmenter / réduire la vitesse|
| `S`         | Afficher / masquer les capteurs|
| `T`         | Afficher / masquer la trajectoire|
| `ESC`       | Quitter                       |

---

## Dépendances

| Bibliothèque | Rôle                                      |
|--------------|-------------------------------------------|
| `pygame`     | Fenêtre, dessin, événements clavier       |
| `numpy`      | Calcul XOR pixel-à-pixel (effet damier)   |
