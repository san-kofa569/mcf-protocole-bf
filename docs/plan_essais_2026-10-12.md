# Plan d'essais sur le MCF — lundi 2026-10-12

Une commande à la fois, lancée par l'opérateur. Lire chaque réponse avant la suivante. Captures brutes dans
`appareil/brut/` (hors dépôt). Charges utiles dans `appareil/essais/2026-10-12/`, produites par
`appareil/formats.py` (reproduction testée de la construction d'ECOHADA MCF CLI, lue dans le binaire).

## Ce qui fonde les hypothèses

| Fait | Source | Force |
|---|---|---|
| C0 au format Niger accepté (`1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0001`) | appareil, 2026-10-09 | prouvé |
| `formats.c0()` redonne ce C0 à l'octet près | test `test_c0_identique_a_celui_accepte_le_2026_10_09` | témoin |
| 31 Niger = `nom[\ncode]\t<groupe><taux de C1>%<montant>\t<prix>*<qté>` | binaire ECOHADA, fcn.004096b0 | lu |
| `montant` = round(prix × qté + taxe spécifique) : le TOTAL de la ligne | binaire, fcn.00411ea0 0x4127cb-0x4128d1 | lu |
| L'essai 5 refusé envoyait `%0` au lieu de `%100` | appareil/essais/a31_essai5.txt | écart expliqué |
| C1 burkinabè = 31 champs ; ECOHADA n'accepte que 10 (Bénin) ou 29 (Niger) | binaire, fcn.0040fcc0 | lu |
| C3 = `IFU,nom,c3,c4,c5` ; refus « type de destinataire » quand c3 est vide | binaire fcn.0040f5f0 + appareil | lu + prouvé |
| Types de client du Burkina : CC, PM, PP, PC (CC sans champ obligatoire) | annexe note 2025-0889 (tableaux de paramétrage) | officiel |
| Article burkinabè : code, type LOCBIE/LOCSER/IMPBIE/IMPSERV (§2.19) | annexe note 2025-0889 | officiel |
| 33 sans données, réponse ≥ 9 champs, champ 0 = total | binaire fcn.00415a10 | lu |
| 35 = mode (V C M D E A) collé au montant ; succès si la réponse commence par `R` | binaire fcn.0040aa70 | lu |
| 38 sans données ; 7 champs = validée (compteurs, type, date, NIM, IFU, signature), 6 = annulée | binaire fcn.0040bee0 | lu |
| ECOHADA émet en exécution C3, C0, 31, 36, 33, 35, 38 ; `formats.py` les redonne à l'octet près | `simulateur.matrice`, faux MCF, 2026-10-10 | témoin |
| Réponses attendues par ECOHADA (Niger) : C3 = 1 champ, C0 = **7 exactement**, 31 = **5 exactement**, 33 ≥ 9, 38 = 7 | binaire (`sete` / `jl`) | lu |
| Réponse C0 de l'appareil le 2026-10-09 : `1,3,,,,,,` = 8 champs, transcrite, sans trame brute | note du 2026-10-09 | à recompter |
| Article à taxe spécifique : suffixe `;T<a>,<b>` après la quantité ; accents envoyés en Latin-1 (`É` = `C9`) | exécution 2026-10-10 | témoin |

## Ordre des essais (arbre de décision)

Chaque étape répond à une seule question ; l'ordre va de l'hypothèse la plus probable à la moins
probable. Au pire : 13 commandes.

0. Une fois, en début de séance : `export MCF_IFU=<IFU de l'appareil>`
1. État : `python3 appareil/trame.py /dev/ttyACM0 30 C1`
   Noter les compteurs (champs 4 à 6). La facture n°1 (ouverte le 2026-10-09) est peut-être encore ouverte.
2. Article, hypothèse 1 (format ECOHADA exact) :
   `python3 appareil/trame.py /dev/ttyACM0 31 31 "$(cat appareil/essais/2026-10-12/a31_h1_ecohada.txt)"`
   - accepté (pas de `E:`) → étape 6 ;
   - `E:` qui parle de facture absente ou fermée → la facture n°1 n'existe plus → étape 9 ;
   - `E:` de format → étape 3.
   Si accepté : compter les champs de la réponse (ECOHADA Niger en exige 5) et garder la trame brute.
3. Hypothèse 2 (code article, exigé au Burkina §2.19) :
   `python3 appareil/trame.py /dev/ttyACM0 32 31 "$(cat appareil/essais/2026-10-12/a31_h2_avec_code.txt)"`
   accepté → étape 6 ; refusé → étape 4.
4. Hypothèse 3 (groupe A, taux 0 : isole le groupe B) :
   `python3 appareil/trame.py /dev/ttyACM0 33 31 "$(cat appareil/essais/2026-10-12/a31_h3_groupe_a.txt)"`
   accepté → le groupe B pose problème, noter le message ; refusé → étape 5.
5. Hypothèse 4 (type d'article à la place du code) :
   `python3 appareil/trame.py /dev/ttyACM0 34 31 "$(cat appareil/essais/2026-10-12/a31_h4_type_article.txt)"`
   refusé → arrêter les articles, annuler (étape 8) et revenir avec les messages.
6. Sous-total : `python3 appareil/trame.py /dev/ttyACM0 35 33`
   Attendu : ≥ 9 champs, champ 0 = 100.
7. Paiement, si le total vaut bien 100 (sinon remplacer 100 par le champ 0 lu à l'étape 6) :
   `python3 appareil/trame.py /dev/ttyACM0 36 35 "$(cat appareil/essais/2026-10-12/p35_especes_100.txt)"`
   Attendu : réponse qui commence par `R`.
8. Clôture : `python3 appareil/trame.py /dev/ttyACM0 37 38`
   7 champs = facture VALIDÉE, signée (environnement développeur DGI) ; 6 champs = annulée (sans 35).
9. Client, hypothèse 1 (client comptant) — C3 se place AVANT C0 :
   `python3 appareil/trame.py /dev/ttyACM0 38 C3 "$(cat appareil/essais/2026-10-12/c3_h1_comptant.txt)"`
   accepté (1 champ) → étape 10 ; « type de destinataire » → hypothèse 2 :
   `python3 appareil/trame.py /dev/ttyACM0 39 C3 "$(cat appareil/essais/2026-10-12/c3_h2_type_en_4e.txt)"`
10. Ouverture de la facture n°2 :
    `python3 appareil/trame.py /dev/ttyACM0 3A C0 "$(cat appareil/essais/2026-10-12/c0_facture_2.txt)"`
    Garder la trame brute de la réponse et compter ses champs (ECOHADA Niger en exige 7 ; le 09 : 8 transcrits).
    puis l'article retenu, 33, 35 et 38 comme aux étapes 2 à 8.

## Ce qui reste inconnu après ces essais

- Le sens des champs 4 et 5 de C3 (adresse, contact ?), et les champs obligatoires par type de client.
- Les deux champs de C1 en plus du format Niger.
- La place du type d'article burkinabè, si l'hypothèse 1 passe sans lui (alors il n'est pas transmis au MCF).
