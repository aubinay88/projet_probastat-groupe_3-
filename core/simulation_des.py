

from collections import deque
from core.generateur import generer_inter_arrivee, generer_duree_service, generer_patience
from core.structures  import Client, EtatSysteme, ResultatRealisation

def initialiser_systeme(lambda_: float) -> EtatSysteme:
    
    etat = EtatSysteme()
    etat.t_proch_arr = generer_inter_arrivee(lambda_)  # 1ère arrivée
    return etat

def _avancer_horloge(etat: EtatSysteme, t_evt: float) -> None:
    delta = t_evt - etat.t_precedent
    if delta < 0:
        raise RuntimeError(f"Temps négatif : delta={delta:.6f} (t_evt={t_evt}, t_prec={etat.t_precedent})")
    
    etat.aire_file    += etat.longueur_file * delta

    
    if not etat.serveur_libre:
        etat.temps_occupe += delta

    etat.t           = t_evt
    etat.t_precedent = t_evt


def _demarrer_service(etat: EtatSysteme, mu: float) -> None:

    assert etat.serveur_libre, " serveur doit être libre"
    assert etat.file,          "file ne doit pas être vide"

    client = etat.file.popleft()
    wq_i   = etat.t - client.t_arrivee   #

    etat.somme_wq  += wq_i
    etat.n_servis  += 1

    # Mise à jour client
    client.t_debut_srv  = etat.t
    duree_service       = generer_duree_service(mu)
    client.t_fin_srv    = etat.t + duree_service

    # Mise à jour serveur
    etat.t_fin_service  = client.t_fin_srv
    etat.serveur_libre  = False


def _purger_expires(etat: EtatSysteme) -> None:
    n_avant  = len(etat.file)
    etat.file = deque(c for c in etat.file if c.deadline > etat.t)
    n_apres  = len(etat.file)
    etat.n_abandons += (n_avant - n_apres)


def _traiter_arrivee(
        etat       : EtatSysteme,
        K          : int,
        theta      : float,
        mu         : float,
        lambda_    : float,
        compteur_id: list
) -> None:

    etat.n_arrives += 1
    t = etat.t

    if etat.longueur_file < K:
        patience_i = generer_patience(theta)
        deadline_i = t + patience_i

        compteur_id[0] += 1
        client = Client(
            id_client = compteur_id[0],
            t_arrivee = t,
            deadline  = deadline_i
        )
        etat.file.append(client)

        if etat.serveur_libre:
            _demarrer_service(etat, mu)
    else:
        etat.n_rejetes += 1
    etat.t_proch_arr = t + generer_inter_arrivee(lambda_)


def _traiter_fin_service(etat: EtatSysteme, mu: float) -> None:
    
    etat.t_fin_service = float("inf")
    etat.serveur_libre = True

    _purger_expires(etat)   # Nettoyer avant de prendre le suivant

    if etat.file:
        _demarrer_service(etat, mu)


def _traiter_abandon(etat: EtatSysteme, t_abandon: float) -> None:
    
    n_avant   = len(etat.file)
    etat.file = deque(c for c in etat.file if c.deadline > t_abandon)
    n_apres   = len(etat.file)
    etat.n_abandons += (n_avant - n_apres)


#  FONCTION PRINCIPALE
def simuler_une_realisation(
        lambda_ : float,
        mu      : float,
        theta   : float,
        K       : int,
        T_max   : float
) -> ResultatRealisation:
    etat         = initialiser_systeme(lambda_)
    compteur_id  = [0]   # Liste mutable pour l'ID des clients


    # BOUCLE PRINCIPALE DES : avancer événement par événement
    while True:

        t_ab  = etat.prochain_abandon()
        t_evt = min(etat.t_proch_arr, etat.t_fin_service, t_ab)
        if t_evt >= T_max:
            _avancer_horloge(etat, T_max)
            break
        _avancer_horloge(etat, t_evt)
        
        if t_evt == etat.t_proch_arr:
            _traiter_arrivee(etat, K, theta, mu, lambda_, compteur_id)

        elif t_evt == etat.t_fin_service:
            _traiter_fin_service(etat, mu)

        else:
            _traiter_abandon(etat, t_evt)

    # Calcul des indicateurs de cette réalisation
    T_eff = T_max
    wq  = etat.somme_wq    / etat.n_servis  if etat.n_servis  > 0 else 0.0
    lq  = etat.aire_file   / T_eff
    rho = etat.temps_occupe / T_eff
    pa  = etat.n_abandons  / etat.n_arrives  if etat.n_arrives > 0 else 0.0
    w   = wq + (1.0 / mu)

    # Postconditions de cohérence
    assert 0.0 <= rho <= 1.0 + 1e-9, f"ρ hors [0,1] : {rho:.6f}"
    assert 0.0 <= pa  <= 1.0,         f"Pa hors [0,1] : {pa:.6f}"
    assert lq  >= 0.0,                f"Lq négatif    : {lq:.6f}"

    return ResultatRealisation(
        wq=wq, lq=lq, rho=rho, pa=pa, w=w,
        n_servis=etat.n_servis,
        n_arrives=etat.n_arrives,
        n_abandons=etat.n_abandons,
        n_rejetes=etat.n_rejetes
    )
