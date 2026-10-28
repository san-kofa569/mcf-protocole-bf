# Essais sur le MCF du 2026-10-12

Plan suivi : docs/plan_essais_2026-10-12.md. Une commande à la fois, lancée par l'opérateur. Heures du PC (UTC+2) ;
l'horloge du MCF est en UTC et retarde d'environ 1 min. Trames complètes dans appareil/brut/ (hors dépôt).
NIM et IFU jamais recopiés ici.

## Déroulé

| Heure | Seq | Commande | Données | Réponse |
|---|---|---|---|---|
| 13:30 | 30 | C1 | — | 31 champs, identiques au 09 sauf l'horloge ; compteurs 2,0,0 ; statut 6x80 |
| 13:37 | 31 | 31 | `ARTICLE TEST⇥B18.0%100⇥100*1` (h1) | `E:La commande C0 doit être soumise en premier` |
| 13:40 | 38 | C3 | `,CLIENT COMPTANT,CC,,` | `E:Erreur de type de destinataire` |
| 13:40 | 39 | C3 | `,CLIENT COMPTANT,,CC,` | `E:Erreur de type de destinataire` |
| 13:45 | 3A | C0 | `1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0002` | ACCEPTÉ : `1,3,,,,,,` (8 champs, recomptés sur trame brute) |
| 13:55 | 3B | 31 | h1 (ci-dessus) | `E:Erreur de format des données ou incompatibilité` |
| 13:58 | 3C | 31 | `ARTICLE TEST␊ART001⇥B18.0%100⇥100*1` (h2) | même refus de format |
| 13:59 | 3D | 31 | `ARTICLE TEST⇥A0.0%100⇥100*1` (h3) | même refus de format |
| 14:00 | 3E | 31 | `ARTICLE TEST␊LOCBIE⇥B18.0%100⇥100*1` (h4) | même refus de format |
| 14:12 | 3F | C3 | `,CLIENT COMPTANT,1,,` (facture 2 ouverte) | `15` (NAK) puis trame valide SANS données, statut `a2 80 80 80 80 80` |
| 14:25 | 40 | 38 | — (facture 2 sans article) | `E:Aucune donnée valide n'a été reçue` |
| 14:26 | — | arrêt et rallumage du MCF | — | sortie USB 14:26:19, retour 14:26:40 |
| 14:28 | 41 | C1 | — | compteurs 2,0,0 inchangés, statut 6x80 |
| 14:28 | 42 | C3 | `,CLIENT COMPTANT,1,,` (aucune facture ouverte) | `E:Erreur de type de destinataire` |

## Faits établis

1. Une facture ouverte sans article ne survit pas au-delà de la séance (facture 1 du 09 disparue le 12 ; cause :
   arrêt de l'appareil ou délai, non tranché). Elle n'est ni comptée ni déclarée : compteurs 2,0,0 inchangés.
2. 38 ne ferme pas une facture sans article (« Aucune donnée valide »), le 09 comme le 12. Pas de commande
   d'annulation connue.
3. Réponse de C0 au Burkina : 8 champs (`1,3` puis 6 vides). ECOHADA (mode Niger) en exige exactement 7, et C1 en
   compte 31 (Niger : 29). ECOHADA ne piloterait pas cet appareil tel quel : le Burkina n'est pas le Niger à l'octet.
4. 31 : six formes de la famille `nom⇥<groupe>…⇥prix*qté` refusées pour « format » (essais 3, 4, 5 du 09 ; h1 à h4
   du 12). Ni le groupe (A ou B), ni la valeur après `%`, ni une 2e ligne (code ou type) n'y changent rien.
   C'est la structure de la ligne qui diffère.
5. C3 : `CC` (3e ou 4e champ), `1` (3e champ) et vide sont refusés pour « type de destinataire ».
6. C3 pendant une facture ouverte : NAK (`15`) puis trame sans données, octet de statut 0 = `a2`. Lecture Datecs
   (hypothèse) : bit 5 erreur générale, bit 1 code de commande invalide. Première fois que le statut n'est pas 6x80.
   `trame.py` ne savait pas lire une réponse précédée d'un NAK : corrigé (fonction `paquet`, tests).
7. Un refus de 31, de C3 ou de 38 ne fait pas quitter l'USB (contrairement au refus de C0 du 09).

## Spécifications burkinabè relues (officiel/, scans)

- Note 2025-0889 (SFE), annexe : chaque tableau de paramétrage est numéroté (types de client #1 CC, #2 PM, #3 PP,
  #4 PC ; types d'article #1 LOCBIE … #4 IMPSERV ; nature d'avoir #1 COR … #4 RRR). Le numéro `1` n'a pas suffi en C3.
- Spécification MCF §2.5.1 : 16 groupes (PARAM_TA…TP) et 4 taux PSVB (PARAM_PSVBA…D) : les 4 derniers champs de C1
  (2.0, 1.0, 0.2, 0.0) sont les taux PSVB. §2.10.2 d : rejet si un article a un montant ≤ 0.
- Types de facture : FV, FT, FA, EV, ET, EA (C0 champ 4).
- Aucune de ces deux notes ne décrit le protocole : « défini par l'Administration » (§2.1.8).

## Recherche documentaire du jour

Protocole du Niger introuvable en archive (docplayer injoignable, absent de web.archive.org) ; circulaires 74 et 75
du Niger = lettres d'envoi d'une page (docs/EXTERNE.md). Page ECOHADA Burkina : rien sur le protocole.

## Suite

Les essais à l'aveugle s'arrêtent ici : chaque nouvelle forme de 31 ou de C3 serait une devinette. Demande de
documentation au fournisseur mise à jour (hors dépôt).

## 16:20 : sondes sans réponse

Les 8 trames des sondes (C3 s1 à s4, C0 facture 3, 31 s3, s1, s2 ; seq 50 à 57) n'ont reçu **aucun octet**.
Juste avant, l'écran du MCF était dans les paramètres Android (« About device »). Hypothèse : l'application
fiscale ne sert le port série que lorsqu'elle est au premier plan. Aucune conclusion sur les formats : ces sondes
sont à refaire, après un C1 de contrôle, l'application fiscale à l'écran.

Relevé de l'écran « About device » (identifiants de l'appareil non recopiés) : Android 10 (et non 7.1 comme
le manuel éthiopien) ; noyau 4.9.218-perf du 2026-07-06 ; **firmware V1.1.58_BF_20260717** (version propre au
Burkina) ; custom build FIS-NANO_V1.0.0 ; Security OS 20251119-0 ; bande de base SC200R (module Quectel
bâti sur la puce QCM2150) ; SIM Orange BF. Menu Paramètres de Datamega : Système, Matériel, Sécurité,
Transfert et sauvegarde.

## 16:43 à 17:54 : sondes, application à l'écran

- 16:43 C1 : réponse normale dès que l'application fiscale (EazSell) est au premier plan. **Le MCF ne sert le port
  que si son application est à l'écran** ; « Connexion PC » passe alors à « Connecté » sur le tableau de bord.
- C3 refusé « type de destinataire » pour toutes ces formes (aucune facture ouverte) :
  - saturations à 5 champs : `CC`, `1`, `PP`, `PM`, `PC`, `2`, `0` ; à 8 champs : `CC` ; à 12 champs : `PP`, `PM`, `PC`, `2`, `3` ;
  - valeur seule : `CC`, `PP`, `PM`, `PC`, `1`, `2`, `3`, `4` ;
  - tabulations : `PP`, `PM`, `1` ;
  - forme naturelle : `{IFU},CLIENT TEST,PM,,`, `,CLIENT TEST,PP,,`, `{IFU},CLIENT TEST,PC,,`.
  Aucun code ni numéro des tableaux officiels n'est reconnu, à aucune place, avec aucun séparateur essayé.
- C0 factures 3 et 4 acceptées (`1,3,,,,,,`). 31 refusé « format » pour 9 formes de plus : nom seul, virgules,
  décimales, type `LOCBIE` en fin, type + unité en fin, type avant la taxe, trois lignes, type `1` en fin,
  tout en virgules. Total : 16 formes d'article refusées avec le même message.
- Hypothèse : 31 est refusé parce que la facture est ouverte sans client (le message dit « ou incompatibilité ») ;
  C3 serait alors le vrai verrou. Non prouvée.

## Écrans de l'appareil (lecture seule)

- L'application fiscale s'appelle **EazSell** (Datamega). Au Burkina elle tourne en **MCF pur** : tableau de bord
  (état, connexion PC, audit à distance, factures, Z et C-rapports), rapports, transactions, paramètres ; ni écran
  de vente, ni fiche article, ni fiche client. Aucun réglage de protocole (Matériel : densité d'impression seule ;
  aucun module complémentaire). Export de la base des ventes vers un dossier `EAZSell` (0 reçu).
- Rapports imprimés à 15:36-15:37 (heure MCF) : A-rapports, X-quotidien, **Z-rapport** « Pas de vente ». C1 inchangé
  après le Z (`2,0,0`) : les compteurs de C1 ne comptent pas les rapports.

## Suite décidée

Accord de l'opérateur (2026-10-12) : une recherche systématique bornée du type de destinataire de C3, par script —
une liste de candidats, chaque candidat à toutes les places en une trame, une trame toutes les 3 s, 80 au plus,
arrêt au premier message nouveau, au premier NAK, silence ou déconnexion ; répétée d'abord sur le jumeau.

## 18:40 à 19:30 : recherche bornée de C3 (appareil/recherche_bornee.py)

Séances 1 à 4 (trames 1 à 237 et 241 à 320 ; 238 à 240 non envoyées, séance 3 interrompue) : **317 formes de C3,
toutes refusées « Erreur de type de destinataire »**. Candidats : 5 à 9, 01 à 04, A à F, N, O, T, P, M, FV, FT, FA,
EV, ET, EA, TS, TA, TN, TI, TM, TP, chacun seul à chacune des 5 places, avec et sans nom. Ni NAK ni silence ni
déconnexion. Séance 5 (IFU, NIM, CLIENT, COMPTANT, DESTINATAIRE) non jouée. Captures : appareil/brut/c3_seance1..4.

Conclusion : avec les sondes du jour, plus de 360 formes, à 1, 5, 8 ou 12 champs, virgule ou tabulation, un seul
et même message. Le contrôle ne lit pas ce que nous faisons varier. L'énumération de C3 s'arrête.

## Formes de 31 de l'ECOHADA béninois (fcn.004087e0, lecture statique)

`nom[⏎code]⇥<groupe><prix>*<qté>[;<taxe spécifique>][⇥<prix d'origine>,<motif>]`, sans `%`. La forme simple a déjà
été refusée le 09 (essai 3) : les deux familles ECOHADA (BJ et NE) sont refusées. Le message de 31 est le même que
celui du C0 béninois du 09 (« format des données ou incompatibilité ») : on teste désormais l'**incompatibilité**
avec la facture ouverte, en faisant varier C0 (seul message dont on sait qu'il dépend du contenu).
Charges utiles : appareil/essais/compat/.

## 19:02 à 19:13 : C0 varié, puis 31

| Heure | Seq | Commande | Données | Réponse |
|---|---|---|---|---|
| 19:02 | 76 | C0 | `1,Essai,{IFU},FV,HT,ISF-ESSAI,ESSAI-0007` (mode HT) | ACCEPTÉ `1,3,,,,,,` |
| 19:02 | 77, 78 | 31 | h1 (NE) puis essai 3 (BJ) | format ou incompatibilité |
| 19:11 | 72 à 74 | 31 | h1, essai 3, vide (aucune facture : MCF_IFU absent, C0 non envoyé) | « La commande C0 doit être soumise en premier » |
| ~19:13 | 7A | C0 | `…,ESSAI-0006,A` (8 champs) | accepté (déduit : 31 passe ensuite au contrôle de format) |
| 19:13 | 7B, 7C | 31 | h1, essai 3 | format ou incompatibilité |
| 19:13 | 7D | 31 | **vide** | **`E:Aucune donnée valide n'a été reçue`** |

Faits : HT ou TTC ne change rien à 31. C0 accepte un 8e champ (lu ou ignoré : non tranché). **31 vide reçoit un autre
message que 31 non vide** : l'appareil lit le contenu de 31, l'état seul n'explique pas le refus. `trame.py` refuse
désormais un MCF_IFU qui n'a pas 9 caractères alphanumériques (un « … » collé a failli partir).

## 19:14 : 31 à un seul caractère (facture ouverte)

| Données de 31 | Réponse |
|---|---|
| `⇥` (09), espace (20), `⏎` (0A) | `E:Aucune donnée valide n'a été reçue` |
| `,` `;` `*` `%` `X` `0` | `E:Erreur de format des données ou incompatibilité` |

Lecture : les trois caractères « vides » sont exactement ceux qu'enlève un `trim()` (Java/Kotlin : tout caractère
≤ 0x20). Le premier contrôle de 31 est donc « données vides après trim » ; il ne prouve pas que la tabulation soit
un séparateur. Tout le reste tombe dans le même refus, qui ressemble à une exception attrapée en bloc (nombre
illisible, champ manquant). Suite : sondes de structure (JSON, longueur) sur 31 et C3.

## 19:17 : sondes de structure

| Heure | Seq | Commande | Données | Réponse |
|---|---|---|---|---|
| 19:17 | 8A | C0 | `…,ESSAI-0009` | ACCEPTÉ `1,3,,,,,,` |
| 19:17 | 8B à 8E | 31 | `{}`, `[]`, article en JSON, 150 × `A` | format ou incompatibilité (les 4) |
| 19:17 | 8F à 92 | C3 | `{}`, `[]`, `{"type":"CC"}`, `type=CC` | NAK + statut `a2` : facture 9 encore ouverte, **essais nuls** |

31 n'attend pas du JSON ; pas de contrôle de longueur à 150 caractères. Les C3 sont à refaire sans facture ouverte
(arrêt et rallumage, puis C1 de contrôle). Recherche web des messages d'erreur exacts : aucune occurrence publique.

## Bilan du soir

- C3 : ~360 formes, message unique ; énumération arrêtée. Sondes de structure à refaire hors facture.
- 31 : trois messages distincts seulement — « C0 en premier » (aucune facture), « aucune donnée » (vide après trim),
  « format ou incompatibilité » (tout le reste, y compris les deux formats ECOHADA, HT ou TTC, C0 à 8 champs).
- Outils : `trame.py` vérifie MCF_IFU (9 caractères) ; `recherche_bornee.py` imprime la séance suivante avec `--port`.
