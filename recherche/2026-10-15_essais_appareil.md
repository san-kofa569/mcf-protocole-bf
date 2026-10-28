# Essais sur le MCF du 2026-10-15

Une trame à la fois, lancée par l'opérateur, ou un script borné (une trame toutes les 3 s, 80 au plus, arrêt au premier message
nouveau). Heures du PC (UTC+2) ; l'horloge du MCF est en UTC et retarde d'environ 1 min. Captures dans `appareil/brut/` (hors
dépôt). IFU et NIM jamais recopiés ici. Résultat consolidé : `docs/REFERENCE_PROTOCOLE.md`.

## Déroulé

| Heure | Trame | Résultat |
|---|---|---|
| 11:28 à 11:34 | C1 ; C3 vide ; C0 Niger ; 31 Niger | C1 normal ; C3 vide `R` ; C0 accepté ; 31 refusé au format |
| 11:40 à 12:15 | rallumage ; 40 C3 vides ; C1 avec données de C0 ; USB rebranché à chaud | `R` partout : on crut à un état de l'appareil |
| 12:49 | C2 | dernier contact serveur = heure du démarrage |
| 12:51 | C3 `{IFU},CLIENT TEST,,,`, puis grille de 54 trames (`recherche_structure.py`) | « type de destinataire », puis, à la trame 7 (`PP,PP,PP,PP,PP,PP,PP`), `L'adresse e-mail du destinataire n'est pas valide` : premier message nouveau de C3 |
| 13:03 | même trame après un rallumage propre | même message : **pas d'état caché** |
| 13:07 | carte de C3, 17 trames (`carte_client.py`) | place 5 téléphone, place 6 e-mail, `R` = client accepté |
| 13:13 | C3 `PP,CLIENT TEST,,,70123456,client@example.com,` puis C0 | `R`, puis C0 recopie les champs 2 à 7 du client |
| 13:14 à 14:17 | grilles de 31 : nombres, gabarits, photo, anciens, groupes, nombres2, psvb ; FT, EV, ET, HT | plus de 340 formes, toutes au message de format |
| 14:02 | carte de C0, 22 trames (`carte_c0.py`) | chaque champ a son message ; le format est une erreur de longueur |
| 14:13 | C1 avant chaque nouvelle facture | C1 annule la facture ouverte (C3 = `R`, pas NAK) |

## Faits établis

Voir le détail dans `docs/REFERENCE_PROTOCOLE.md` : trame à 7 champs de C3, grammaire de C0 (IFU, type, mode, ISF, FN, PSVB),
C0 recopie le client, C1 et C2 annulent la facture, pas d'état caché.

## Rectification

La session du 14 (autre assistant) avait conclu à un format de C0 manquant, à un état caché et à la demande au fournisseur. Les
trois sont faux. Les « R » du 14 et du 15 jusqu'à 12:51 étaient les réponses à des C3 **vides**. Cinq hypothèses ont été
posées puis écartées par un essai (phase de démarrage, horloge, rallumage seul, USB seul, réseau).

## Ouvert

- 31 : un seul message pour toute erreur ; structure inconnue. Hypothèses : ISF non enregistré, tables non téléchargées,
  combinaison de plusieurs ajouts (type, unité, PSVB).
- Pistes de documentation fermées : portail SYGMEF développeur (identifiant requis, que l'opérateur n'a pas), plate-forme GDSECeF
  (le compte est celui de la personne qui a demandé le MCF).
- Reste inexpliqué : `99988776,CLIENT TEST,,,` (5 champs) a donné `R` le 14 ; le champ 9 de C0 (`…,x,x`) accepté.
