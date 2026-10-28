# Référence du protocole du MCF Datamega FIS-NANO (état du 2026-10-28)

**Cycle complet prouvé le 2026-10-28** (facture ESSAI-0008 certifiée, environnement de test DGI) :
C3 client → C0 **avec PSVB** → 31 article → 33 sous-total → 35 paiement → 38 `MV` → éléments de sécurité.
Famille : 📖 « PROTOCOLE MCF-SFE v1.0 » de la DGI RDC (code tiers, `recherche/2026-10-28_balayage_sources.md`),
dont le Burkina diffère par le PSVB (C0, 33) et le 38 à une seule donnée.

Ce qui est prouvé sur l'appareil, avec la manière dont on le sait. Aucune donnée réelle : l'IFU s'écrit `{IFU}`, le NIM `{NIM}`.
Notes datées et trames brutes : `recherche/` (notes), `appareil/brut/` (captures, hors dépôt).

Certitude : ✅ prouvé sur l'appareil · 📖 lu dans un code tiers · 📜 texte officiel DGI · 🔍 hypothèse · ❓ inconnu.

## 1. Liaison

- ✅ USB CDC ACM (`/dev/ttyACM0`), 115200 8N1. L'appareil est un terminal Android (firmware V1.1.58_BF) ; l'application fiscale
  EazSell, en « MCF pur », doit être au premier plan, sinon silence total (0 octet).
- ✅ Protocole de la famille Datecs : l'hôte parle toujours le premier, une trame à la fois.

## 2. Trame

Requête : `01 | LEN | SEQ | CMD | DONNÉES | 05 | BCC | 03`

- ✅ `LEN = 0x20 + len(DONNÉES) + 4`. `SEQ` : un octet de `0x20` à `0xFF`. `CMD` : un octet (`C1`, `C0`, `31`...).
- ✅ `BCC` : somme des octets de `LEN` à `05` compris, écrite en 4 quartets, chacun + `0x30`.
- ✅ Réponse : `01 | LEN | SEQ | CMD | DONNÉES | 04 | STATUT (6 octets) | 05 | BCC | 03`. Statut normal : `80 80 80 80 80 80`.
- ✅ Une erreur est une réponse dont les données commencent par `E:` suivi du message, en **UTF-8** (« é » = `c3 a9`) ;
  le statut reste `80×6`.
- ✅ `15` (NAK) devant la trame : commande refusée dans cet état ; le statut est alors `a2 80 80 80 80 80` et les données sont vides.
  `16` (SYN) : attendre (jamais vu).
- 📖 Bits de statut (RDC) : octet 0 bit 0 erreur de syntaxe (✅ `a1`, 2B `I5`), bit 1 commande non valide (✅ `a2`, C3 en facture),
  bit 2 date non réglée ; octet 1 bit 1 commande interdite dans le mode, bit 4 rapport quotidien requis ; octet 2 bit 3
  facture ouverte ; octet 4 mémoire. Seuls `a1` et `a2` ont été vus.
- ❓ Deux trames consécutives de même commande et même séquence : rejeu possible de la réponse précédente (non prouvé ;
  deux commandes différentes de même séquence sont traitées normalement).

## 3. Lectures sans effet de bord

- ✅ **C1** (sans donnée) : 31 champs séparés par des virgules.
  `{NIM}-1`, `{IFU}`, date `AAAAMMJJhhmmss` (heure UTC de l'appareil, environ 1 min de retard sur le PC), trois compteurs,
  cinq champs vides, **16 taux** des groupes de taxe A à P (`0.0, 18.0, 10.0, 0.0, 0.0, 18.0, 10.0, 0.0, 0.0, 0.0, 0.0, 10.0,
  10.0, 0.0, 0.0, 0.0` ici), puis **4 taux PSVB** A à D (`2.0, 1.0, 0.2, 0.0`).
  Identique champ par champ d'un jour à l'autre. **Annule une facture ouverte** (voir §6).
- ✅ **C2** (sans donnée) : 3 champs, `envoyés,total,date du dernier contact avec le serveur`. Annule aussi la facture ouverte.
  La date change au démarrage et par audit périodique.
- ✅ **2B** avec `I0` à `I4` : nom commercial, adresse, quartier ou ville, téléphone, e-mail de la société (valeurs réelles, hors dépôt).
  `I5` : NAK et statut `a1 80 80 80 80 80` (2026-10-16), pas `a2` comme le C3 refusé dans l'état. 🔍 `a1` = paramètre inconnu.

## 4. Ouvrir une facture : C3 puis C0

### C3, déclarer le client (✅ cartographié le 2026-10-15)

Sept champs séparés par des virgules, **avant** C0. Réponse de succès : `R`.

| Champ | Rôle (📖 RDC : `type,NIF,nom,adresse,tél,e-mail,RCCM`) | Contrôle |
|---|---|---|
| 1 | type de client (📜 annexe SFE : `CC`, `PM`, `PP`, `PC`) | aucun vu (consommé, non recopié par C0) |
| 2 | IFU du client | aucun vu (`CLIENT TEST` accepté) |
| 3 | nom | aucun |
| 4 | adresse | aucun |
| 5 | téléphone | contrôle (un e-mail y donne `L'TEL e-mail du destinataire n'est pas valide`, texte de l'e-mail avec « adresse » remplacé par « TEL ») |
| 6 | e-mail | `x` ou un numéro : `L'adresse e-mail du destinataire n'est pas valide` ; `client@example.com` ou vide : accepté |
| 7 | RCCM | aucun |

L'exemple accepté ci-dessous met donc le nom à la place de l'IFU ; la forme régulière serait `PP,,CLIENT TEST,,70123456,…` (non essayée).

- ✅ Exemple accepté : `PP,CLIENT TEST,,,70123456,client@example.com,`.
- ✅ Un C3 vide (aucune donnée) répond `R` aussi.
- ✅ **`E:Erreur de type de destinataire` = trame qui n'a pas sept champs** (1 à 6, 8, 12 champs, tous les types et séparateurs
  essayés). Ce n'est pas un contrôle de valeur : `PP`, `PM`, `PC`, `CC` ne sont exigés nulle part.
- ✅ Pendant une facture ouverte : NAK (`a2`).
- ❓ `99988776,CLIENT TEST,,,` (5 champs) a répondu `R` le 14 octobre (peut-être un rejeu de séquence).

### C0, ouvrir la facture (✅ cartographié le 2026-10-15)

`opérateur,nom,{IFU},type,mode,ISF,FN[,client_IFU,client_nom][,PSVB]`

| Champ | Contrôle (message exact) |
|---|---|
| 1, 2 | libres |
| 3, IFU | doit être celui de l'appareil : `La valeur IFU ne correspond pas` |
| 4, type | `FV`, `FT`, `EV`, `ET` acceptés à 7 champs ; `x` : `Le type de reçu n'existe pas` ; `FA` et `EA` à 7 champs : message de format (🔍 un champ d'origine de plus) |
| 5, mode | `TTC` ou `HT` ; sinon, vide compris : `Incohérence du mode de tarification HT/TTC` |
| 6, ISF | non vide : `L'ISF du destinataire est obligatoire` ; toute valeur non vide est acceptée (`ISF-ESSAI`, `x`) |
| 7, FN (référence) | non vide : `L'FN ne peut pas être vide!` |
| 8 (à 8 champs), dernier à 10 champs, PSVB | `x` : `PSVB n'existe pas!` ; `A` accepté. ✅ **Sans PSVB, aucun article n'est accepté** : toute 31 répond `La taxe est incorrecte!` |
| 9 champs | `…,x,x` accepté (🔍 IFU et nom du client, comme au Bénin) |

- ✅ Forme de la facture certifiée du 2026-10-28 : `1,Essai,{IFU},FV,TTC,ISF-ESSAI,ESSAI-0008,A`. 📖 Avoir (RDC) :
  `type,nature,référence` à la place du type (nature 📜 `COR`, `RAN`, `RAM`, `RRR` ; référence = signature d'origine).

- ✅ `E:Erreur de format des données ou incompatibilité` = **nombre de champs faux** (5, 6, 12 champs).
- ✅ Réponse : `n,tc,` suivi des **champs 2 à 7 du client** déclaré par C3 : `1,3,CLIENT TEST,,,70123456,client@example.com,`.
  Sans client : `1,3,,,,,,`.
- ✅ Un C3 déclaré plus de 100 s avant le C0 n'a pas été rattaché ; 11 s plus tôt, oui (✅ 13:13 et 13:44).
- ✅ Les formes béninoises (20 ou 16 taux) sont refusées au format.

## 5. Articles et clôture

### 31, ajouter un article : ✅ accepté le 2026-10-28

`nom[⏎code]⇥TYPE,G{taux}%{montant}⇥{prix}*{qté}` — accepté : `ARTICLE TEST⇥LOCBIE,B18.0%100.00⇥100.00*1`.
Réponse : `100.0,84.75,15.25,0.0` (TTC, HT, TVA, 🔍 taxe spécifique).

Ordre des contrôles, du premier au dernier (✅ 2026-10-28, environ 110 trames) :

| Contrôle | Message |
|---|---|
| structure : 3 champs à tabulation ; `%` dans le 2e ; prix `…` ou `…;T…` | `E:Erreur de format des données ou incompatibilité` (`LOCBIE,B100.00` sans `%` ; prix `100.00;0.00`) |
| type d'article | `E:Le type de produit n'existe pas` : `BIE`, `IMPSERV`. Passent : `LOCBIE`, `LOCSER`, `IMPBIE` (🔍 `IMPSER`, mention de l'annexe) |
| taxe | `E:La taxe est incorrecte!` pour **toute** écriture tant que le C0 n'a pas de PSVB (16 groupes, `G%taux`, taxe nulle, avec ou sans quantité) |

- ✅ Sans C0 : `E:La commande C0 doit être soumise en premier`. Donnée vide : `E:Aucune donnée valide n'a été reçue`.
- ✅ Tolérés à la structure (dans la facture sans PSVB, donc jugés « taxe ») : sans `*qté`, `;T0,0` après la quantité, un sous-champ de plus.
- ❓ Avec PSVB, une seule forme a été envoyée : on ignore ce que donnent les autres écritures du taux et du montant.
- Les plus de 500 formes refusées du 9 au 15 octobre manquaient toutes le type devant la virgule.
  Générateurs : `appareil/recherche_article.py --liste --grille …` (grilles `rdc`, `taxe`, `taxe2`, `groupes_rdc`, `quantite`, `psvb_rdc`).

### 36, commentaire de facture : ✅ accepté le 2026-10-16

`clé,texte` (virgule), **dans une facture ouverte**, avec ou sans article. `A,ESSAI` répond `R`. Sans C0 : `E:La commande C0 doit
être soumise en premier`. `ESSAI` (1 champ), `Z,ESSAI` (clé hors A–H) et `A,ESSAI,X` (3 champs) : `E:Aucune donnée valide n'a été reçue`
(le même message que 31 pour une donnée vide : ici, c'est le message d'un mauvais découpage, pas d'une valeur).
Forme ECOHADA NE (📖 `#;A;texte` du CSV, cmd 0x36). Une 36 acceptée ne compte pas comme article. Après elle, 33 répond
`E:Veuillez ajouter le produit en premier.` **avec un point final** ; les captures du 12 octobre n'en ont pas (🔍 la 36 change
le chemin du message ; à vérifier par un 33 sur une facture neuve sans 36).

### 33, sous-total : ✅ 2026-10-28

Sans donnée. Réponse à 35 champs : total à payer, 16 montants TTC des groupes A–P, 16 TVA des groupes A–P, **PSVB**, 🔍 taxe
spécifique. Pour l'article ci-dessus : `102.0` = 100 TTC + 2.0 de PSVB (catégorie A, 2 % du TTC, 📜 SFE §6.10) ; B `100.0` ; TVA B
`15.25`. Sans article : `E:Veuillez ajouter le produit en premier` (avec point final après une 36).

### 35, paiement : ✅ 2026-10-28

`{mode}{montant}` : `E102.00` → `R0` (`R` + reste). 📖 Modes (RDC, Bénin) : `E` espèces, `V` virement, `C` carte, `M` mobile, `D` chèque,
`A` autre ; seul `E` essayé. Sans article, vide : `E:Le montant payé est suffisant`.

### 38, normalisation : ✅ 2026-10-28

**Une seule donnée, `MV`** (le total à payer du 33) : `102.00` accepté. Avec une virgule (`102.00,15.25`, `102.0,15.25`, `102,15.25`,
trois champs) : `E:MV n'est pas un nombre valide.` (la chaîne entière est lue comme MV). Avant 35 : `E:La commande 35 doit être
soumise en premier.` Vide, sans article : `E:Aucune donnée valide n'a été reçue`.

Réponse à 8 champs : compteur de factures de vente, compteur total, type (`FV`), date `AAAAMMJJhhmmss`, `{NIM}`, `{IFU}`,
**signature (24 caractères)**, FN. Valeurs réelles dans `appareil/brut/2026-10-28_seance.txt` (hors dépôt).
📖 RDC : réponse `P:` = renvoyer la même commande (jamais vue).

### Annulation

C1, C2 ou un rallumage annulent une facture ouverte. 📖 RDC : `38` avec `C` → `E:ANNULEE` ; ici, sur une facture sans 35,
réponse `E:La commande 35 doit être soumise en premier.` : ❓ non tranché.

## 6. États (✅)

1. **C3 avant C0** : C3 pendant une facture ouverte donne NAK.
2. Un C0 renvoyé pendant une facture ouverte est accepté et recopie le même client.
3. Une facture ouverte sans article reste ouverte plus de 24 minutes, avec son client, tant qu'on n'envoie que des 31.
4. **C1, C2 ou un rallumage de l'appareil l'annulent**, sans la compter (les compteurs restent `2,0,0`).
5. Il n'y a **pas d'état caché** : la réponse d'une trame ne dépend que de sa charge utile et de la facture ouverte.
   (Les « bascules » vues les 14 et 15 octobre venaient de C3 vides, qui répondent `R`.)

## 7. Outils du dépôt

| Fichier | Rôle |
|---|---|
| `appareil/trame.py` | envoie UNE trame ; `{IFU}` remplacé par `MCF_IFU` (9 caractères) |
| `appareil/carte_client.py` | carte des contrôles de C3 (17 trames) |
| `appareil/carte_c0.py` | carte des contrôles de C0 (22 trames) |
| `appareil/recherche_article.py` | grilles de 31 : nombres, nombres2, gabarits, photo, anciens, groupes, psvb ; rdc, taxe, taxe2, groupes_rdc, quantite, psvb_rdc |
| `appareil/recherche_structure.py`, `recherche_bornee.py` | grilles de nombre de champs et de types de C3 |
| `simulateur/faux_mcf.py --variante FIS` | jumeau : rend ce qui a été observé ; `C3_OBSERVE` pour les C3 |

Cadre de chaque séance : une trame toutes les 3 s, 80 au plus, arrêt au premier message nouveau, au NAK, au silence ou à la
déconnexion ; EazSell au premier plan ; accord de l'opérateur ; aucun geste irréversible.

## 8. Ce que dit la spécification officielle 📜 (note 2025-0887, `officiel/`)

Relue le 2026-10-15 (11 pages, scan). Elle ne donne aucun format de trame.

- §2.1.7 à 2.1.9 : port A (SFE) et port B (audit local). Port A : USB ou série, 115200 8N1, « protocole défini par l'Administration ».
  **Port réseau (LAN, Wi-Fi) optionnel**, protocole lui aussi défini par l'Administration : pas une interface documentée à part.
- §2.2.1, 2.2.2 : la clé de cryptage, la clé de code et l'IFU sont stockées dans le MCF, **sans lecture externe**. Le logiciel
  de facturation n'a aucune clé à fournir : le MCF signe lui-même (§2.10.3).
- §2.5.4, 2.5.7 : états Non-activé, **Actif**, Bloqué, Désactivé. Une facture n'est enregistrée que si le MCF est **Actif**.
  Bloqué si le dernier audit à distance réussi est plus vieux que `PARAM_BLOCK` jours, ou si les transactions non envoyées
  dépassent `PARAM_BLOCK2` (quand ils ne valent pas 0).
- §2.5.6 : **mode Test** : l'appareil se **désactive automatiquement** après le nombre de jours fixé par l'Administration à
  l'activation, ne peut plus être réactivé, seulement réinitialisé (§2.8 : par un technicien autorisé, toutes les transactions
  déjà envoyées). ❓ L'appareil est-il en mode Test et pour combien de jours : inconnu ; le tableau de bord affiche « Activé »
  le 15 octobre, et ses rapports C et Z datent du 8 octobre.
- §2.10.2 d : le MCF **rejette** une facture si le montant total est ≤ 0, si le montant d'un article est ≤ 0, ou si le numéro de
  facture envoyé est égal à celui de la dernière facture certifiée (jamais deux fois la même référence). Aucun contrôle de
  l'ISF n'y figure.
- §2.10.3, 2.10.4 : éléments de sécurité : code SECeF/DGI, identifiant `NIM-ACNT`, compteurs `CPIT/FDOC ITL`, date et heure du MCF,
  code QR.
- §2.14 : l'audit à distance s'exécute automatiquement, quel que soit l'état du MCF.
