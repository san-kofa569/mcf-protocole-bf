# mcf-protocole-bf

Protocole série entre un système de facturation d'entreprise (SFE) et le module de contrôle de facturation (MCF)
du SECeF burkinabè, établi par essais sur un **Datamega FIS-NANO** relié par USB à l'environnement de test de la DGI.
Le protocole officiel n'est pas public : tout ce qui est ici a été observé sur l'appareil, lu dans du code tiers
public ou dans les textes publics de la DGI, et chaque point dit d'où il vient.

**État (2026-10-28) : cycle complet prouvé**, jusqu'à une facture certifiée sur l'environnement de test :
C3 (client) → C0 (ouverture, avec PSVB) → 31 (article) → 33 (sous-total) → 35 (paiement) → 38 (normalisation).
La référence est [`docs/REFERENCE_PROTOCOLE.md`](docs/REFERENCE_PROTOCOLE.md).

## Le cycle en bref

| Commande | Données | Réponse |
|---|---|---|
| C3 client | `type,IFU,nom,adresse,tél,e-mail,RCCM` (7 champs) | `R` |
| C0 ouverture | `op,nom_op,IFU,FV,TTC,ISF,FN,PSVB` — sans PSVB, aucun article n'est accepté | `n,tc,` + client |
| 31 article | `nom⇥LOCBIE,B18.0%100.00⇥100.00*1` (type, groupe et taux, montant ; prix*quantité) | `TTC,HT,TVA,…` |
| 33 sous-total | aucune | 35 champs : total, 16 montants, 16 TVA, PSVB, … |
| 35 paiement | `E102.00` (mode + montant) | `R` + reste |
| 38 normalisation | `102.00` (le total du 33, seul) | compteurs, type, date, NIM, IFU, signature, FN |

Trame de la famille Datecs : `01 LEN SEQ CMD DONNÉES 05 BCC 03`, 115200 8N1. Le protocole est de la famille du
« PROTOCOLE MCF-SFE v1.0 » de la DGI de la RDC ; le Burkina y ajoute le PSVB et un 38 à une seule donnée.

## Structure

| Dossier | Contenu |
|---|---|
| `appareil/` | `trame.py` (envoi d'une trame, lecture de la réponse) ; grilles d'essai bornées ; `essais/` charges utiles |
| `simulateur/` | jumeau du MCF : rend ce qui a été observé, pour éprouver un client sans l'appareil |
| `tests/` | tests (`python3 -m pytest -q`) |
| `recherche/` | notes datées : hypothèses, sources, déroulé des essais trame par trame |
| `docs/` | référence du protocole, plan d'essais, logiciels tiers consultés |
| `officiel/` | textes publics de la DGI du Burkina, empreintes dans `EMPREINTES.sha256` |

Non publiés (ignorés) : `appareil/brut/` (captures réelles de l'appareil), `externe/` (logiciels et documents tiers
téléchargés pour lecture, empreintes dans `docs/EXTERNE.md`).

## Envoyer une trame

```bash
python3 appareil/trame.py /dev/ttyACM0 20 C1 --simulation      # affiche la trame, n'envoie rien
export MCF_IFU=                                                 # suivi de l'IFU de l'appareil (9 caractères)
python3 appareil/trame.py /dev/ttyACM0 27 C0 "$(cat appareil/essais/sondes/c0_facture_8_psvb.txt)"
```

`{IFU}` dans une charge utile est remplacé par `MCF_IFU` ; sans cette variable valide, rien n'est envoyé.

## Données

- Aucune donnée réelle : l'IFU s'écrit `{IFU}`, le NIM `{NIM}`. Les clients, téléphones et e-mails des essais sont
  fictifs. L'ISF des essais, une valeur libre non attribuée par la DGI, s'écrit `ISF-ESSAI`.
- L'appareil utilisé est en mode Test, sur l'environnement de développement de la DGI.

## Règles d'essai

- Une commande à la fois vers le MCF, ou une grille bornée (une trame toutes les 3 s, arrêt au premier message
  nouveau) ; aucun geste irréversible (activation, personnalisation, réinitialisation, mise à jour).
- Chaque grille est jouée sur le jumeau avant l'appareil.
- Une hypothèse se confronte à un texte officiel ou à l'appareil avant d'être codée.
