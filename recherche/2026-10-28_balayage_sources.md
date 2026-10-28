# Balayage des sources du 2026-10-28

But : reprendre toutes les sources consultées depuis le 8 octobre et chercher ce qui a paru depuis le 16. Aucune trame
envoyée. Certitude : ✅ prouvé sur l'appareil · 📖 code tiers · 📜 texte officiel · 🔍 hypothèse · ❓ inconnu.

## 1. Résultat net

**Le protocole de l'appareil est celui de la RDC** (« Spécifications techniques des dispositifs électroniques fiscaux —
PROTOCOLE MCF-SFE v1.0 », DGI RDC), pas celui du Bénin ni du Niger. Un code public, ajouté le 2026-10-17, le met en
œuvre en entier, dont **31, 33, 35, 38 et l'annulation**. Tout ce que l'appareil a montré depuis le 9 octobre s'y retrouve
champ pour champ (§3). La forme de 31 qu'il donne **n'a jamais été essayée** (§4).

## 2. La source nouvelle

- Dépôt `bbagabo/dgi_compliance` (application ERPNext/Frappe pour la facture normalisée de la RDC), version 4.0.0
  du 2026-10-17 (commit `0c6065d`, « mode MCF physique (USB) + agent local ») ; dernier commit lu `3f68187` (2026-10-20).
  https://github.com/bbagabo/dgi_compliance
- `mcf_agent/mcf_agent.py` : pont USB série (115200 8N1) entre le MCF et l'ERP. Il cite le PDF de la DGI RDC par ses
  sections (3.2 BCC, 4.2 caractères spéciaux, 4.3 flux, ch. 5 QR, annexe des statuts) et « le prototype E-MCF fourni ».
- 📖 Certitude : code tiers écrit d'après le PDF officiel, **jamais prouvé sur un appareil** (12 tests sur un MCF simulé
  par le même auteur). L'auteur signale une ambiguïté du PDF : l'ordre FN/SIG de la réponse 38 (table et exemple diffèrent).
- Le PDF de la DGI RDC n'a pas été trouvé en ligne : le portail `developper.dgirdc.cd` (plate-forme `sygdef`) demande un
  compte, comme le portail burkinabè.

Copie de lecture dans `externe/docs/rdc_dgi_compliance/` (hors dépôt) :

| Fichier (chemin d'origine) | sha256 |
|---|---|
| `mcf_agent.py` (`mcf_agent/mcf_agent.py`) | `2c70ea30941ca4ef314ce68537013452a3573d84b4f9811490ace5dfe6c629cf` |
| `test_mcf_agent.py` (`mcf_agent/test_mcf_agent.py`) | `7d11d228ceb5dc47383076f651f76394b45485db298098b787c80605a2a69f2b` |
| `README_AGENT.md` (`mcf_agent/README_AGENT.md`) | `f191bf52a5a550f00960dbf63be1ebb3e1ff25347e267bef836698f68537e806` |
| `payload.py` (`dgi_compliance/mcf/payload.py`) | `d1f80726119683e875a3e4b04f61f22fda4c835823a23cd040c37f669ed36424` |
| `mapper.py` (`dgi_compliance/edef/mapper.py`) | `273404d14438f3237b3d8d3081833329d8345b5585fb73545debcbfc7719d780` |
| `WHATS_NEW_4.0.0.md` | `903b257f848bbdec2bdba549f5e39d8dfee8a4b068144e5c19642e57309e3629` |

## 3. Concordance avec l'appareil

| Point | RDC v1.0 (📖) | Burkina (✅ observé) |
|---|---|---|
| Trame, BCC, NAK, SYN | `01 LEN SEQ CMD DATA 05 BCC 03`, BCC 16 bits en 4 quartets + 30h, données ≤ 200 octets | identique |
| Statut, octet 0 | bit 0 erreur syntaxique, bit 1 commande non valide, bit 2 date non réglée | `a1` sur 2B `I5`, `a2` sur C3 pendant une facture ouverte : les deux bits |
| Statut, autres | octet 1 : bit 1 commande interdite dans le mode, bit 4 rapport quotidien requis ; octet 2 bit 3 : **facture ouverte** ; octet 4 : mémoire | jamais lus (🔍 lire l'octet 2 d'un C1 facture ouverte, si C1 ne l'annule pas d'abord) |
| C1 | `MID,NIF,DT,TC,FVC,FRC,DFDT,DFT,DFS,DFN,DMV` puis 16 taux A–P (champs 11 à 26) | 31 champs : les 11 mêmes (les **5 vides** = date, type, signature, numéro, montant de la dernière facture : aucune facture encore), 16 taux aux champs 11 à 26, puis 4 taux PSVB (propres au Burkina) |
| C2 | `EC,DC,DT,STA,ER` | 3 champs : les 3 premiers |
| C3 | `type,NIF,nom,adresse,tél,e-mail,RCCM` ; types `PP PM PC PL AO` ; réponse `R` | 7 champs, tél. 5e, e-mail 6e, `R` : **la sémantique est résolue** (champ 1 = type, 2 = IFU du client, 3 = nom, 4 = adresse, 7 = RCCM) |
| C0 | `op,nom_op,NIF,type,mode,ISF,FN` ; avoir : `type,nature,référence` à la place de `type` (nature `COR RAN RAM RRR`, référence = SIG d'origine) ; USD : `,taux,date` en fin | 7 champs identiques ; `FA`/`EA` refusés à 7 champs : il leur manque nature et référence |
| Réponse de C0 | 8 champs (`24,50,,,,,,` dans les tests) | `1,3,,,,,,` |
| 31 | `nom[⏎code]⇥TYPE,G{taux}%{montant}⇥{prix}[*qté][⇥{prix_orig},{motif}]` | ❓ toujours refusé — **forme jamais essayée** |
| 36 | `lettre,texte`, lettres A–H | `A,ESSAI` → `R` ; `Z,ESSAI` refusé |
| 33 | sans donnée ; réponse : total, 16 montants A–P, 16 taxes A–P, taxe spécifique, devise | sans article : `E:Veuillez ajouter le produit en premier` |
| 35 | `{lettre}{montant}` (E espèces, V virement, C carte, M mobile, D chèque, A autre) ou vide = espèces pour le total ; réponse `R{reste}` | vide sur facture à 0 : `E:Le montant payé est suffisant` (cohérent : rien à payer) |
| 38 | **`{total},{taxe}`** (montants à 2 décimales) ; réponse `R…`, `P:` = renvoyer, `E:` ; 8 champs `FC,TC,FT,DT,MID,NIF,FN,SIG` | vide : `E:Aucune donnée valide n'a été reçue` (cohérent : 38 attend des données) |
| Annulation | **`38` avec `C`** → `E:ANNULEE` | inconnue ; C1, C2 ou un rallumage annulent |
| Échappements | `&` `^amp;`, CR `^xa;`, LF `^xd;`, `,` `^x2c;`, `<` `^lt;`, `>` `^gt;` | jamais testés |
| QR | `RDCDEF01;MID;SIG;NIF;DT` | ❓ |

## 4. La forme de 31 qui n'a pas été essayée

Exemples des tests RDC (TTC) : `EAU⇥BIE,A0.00%3600.00⇥720.00*5` et `LAIT^x2c; GR⇥BIE,B16.00%464.00⇥464.00`.
Lecture : désignation, tabulation, **type d'article puis virgule**, lettre du groupe collée au taux (2 décimales), `%`,
montant de la ligne (prix × quantité), tabulation, prix unitaire, `*quantité` seulement si elle n'est pas 1.
Réponse d'un article accepté dans les tests : `3600.00,3600.00,0.00,0.00`.

Les 500 formes déjà refusées ont toutes manqué ce point : le type d'article n'a jamais été mis **après une tabulation
et devant une virgule** collée au groupe. Le plus proche, `ARTICLE TEST⇥LOCBIE⇥B18.0%100⇥100*1` (12 octobre), a une
tabulation après le type ; la grille « gabarits » met le même délimiteur des deux côtés du type.

Au Burkina, les types d'article sont `LOCBIE`, `LOCSER`, `IMPBIE`, `IMPSERV` (📜 note 2025-0889, annexe, relevée le
12 octobre) ; la RDC écrit `BIE`, `SER`. Même annexe : types de client `CC PM PP PC` (RDC : `PP PM PC PL AO`), nature
d'avoir `COR` … `RRR` (RDC : `COR RAN RAM RRR`). Taux du groupe B lu par C1 : 18.0.

## 5. Sources reprises sans rien de nouveau

- dgi.bf, page « NOTE FEC » : mêmes quatre PDF du 16 janvier 2026 (`officiel/`). Actualités jusqu'au 20/10 : rien sur
  le MCF ni le protocole.
- dgi.bf, « Guide pratique FEC » (`wp-content/uploads/2026/01/GUIDE-FEC.pdf`, dépliant de 6 p., en courbes, sans
  texte) : grand public, rien de technique. Copie `externe/docs/bf_dgi_guide_fec.pdf`,
  sha256 `1e8d8221034e872dba86bc2ee852205da8b2e1dc87958b903a38c9dc8fe191a4`.
- dgi.bf, « liste des logiciels homologués » (`/verification/verification-logiciels-homologues`) : nouvelle page,
  table chargée par script (colonnes IFU, raison sociale, logiciel, **ISF**, date, attestation). Non lue : à ouvrir dans
  un navigateur. Elle donnerait la forme d'un ISF attribué (jamais à recopier ni à réutiliser).
- dgi.bf/ventesecef : formulaire de demande seulement.
- Communiqué d'un premier éditeur homologué (presse, 5 octobre) : déjà connu, rien de technique.
- ECOHADA, pages développeurs BF et RDC : mêmes versions (CLI et Server 23.04081, SDK 23.0827). La page cite désormais
  une variante RDC (« DEF, e-DEF »), absente des binaires lus le 16.
- DataMega : help.datamega.tech n'a toujours que le manuel Éthiopie (liste d'erreurs du ch. 7 : rien sur l'article) ;
  bf.eazsell.net inchangé, sans téléchargement ; « PC MANAGER » introuvable en ligne.
- GitHub (recherche de code, désormais possible) : les messages d'erreur de l'appareil n'apparaissent nulle part ;
  `lara-sygmef` et `normalisation-SYGMEF` (Bénin) et `marlon01/marlon` (`norma_facture`, RDC) ne font que l'e-MCF en
  HTTP ; le dépôt `Rachid-Ouattara/certia`, cité par un moteur pour un SFE burkinabè, répond 404.
- Documents du Niger (docplayer, guide des éditeurs) et du Bénin (`MECeF_MCF_SFE_Protocole_v2.pdf`) : toujours
  introuvables.

## 6. Conséquences

- La demande au fournisseur reste utile pour le texte officiel burkinabè, mais ses questions sur C3, 33, 35, 38 et
  l'annulation ont maintenant une réponse probable. La lettre est à reprendre avant envoi.
- La spécification à demander a probablement un équivalent burkinabè du titre RDC : « protocole MCF-SFE ».
- `docs/REFERENCE_PROTOCOLE.md` (C3 : rôles des champs 1 à 4 et 7) est à corriger, en 📖, sans attendre l'appareil.

## 7. Essais sur l'appareil (2026-10-28, rallumé ; une trame à la fois, lancées par l'opérateur)

Captures : `appareil/brut/2026-10-28_seance.txt` (hors dépôt).

| Heure | seq | Trame | Réponse |
|---|---|---|---|
| 11:56 | 7A | C3 `PP,CLIENT TEST,,,70123456,client@example.com,` | `R` |
| 11:56 | 7B | C0 | non envoyé (`MCF_IFU` absent : garde-fou) |
| 11:56 | 7C | 31 `rdc/LOCBIE` sans facture | `E:La commande C0 doit être soumise en premier` |
| 11:58 | 7D | C3 (même client) | `R` |
| 11:58 | 7E | C0 `ESSAI-0007` | `1,3,CLIENT TEST,,,70123456,client@example.com,` (facture ouverte) |
| 11:58 | 7F | 31 `ARTICLE TEST⇥LOCBIE,B18.00%100.00⇥100.00` | **`E:La taxe est incorrecte!`** |
| 11:58 | 8E | 38 `C` | **`E:La commande 35 doit être soumise en premier.`** |

- ✅ **La structure RDC de 31 est lue** : premier message de valeur après plus de 500 formes refusées au format.
  Reste à trouver la valeur de taxe attendue (grille `taxe`, 22 trames : écriture du taux, groupe, sens des champs,
  taxe spécifique, type à taxe égale).
- ✅ 38 contrôle l'ordre avant ses données : 35 doit précéder. `C` (annulation RDC) n'est ni confirmé ni infirmé.
- Jumeau mis à jour (31 forme RDC → taxe incorrecte ; 38 avec données → 35 en premier) ; 181 tests.

## 8. Suite de la séance : jusqu'à la facture certifiée (12:04–12:31)

| Heure | seq | Trames | Réponse |
|---|---|---|---|
| 12:04 | 8F–99 | grille `taxe` 1–11, ESSAI-0007 (C0 sans PSVB) | `taxe incorrecte` ×10 ; `LOCBIE,B100.00` (sans `%`) : format |
| 12:07 | 9A–9D | `taxe` 13–16 | `taxe incorrecte` ×3 ; prix `100.00;0.00` : format |
| 12:08 | 9E | `taxe` 17 : `BIE,…` | `E:Le type de produit n'existe pas` |
| 12:10 | 9F–AF | grille `taxe2` (17) : `G%taux`, taxe nulle, `TA`/`TB`, ordre inverse | `taxe incorrecte` ×17 |
| 12:14 | B0–B2 | `LOCSER`, `IMPBIE`, `IMPSERV` | ×2, puis `type de produit n'existe pas` (IMPSERV) |
| 12:18 | B3–CA | grille `groupes_rdc` (24) : D, E, G–P | `taxe incorrecte` ×24 |
| 12:21 | CB–D7 | grille `quantite` (13) : `*qté` explicite, taxes arrondies | `taxe incorrecte` ×13 |
| 12:24 | D8–E3 | grille `psvb_rdc` (12) : PSVB après `%`, `;T0,0`, sous-champ | `taxe incorrecte` ×12 |
| 12:26 | E4 | C1 | annule ESSAI-0007 ; compteurs `2,0,0` |
| 12:26 | E5, E6 | C3 ; C0 `…,ESSAI-0008,A` (**PSVB A en 8e champ**) | `R` ; `1,3,CLIENT TEST,…` |
| 12:26 | E7 | 31 `ARTICLE TEST⇥LOCBIE,B18.0%100.00⇥100.00*1` | **`100.0,84.75,15.25,0.0`** |
| 12:27 | E8 | 33 | `102.0,0.0,100.0,…,15.25,…,2.0,0.0` (35 champs) |
| 12:28 | E9 | 35 `E102.00` | `R0` |
| 12:29 | EA | 38 `102.00,15.25` | `E:MV n'est pas un nombre valide.` |
| 12:30 | EB–EE | 38 `102.0,15.25`, `102,15.25`, `102.00,15.25,2.00`, `102,15,2` | idem |
| 12:31 | EF | 38 `102.00` | **accepté : 8 champs** (compteurs `1`, `3`, `FV`, date, NIM, IFU, signature de 24 caractères, FN) |

- ✅ **Première facture certifiée** (ESSAI-0008, environnement de test de la DGI, décision de l'opérateur). ISF d'essai, non
  attribué : à surveiller par C2 (envoyés/total) et sur le serveur.
- ✅ Le verrou de la 31 était le **PSVB du C0** : « La taxe est incorrecte! » vise la taxe de la facture, pas l'écriture de la
  ligne (la même trame, refusée à 12:21 dans ESSAI-0007, passe à 12:26 dans ESSAI-0008).
- ✅ 38 burkinabè = `MV` seul (RDC : `MV,MT`).
- ✅ C2 à 12:53 : `3,3,…` (3 documents envoyés sur 3, dernier contact 11:41 UTC) : la facture est transmise.
- Détail des formats : `docs/REFERENCE_PROTOCOLE.md` §4–5.

## 9. Deuxième séance : deux lignes, deux modes (14:44–14:45), client `appareil/cycle.py`

| Heure | Trame | Réponse |
|---|---|---|
| 14:44:38 | C3 | `R` |
| 14:44:41 | C0 `…,ESSAI-0009,A` | `2,4,CLIENT TEST,…` (compteurs avancés) |
| 14:44:45 | 31 bien `LOCBIE,B18.0%100.00⇥100.00*1` | `100.0,84.75,15.25,0.0` |
| 14:44:48 | 31 service `LOCSER,C10.0%110.00⇥110.00*1` | `110.0,100.0,10.0,0.0` |
| 14:44:51 | 33 | total `214.2` ; B 100, C 110 ; TVA 15.25 et 10.0 ; **PSVB 4.2** (2 % de 210 : services compris) |
| 14:44:54 | 35 `M100.00` | **`R-114.2`** (reste dû en négatif ; mode M accepté) |
| 14:44:57 | 35 `E-114.20` | `R-228.4` — **erreur du client** : il a recopié le reste avec son signe |
| 14:45:01 | 38 `214.20` | accepté, compteurs `2/4 FV` : **facture certifiée non soldée** |
| 14:45:06 | C3 (scénario annulation) | NAK : arrêt avant toute autre trame |
| 14:45:15 | C1 | compteurs `4,2,0`, statut normal : aucune facture ouverte |

- ✅ L'appareil ne contrôle ni le signe d'un paiement ni le solde avant le 38. ESSAI-0009 porte donc des paiements
  incohérents (M 100.00, E -114.20) sur l'environnement de test : à corriger par un avoir quand sa forme sera connue.
- Client corrigé : `R-x` = x dû ; aucun paiement nul ou négatif ; 38 seulement après `R0`. Jumeau mis à jour (PSVB sur
  toutes les lignes, mode M, reste négatif, 38 sans contrôle du solde).
- 🔍 NAK au C3 5 s après un 38 : appareil occupé après la clôture ; la sonde d'annulation est à relancer après une pause.

## 10. Annulation (14:56)

| Heure | Trame | Réponse |
|---|---|---|
| 14:56:00 | C3, puis C0 `…,ESSAI-0010,A` | `R` ; `3,5,CLIENT TEST,…` |
| 14:56:06 | 31 bien B, 33, 35 `E102.00` | `100.0,84.75,15.25,0.0` ; total `102.0` ; `R0` |
| 14:56:16 | **38 `C`** | **`E:ANNULEE`** |
| 14:57:15 | C1 | compteurs `4,2,0` inchangés, statut normal |

- ✅ Annulation d'une facture payée : `38 C`, non comptée. Le NAK de 14:45 venait bien du moment (5 s après un 38) :
  relancée 11 minutes plus tard, la même séquence passe.

## 11. Avoir : la référence RN (15:06)

- Signature d'ESSAI-0009 lue dans le C1 de 14:45 (`appareil/signature.py --numero 2`), exportée sans affichage.
- 15:06:15 : C3 `R` ; C0 `1,Essai,{IFU},FA,COR,{SIG},TTC,ISF-ESSAI,AVOIR-0001,A` →
  **`E:Erreur de format RN! <la signature envoyée>`** : la structure de l'avoir est lue, RN est jugé, et le message
  renvoie la valeur. Rien d'ouvert.
- ✅ Les signatures du mode Test commencent par `TESTFACT` (vérifié sur les trois de la capture).
- Suite : RN en six groupes de 4 avec tirets, puis FN d'origine, puis numéro d'origine (`cycle.py --scenario avoir`,
  écho masqué à l'écran).
- 15:10 : RN = signature à tirets, FN d'origine, numéro d'origine → même refus ; l'écho reprend la valeur telle quelle.
  Suite : `NIM-TC` (forme d'ECOHADA au Niger), `NIM-ACNT-TC`, `2/4 FV` (identifiant unique de la note 0887), `NIM-2`.

## 12. Premier avoir certifié (15:13)

| Heure | Trame | Réponse |
|---|---|---|
| 15:13:36 | C0 `…,FA,COR,{NIM}-4,TTC,ISF-ESSAI,AVOIR-0001,A` | `E:Erreur de format RN!` |
| 15:13:42 | C0 `…,FA,COR,{NIM-ACNT}-4,TTC,ISF-ESSAI,AVOIR-0001,A` | **`1,5,CLIENT TEST,…`** |
| 15:13:45–49 | 31 bien B ; 31 service C | `100.0,84.75,15.25,0.0` ; `110.0,100.0,10.0,0.0` |
| 15:13:52 | 33 | total `214.2`, PSVB `4.2` |
| 15:13:55 | 35 `E214.20` | `R0` |
| 15:13:58 | 38 `214.20` | accepté : compteurs **`1/5 FA`** |

- ✅ RN = identifiant de l'appareil `NIM-ACNT` + `-` + TC de la facture d'origine. ESSAI-0009, aux paiements incohérents,
  est corrigée par l'avoir AVOIR-0001 (nature COR, mêmes lignes).
- Le cycle d'une facture et de son avoir est complet : vente, annulation, avoir.

## 13. Mode HT et écran des reçus (15:42)

- 15:42:53 : C0 `…,FV,HT,ISF-ESSAI,ESSAI-0011,A` → `3,6,CLIENT TEST,…` : **le mode HT est accepté**.
- 15:42:57 : 31 `ARTICLE TEST⇥LOCBIE,B18.0%100.00⇥100.00*1` → **`E:Mismatch de montant`** : en HT, le montant ou le prix
  ne s'entend pas comme en TTC. ESSAI-0011 reste ouverte ; les C3 suivants (scénarios `credit`, `modes`, lancés dans la
  même seconde) : NAK `a2` (C3 pendant une facture ouverte). Grille `ht` (6 formes) pour la suite, dans ESSAI-0011.
- Écran « Reçu de vente » de l'application fiscale (photo) : 102,00 à 11:30:46 (ESSAI-0008) avec le nuage vert,
  214,20 (ESSAI-0009) et (-214,20) (AVOIR-0001) avec un indicateur en cours : **transmis / pas encore transmis**.
  L'annulation (ESSAI-0010) n'y figure pas. Chaque reçu s'ouvre (`>`) : piste du code QR.
- 15:46:19 : grille `ht`, 1re forme : `ARTICLE TEST⇥LOCBIE,B18.0%118.00⇥100.00*1` → **`118.0,100.0,18.0,0.0`** (montant TTC,
  prix HT). ESSAI-0011 annulée ensuite par C1 : non comptée (le C0 suivant reprend `3,6`).
- 15:46:43–59 : scénario `credit`, ESSAI-0012 : 31, 33 (102.0), **35 `A102.00` → `R0`**, 38 accepté, **`3/6 FV`**.

## 14. Facture HT complète et blocage du C3 après un 38 (16:00–16:03)

- 16:00:23 et 16:00:32 : C3 → NAK `a2` (13 min après le 38 d'ESSAI-0012, sans C1 depuis). 16:01:38 : C1, statut normal,
  compteurs `6,3,1` ; son 10e champ (4) compte toutes les factures, pas le numéro dans le type.
- 16:03:18–34 : scénario `ht`, ESSAI-0013 : C3 `R`, C0 HT `4,7,…`, 31 `B18.0%118.00⇥100.00*1` → `118.0,100.0,18.0,0.0`,
  33 → `120.36,…,118.0,…,18.0,…,2.36,0.0` (montants TTC), 35 `E120.36` → `R0`, 38 → **`4/7 FV`**.
- 16:03:41 : C3 du scénario `modes`, 7 s après ce 38 → NAK `a2`. Règle : après un 38 accepté, C3 refusé jusqu'à un C1.
  `cycle.py` commence désormais chaque facture par un C1 et réessaie un NAK `a2` au C3.
- 16:07:09–38 : scénario `modes`, ESSAI-0014 : C1 de départ (compteurs 7,4,1), C3 `R`, C0 PSVB `D` `5,8,…`, 31 bien B,
  31 `POSE^x2c; TEST⇥IMPSER,C10.0%110.00⇥110.00*1` → `110.0,100.0,10.0,0.0`, 33 → `210.0,…,0.0,0.0` (PSVB 0),
  35 `V70.00` → `R-140.0`, `C70.00` → `R-70.0`, `D70.00` → `R0`, 38 → **`5/8 FV`**.
- Le reçu d'ESSAI-0008 ouvert sur l'appareil ne montre **pas de QR** : à construire par le logiciel, format à obtenir.
