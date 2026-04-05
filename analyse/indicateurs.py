

from dataclasses import dataclass, field
from typing import List, Optional

from core.structures import ResultatMonteCarlo


# ══════════════════════════════════════════════════════════════════
#  CLASSES DE CONFIGURATION ET DE RÉSULTATS
# ══════════════════════════════════════════════════════════════════
@dataclass
class SeuilsQualite:
    """
    Seuils de qualité de service définis par l'opérateur.
    Valeurs par défaut typiques pour un centre d'appels.
    """
    rho_max : float = 0.85   # Taux d'occupation max acceptable
    pa_max  : float = 0.10   # Taux d'abandon max acceptable (10 %)
    wq_max  : float = 3.0    # Temps d'attente max acceptable (ut)


@dataclass
class AnalyseQualite:
    """Résultat de l'analyse de qualité de service."""
    score           : float
    alertes         : List[str]
    recommandations : List[str]
    statut          : str   # "OK", "ATTENTION", "CRITIQUE"


# ══════════════════════════════════════════════════════════════════
#  VALEURS THÉORIQUES
# ══════════════════════════════════════════════════════════════════
def calculer_valeurs_theoriques(lambda_: float, mu: float) -> dict:
    """
    Calcule les valeurs théoriques du modèle M/M/1 standard
    (sans abandon, sans capacité limitée, valable si ρ < 1).

    Formules de Pollaczek-Khinchine :
        ρ  = λ/μ
        Wq = ρ / (μ(1-ρ))
        W  = 1 / (μ(1-ρ))
        Lq = ρ² / (1-ρ)
        L  = ρ  / (1-ρ)

    Ces valeurs servent de référence pour la validation croisée.

    Returns:
        Dict avec rho, Wq_th, W_th, Lq_th, L_th, stable, note.
    """
    rho = lambda_ / mu

    if rho >= 1.0:
        return {
            "rho"    : rho,
            "stable" : False,
            "msg"    : f"Système instable : ρ = {rho:.4f} >= 1.0. Formules M/M/1 non valides."
        }

    Wq = rho / (mu * (1.0 - rho))
    W  = 1.0 / (mu * (1.0 - rho))
    Lq = rho**2 / (1.0 - rho)
    L  = rho    / (1.0 - rho)

    return {
        "rho"    : round(rho, 6),
        "Wq_th"  : round(Wq, 6),
        "W_th"   : round(W,  6),
        "Lq_th"  : round(Lq, 6),
        "L_th"   : round(L,  6),
        "stable" : True,
        "note"   : "Valeurs théoriques M/M/1 pur (sans abandon ni capacité limitée)"
    }


# ══════════════════════════════════════════════════════════════════
#  ANALYSE DE QUALITÉ
# ══════════════════════════════════════════════════════════════════
def analyser_qualite(
        res    : ResultatMonteCarlo,
        seuils : Optional[SeuilsQualite] = None
) -> AnalyseQualite:
    """
    Analyse la qualité de service et produit des recommandations.
    Correspond à ANALYSER_ET_RECOMMANDER() de l'Algorithme 5.

    Args:
        res    : Résultats Monte Carlo.
        seuils : Seuils de qualité. Si None, valeurs par défaut.

    Returns:
        AnalyseQualite avec score 0-100, alertes et recommandations.
    """
    if seuils is None:
        seuils = SeuilsQualite()

    alertes         : List[str] = []
    recommandations : List[str] = []
    penalite = 0.0

    # ── Analyse taux d'occupation ──
    if res.rho_moy > seuils.rho_max:
        alertes.append(
            f"CRITIQUE — ρ = {res.rho_moy:.3f} dépasse le seuil {seuils.rho_max}"
        )
        recommandations.append(
            "Réduire λ (limiter les arrivées) ou augmenter μ (accélérer le service)."
        )
        penalite += 30.0 * min(1.0, (res.rho_moy - seuils.rho_max) / 0.15)

    # ── Analyse taux d'abandon ──
    if res.pa_moy > seuils.pa_max:
        alertes.append(
            f"CRITIQUE — Pa = {res.pa_moy:.3f} ({res.pa_moy*100:.1f}%) "
            f"dépasse le seuil {seuils.pa_max*100:.0f}%"
        )
        recommandations.append(
            "Mettre en place un message d'attente (augmente la patience θ)."
        )
        recommandations.append(
            "Ou augmenter K (capacité de la file) pour éviter les rejets."
        )
        penalite += 40.0 * min(1.0, res.pa_moy / max(seuils.pa_max, 1e-9) - 1.0)

    # ── Analyse temps d'attente ──
    if res.wq_moy > seuils.wq_max:
        alertes.append(
            f"ATTENTION — Wq = {res.wq_moy:.3f} ut dépasse le seuil {seuils.wq_max} ut"
        )
        recommandations.append(
            "Envisager un deuxième agent pour réduire Wq."
        )
        penalite += 20.0 * min(1.0, (res.wq_moy - seuils.wq_max) / seuils.wq_max)

    # ── Validation loi de Little ──
    if res.erreur_little_pct > 5.0:
        alertes.append(
            f"AVERTISSEMENT — Loi de Little : écart = {res.erreur_little_pct:.2f}%"
        )
        recommandations.append(
            "Augmenter N_sim ou T_max pour améliorer la convergence."
        )

    # ── Score global ──
    score = max(0.0, 100.0 - penalite)

    if   score >= 80: statut = "OK"
    elif score >= 50: statut = "ATTENTION"
    else:             statut = "CRITIQUE"

    return AnalyseQualite(
        score=round(score, 1),
        alertes=alertes,
        recommandations=recommandations,
        statut=statut
    )


# ══════════════════════════════════════════════════════════════════
#  AFFICHAGE RAPPORT CONSOLE
# ══════════════════════════════════════════════════════════════════
def afficher_rapport(
        res     : ResultatMonteCarlo,
        analyse : AnalyseQualite,
        params  : dict
) -> None:
    """Affiche un rapport textuel formaté dans la console."""
    sep = "=" * 58
    print(sep)
    print("  RAPPORT DE SIMULATION — M/M/1 AVEC ABANDON")
    print(sep)
    print(f"  Paramètres : λ={params['lambda_']}, μ={params['mu']}, "
          f"θ={params['theta']}, K={params['K']}")
    print(f"               N_sim={params['N_sim']}, T_max={params['T_max']}")
    print(sep)
    print(f"  Wq  = {res.wq_moy:.4f}  IC95%: [{res.wq_ic[0]:.4f}, {res.wq_ic[1]:.4f}]")
    print(f"  Lq  = {res.lq_moy:.4f}  IC95%: [{res.lq_ic[0]:.4f}, {res.lq_ic[1]:.4f}]")
    print(f"  ρ   = {res.rho_moy:.4f}  IC95%: [{res.rho_ic[0]:.4f}, {res.rho_ic[1]:.4f}]")
    print(f"  Pa  = {res.pa_moy:.4f}  IC95%: [{res.pa_ic[0]:.4f}, {res.pa_ic[1]:.4f}]")
    print(f"  W   = {res.w_moy:.4f}  IC95%: [{res.w_ic[0]:.4f}, {res.w_ic[1]:.4f}]")
    print(f"  Loi de Little : écart = {res.erreur_little_pct:.2f}%")
    print(sep)
    print(f"  Statut QoS : {analyse.statut}  (Score : {analyse.score}/100)")
    for alerte in analyse.alertes:
        print(f"  [!] {alerte}")
    for rec in analyse.recommandations:
        print(f"  [→] {rec}")
    print(sep)
