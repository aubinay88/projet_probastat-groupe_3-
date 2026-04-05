"""
Module : monte_carlo.py
Objet  : Cadre Monte Carlo — agrégation de N_sim réalisations DES.
Ref    : Algorithme 4 — Formalisation algorithmique
"""

import math
import statistics
from typing import List

from core.simulation_des import simuler_une_realisation
from core.structures      import ResultatRealisation, ResultatMonteCarlo


# Quantile de la loi normale standard pour IC à 95%
Z_95: float = 1.96

#  FONCTIONS UTILITAIRES

def _intervalle_confiance(valeurs: List[float]) -> tuple:
   
    n = len(valeurs)
    if n < 2:
        return (valeurs[0], valeurs[0])

    moy    = statistics.mean(valeurs)
    sigma  = statistics.stdev(valeurs)
    erreur = Z_95 * sigma / math.sqrt(n)

    return (moy - erreur, moy + erreur)


def _valider_loi_little(
        lq_moy  : float,
        wq_moy  : float,
        lambda_ : float,
        pa_moy  : float
) -> float:
    
    if wq_moy <= 0 or lq_moy <= 0:
        return 0.0

    lambda_eff = lambda_ * (1.0 - pa_moy)
    lq_little  = lambda_eff * wq_moy
    erreur_pct = abs(lq_moy - lq_little) / lq_moy * 100.0

    return round(erreur_pct, 4)


#  FONCTION PRINCIPALE

def monte_carlo(
        lambda_ : float,
        mu      : float,
        theta   : float,
        K       : int,
        N_sim   : int,
        T_max   : float,
        verbose : bool = False
) -> ResultatMonteCarlo:
   
    # ── Vérification des préconditions (Algorithme 0) ──
    if lambda_ <= 0 : raise ValueError(f"lambda_ doit être > 0, reçu : {lambda_}")
    if mu      <= 0 : raise ValueError(f"mu doit être > 0, reçu : {mu}")
    if theta   <  0 : raise ValueError(f"theta doit être >= 0, reçu : {theta}")
    if K       <  1 : raise ValueError(f"K doit être >= 1, reçu : {K}")
    if N_sim   <  1 : raise ValueError(f"N_sim doit être >= 1, reçu : {N_sim}")
    if T_max   <= 0 : raise ValueError(f"T_max doit être > 0, reçu : {T_max}")

    # ── Vecteurs de collecte ──
    vec_wq  : List[float] = []
    vec_lq  : List[float] = []
    vec_rho : List[float] = []
    vec_pa  : List[float] = []
    vec_w   : List[float] = []


    # BOUCLE PRINCIPALE MONTE CARLO

    for sim in range(1, N_sim + 1):
        res: ResultatRealisation = simuler_une_realisation(
            lambda_=lambda_, mu=mu, theta=theta, K=K, T_max=T_max
        )
        vec_wq.append(res.wq)
        vec_lq.append(res.lq)
        vec_rho.append(res.rho)
        vec_pa.append(res.pa)
        vec_w.append(res.w)

        if verbose and sim % 100 == 0:
            print(f"  Progression : {sim}/{N_sim} réalisations...")

    # ── Estimateurs (loi des grands nombres) ──
    wq_moy  = statistics.mean(vec_wq)
    lq_moy  = statistics.mean(vec_lq)
    rho_moy = statistics.mean(vec_rho)
    pa_moy  = statistics.mean(vec_pa)
    w_moy   = statistics.mean(vec_w)

    # ── Intervalles de confiance à 95% (TCL) ──
    wq_ic  = _intervalle_confiance(vec_wq)
    lq_ic  = _intervalle_confiance(vec_lq)
    rho_ic = _intervalle_confiance(vec_rho)
    pa_ic  = _intervalle_confiance(vec_pa)
    w_ic   = _intervalle_confiance(vec_w)

    # ── Validation croisée par la loi de Little ──
    erreur_little = _valider_loi_little(lq_moy, wq_moy, lambda_, pa_moy)
    if erreur_little > 5.0:
        print(f"[AVERTISSEMENT] Loi de Little : erreur = {erreur_little:.2f}%")
        print("  => Augmenter T_max ou N_sim pour améliorer la convergence.")

    return ResultatMonteCarlo(
        wq_moy=wq_moy, lq_moy=lq_moy, rho_moy=rho_moy,
        pa_moy=pa_moy, w_moy=w_moy,
        wq_ic=wq_ic, lq_ic=lq_ic, rho_ic=rho_ic,
        pa_ic=pa_ic, w_ic=w_ic,
        erreur_little_pct=erreur_little,
        n_sim=N_sim
    )
