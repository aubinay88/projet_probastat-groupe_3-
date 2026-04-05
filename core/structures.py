

from dataclasses import dataclass, field
from typing import List, Optional
from collections import deque


#  CLASSE CLIENT
@dataclass
class Client:

    id_client   : int
    t_arrivee   : float
    deadline    : float
    t_debut_srv : Optional[float] = None
    t_fin_srv   : Optional[float] = None
    abandonne   : bool = False
    rejete      : bool = False

    @property
    def wq(self) -> Optional[float]:
        """Temps d'attente en file (None si non servi)."""
        if self.t_debut_srv is None:
            return None
        return self.t_debut_srv - self.t_arrivee

    @property
    def w(self) -> Optional[float]:
        """Temps total dans le système (None si non servi)."""
        if self.t_fin_srv is None:
            return None
        return self.t_fin_srv - self.t_arrivee

    @property
    def est_servi(self) -> bool:
        """True si le client a été complètement servi."""
        return self.t_fin_srv is not None

@dataclass
class EtatSysteme:
    """

    Attributes:
        t             : Horloge courante.
        t_precedent   : Horloge au dernier événement traité.
        serveur_libre : True si le serveur est disponible.
        t_fin_service : Heure de fin du service en cours (+inf si libre).
        file          : File d'attente (deque FIFO de clients).
        t_proch_arr   : Heure de la prochaine arrivée planifiée.
        n_arrives     : Nombre total de clients arrivés.
        n_servis      : Nombre de clients servis.
        n_rejetes     : Nombre de clients rejetés (file pleine).
        n_abandons    : Nombre de clients ayant abandonné.
        somme_wq      : Somme cumulée des temps d'attente individuels.
        aire_file     : Intégrale temporelle de Nq(t) (Riemann).
        temps_occupe  : Durée totale où le serveur est actif.
    """
    
    t             : float = 0.0
    t_precedent   : float = 0.0
    serveur_libre : bool  = True
    t_fin_service : float = field(default_factory=lambda: float("inf"))
    file          : deque = field(default_factory=deque)
    t_proch_arr   : float = 0.0
    # Accumulateurs
    n_arrives     : int   = 0
    n_servis      : int   = 0
    n_rejetes     : int   = 0
    n_abandons    : int   = 0
    somme_wq      : float = 0.0
    aire_file     : float = 0.0
    temps_occupe  : float = 0.0

    @property
    def longueur_file(self) -> int:
        return len(self.file) #Nombre de clients actuellement en file d'attente Nq(t).

    @property
    def n_dans_systeme(self) -> int:
        return len(self.file) + (0 if self.serveur_libre else 1) #Nombre total de clients dans le système : file + serveur.

    def prochain_abandon(self) -> float:
        if not self.file:
            return float("inf")
        return min(client.deadline for client in self.file) #Prochain temps d'abandon (minimum des deadlines des clients en file, ou +inf si file vide).

@dataclass
class ResultatRealisation:
    
    wq         : float   # Temps moyen d'attente en file (servis seulement)
    lq         : float   # Longueur moyenne de la file
    rho        : float   # Taux d'occupation du serveur
    pa         : float   # Taux d'abandon
    w          : float   # Temps total moyen dans le système
    n_servis   : int     # Nombre de clients servis
    n_arrives  : int     # Nombre de clients arrivés
    n_abandons : int     # Nombre d'abandons
    n_rejetes  : int     # Nombre de rejets (file pleine)


@dataclass
class ResultatMonteCarlo:
    wq_moy  : float   # Estimateur Ŵq
    lq_moy  : float   # Estimateur L̂q
    rho_moy : float   # Estimateur ρ̂
    pa_moy  : float   # Estimateur P̂a
    w_moy   : float   # Estimateur Ŵ
    
    # Intervalles de confiance à 95% (borne inf, borne sup)
    wq_ic   : tuple   # (wq_inf, wq_sup)
    lq_ic   : tuple   # (lq_inf, lq_sup)
    rho_ic  : tuple   # (rho_inf, rho_sup)
    pa_ic   : tuple   # (pa_inf, pa_sup)
    w_ic    : tuple   # (w_inf, w_sup)
    
    # Validation
    erreur_little_pct : float   # Écart % à la loi de Little
    n_sim             : int     # Nombre de réalisations effectuées
