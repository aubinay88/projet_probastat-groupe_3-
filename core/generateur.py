"""
Module : generateur.py
Objet  : Génération des variables aléatoires exponentielles par inversion de CDF.
Ref    : Algorithme 1 — Formalisation algorithmique
"""

import math
import random
from typing import Optional


# ─────────────────────────────────────────────────────────────────
# CONSTANTE : graine par défaut (reproductibilité des résultats)
# ─────────────────────────────────────────────────────────────────
GRAINE_DEFAUT: int = 42


def initialiser_graine(graine: Optional[int] = None) -> None:
    """
    Initialise la graine du générateur pseudo-aléatoire.

    Args:
        graine: Entier pour la graine. Si None, graine aléatoire (temps système).

    Note:
        Utiliser une graine fixe garantit la reproductibilité exacte
        des résultats — essentiel pour la validation et le débogage.
    """
    if graine is not None:
        random.seed(graine)
    # Si graine=None, random utilise le temps système => irréproductible


def generer_exp(taux: float) -> float:
    """
    Génère une réalisation de la loi exponentielle Exp(taux).

    Méthode : Inversion de la CDF.
      Si U ~ Unif(0,1), alors X = -ln(U)/taux ~ Exp(taux).
      Preuve : F(x) = 1 - e^(-taux*x)
               F^(-1)(u) = -ln(1-u)/taux
               Or (1-U) ~ Unif(0,1) si U ~ Unif(0,1) => on utilise -ln(u)/taux

    Args:
        taux: Paramètre de la loi exponentielle (taux > 0).

    Returns:
        Réalisation x > 0 de Exp(taux).

    Raises:
        ValueError: Si taux <= 0.
    """
    if taux <= 0:
        raise ValueError(f"taux doit être > 0, reçu : {taux}")

    while True:
        u = random.random()     # u ~ Unif(0, 1)
        if u > 0:               # Évite ln(0) = -infini
            break

    x = -math.log(u) / taux    # Inversion de la CDF : F^(-1)(u)

    assert x > 0, f"Postcondition : x doit être > 0, obtenu {x}"
    return x


def generer_inter_arrivee(lambda_: float) -> float:
    """Génère un temps inter-arrivées Ta ~ Exp(lambda_)."""
    return generer_exp(lambda_)


def generer_duree_service(mu: float) -> float:
    """Génère une durée de service Ts ~ Exp(mu)."""
    return generer_exp(mu)


def generer_patience(theta: float) -> float:
    """
    Génère un seuil de patience Tp ~ Exp(theta).

    Cas particulier : si theta == 0 (clients infiniment patients),
    retourne +inf (le client ne part jamais).
    """
    if theta == 0.0:
        return float("inf")     # Client infiniment patient
    return generer_exp(theta)


# ─────────────────────────────────────────────────────────────────
# Fonctions de validation statistique
# ─────────────────────────────────────────────────────────────────
def valider_generateur(taux: float, n: int = 100_000) -> dict:
    """
    Valide le générateur en comparant moyenne empirique à 1/taux.

    Args:
        taux : Paramètre de la loi à tester.
        n    : Nombre de tirages pour la validation.

    Returns:
        Dict avec moyenne_empirique, moyenne_theorique, erreur_relative_%.
    """
    echantillon = [generer_exp(taux) for _ in range(n)]
    moy_emp  = sum(echantillon) / n
    moy_theo = 1.0 / taux
    erreur   = abs(moy_emp - moy_theo) / moy_theo * 100

    return {
        "moyenne_empirique" : round(moy_emp, 6),
        "moyenne_theorique" : round(moy_theo, 6),
        "erreur_relative_%" : round(erreur, 4),
        "valide"            : erreur < 1.0   # Tolérance 1%
    }
