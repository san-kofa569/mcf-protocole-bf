# Carte du binaire ECOHADA MCF CLI 23.04081 (MCF-CLI.exe)

Lecture statique (radare2), PE **32 bits** (pei-i386, pas x64), image base 0x400000, `.text` 0x401000, `.rdata` 0x41e000, `.data` 0x428000.
Adresses = VA. Certitude : **[L]** lu en clair, **[D]** déduit du code, **[S]** supposé.

Vérité terrain à utiliser pendant les essais : le CLI écrit sur la console, pour chaque trame, `Donnees: <données échappées>` puis `Reponse: <réponse>` (fcn.00415790 : chaînes 0x41ecd8 / 0x41eccc, journal via fcn.00411910). Comparer ces lignes à la carte ci-dessous tranche tout doute. [L]

---
## 0. Réponses aux questions ouvertes (NE)

**A. Données de 31 (article), NE — fcn.004096b0** [L pour la structure, D pour le rôle de chaque champ]

```
data31 = esc(left(designation,64))
         [ "\n" + esc(left(code,24)) ]          ; seulement si 'code' non vide (toujours vide depuis ce CSV)
         + "\t" + R + MAP[R] + "%" + esc(TS)
         + "\t" + esc(PU) + "*" + esc(QTE)
```
- `R` = lettre de régime telle qu'elle est dans le CSV (A..F...), recopiée brute ; `MAP[R]` = chaîne de `map 0x4284fc[R]`, remplie par la réponse de C1 (voir §3.1) : pour NE, A..P = champs 9..24 de la réponse C1 (A=9, B=10, C=11, D=12, E=13, F=14, G=15, H=16, I=17, J=18, K=19, L=20, M=21, N=22, O=23, P=24). Donc `<groupe><valeur lue dans C1>` collés, puis `%`. [L pour l'assemblage 0x4098ad-0x409912, D pour « valeur = taux »]
- Séparateurs : TAB (QChar 9) avant le groupe, `%` juste après MAP[R], TAB avant le prix, `*` entre prix et quantité. Pas de virgule. [L]
- Tous les champs passent par `esc()` (fcn.004155a0, §4). [L]
- Nombres : prix et TS arrivent **déjà formatés** par `%.0f` après `round()` (0x41fe3c, appels asprintf en 0x412810, 0x41286a, 0x41289f, 0x4128d1, dans fcn.00411ea0). La quantité (QTE) est la chaîne du CSV telle quelle (trimmée), non reformatée. [L]
- Choix HT/TTC selon `modePrix` (app.xml, comparé à "TTC", 0x4096e2/0x409711) : mode TTC → PU = F3 (arrondi du PU TTC, col. 4) et TS = F1 ; sinon (HT, valeur par défaut) → PU = F4 (arrondi du PU HT, col. 3) et TS = F2. [L pour le choix, via `cmove` en 0x409701 et 0x40972d]
- **Vérifié en exécution le 2026-10-10** (recherche/2026-10-10_execution_ecohada.md) : F1 = round(PU TTC × qté + col. 7), F2 = round(PU HT × qté + col. 6) ; les colonnes 5 et 6 non vides ajoutent `;T<col 5>,<col 6>` après la quantité. Note d'origine : F1 = round(PU_TTC × qté + X) et F2 = round(PU_HT × qté + Y), avec X = colonne article 8 (index 7) et Y = colonne article 7 (index 6) du CSV selon le rangement `at(idx)` de fcn.00411ea0 (0x4122d0-0x412660). Ça ressemble à un total de ligne et non à une taxe spécifique : si le champ après `%` ressort comme un grand nombre, c'est cette formule. Si taxes spécifiques = 0, attendre `...%<total ligne>`. Comparer avec la ligne `Donnees:` avant de conclure.
- Régime vide : si la colonne 1 de l'article est vide, le CLI la remplace par `B` si la TVA de la ligne (qté×(PU TTC − PU HT) arrondie, toLong) est non nulle, sinon `A` (0x412665-0x4126af). [L]
- Code commande : octet **0x31** ; réponse : découpée par `,`, le CLI attend **exactement** 5 champs (`cmp [liste+8],5 ; sete` en 0x409e9c). [L]

**B. Type de destinataire de C3** : **aucune constante** (`CC`, `PM`, `PP`, `PC` absents de `.rdata`, vérifié sur toutes les chaînes). Les 3 derniers champs de C3 sont les colonnes CSV d'index 7, 8, 9 de la ligne d'en-tête (0x42855c, 0x428568, 0x428574), recopiés tels quels (trimmés, échappés). [L]
Donc le « type de destinataire » vient d'une de ces trois colonnes ; le binaire ne dit pas laquelle (non typé). [S : c7 = type, c8/c9 = adresse/contact]

**C. Ce qu'envoie 35 (NE et BJ communs ?)** — fcn.0040aa70, cmd **0x35** [L] :
```
data35 = esc(MODE) + esc(MONTANT)      ; AUCUN séparateur [L, 0x40b43b : concat(a,b)]
```
- `MODE` = colonne en-tête index 4 (0x4285bc) ; accepté s'il est dans la liste {V, C, M, D, E, A} (liste construite en 0x40aad4..0x40b3e7), sinon remplacé par `A` (0x40b3ef). [L pour V,C,M,D,A ; D pour E]
- `MONTANT` = **premier champ de la réponse de la commande 0x33** (sous-total, §3.5), copié tel quel. **Ce n'est pas la colonne 14 (montant reçu)** : elle n'est lue nulle part (le découpage s'arrête à l'index 12). [L : 0x412d9a, `esi = début de la liste`, passé à fcn.0040aa70 avec 0x4285bc]
- Succès si la réponse commence par `R` (0x41f04c, test `startsWith` en 0x40b49f). [L]

**D. Protocole 1.1 / 2.0** : il n'y a **pas** de bascule 1.1/2.0 dans ce binaire. La variante est **détectée sur la réponse de C1** : réponse à **10 champs** → variante « BJ » (journal « Initialisation MCF BJ terminee. »), **29 champs** → « NE » (« Initialisation MCF NE terminee. »), autre → « Initialisation échouée » (fcn.0040fcc0, `cmp eax,0xa` en 0x40fd5a, `cmp eax,0x1d` en 0x410075). Le résultat est stocké dans la chaîne globale 0x4284cc ("BJ"/"NE"), testée par C3 (0x40f627), le commentaire (0x40fb1e), les dispatchers fcn.00411ce0 (C0) et fcn.00411a50 (31). L'attribut `versionMCF` d'app.xml n'est lu que pour la licence (passé à fcn.00410c00). Les paramètres de ligne de commande n'ont aucun rôle de version. [L]
Différence C0/31 BJ vs NE : BJ → fcn.00408d50 (C0) et fcn.004087e0 (31) ; NE → fcn.00409fb0 (C0) et fcn.004096b0 (31). Les versions BJ n'ont pas été lues en détail. [L pour l'aiguillage]

---
## 1. Format du CSV d'entrée

Découpage : fcn.00415dd0 (appelée par main en 0x417f5f pour chaque ligne lue par `QTextStream::readLine`, main 0x417ed0). [L]
- Fichier = `argv[1]` (défaut `<dossier exe>/input.csv`, chaîne 0x4201ec) ; sortie = `argv[2]` sinon `<entrée>.mcf` (0x4201f8). Le fichier de sortie est supprimé au démarrage (`QFile::remove`, 0x4176f9). [L]
- Séparateur **`;`** (`QChar(0x3b)` en 0x415e39, 0x4137.., 0x4145..). Chaque champ est `trimmed()`. [L]
- Lignes vides ignorées (test `== ""` en 0x417ef3). Un octet de la ligne est supprimé avant traitement (`replace(QChar, "")` en 0x417f2e ; le caractère exact n'a pas été isolé, probablement `\r`). [D]
- Compteur de lignes global 0x428428 : **ligne n°0 = en-tête de facture** ; les suivantes : si la ligne commence par `#` → **commentaire** (fcn.00414590), sinon → **article** (fcn.004136d0). [L : 0x416977-0x4169d3]

### 1.1 Ligne d'en-tête (index 0-basés ; fcn.00415dd0 0x415e51-0x4166e1)
| idx | global | usage |
|---|---|---|
| 0 | 0x4285b0 | référence de la facture (clé SQL, C0, table `facture`) |
| 1 | 0x42852c | type (FV, FA, EV, EA ...) passé tel quel à C0 |
| 2 | 0x428474 | nom du vendeur (affiché « Utilisateur: ») |
| 3 | 0x428498 | ID du vendeur |
| 4 | 0x4285bc | mode de règlement (→ 35) |
| 5 | 0x428550 | nom du client |
| 6 | 0x428580 | IFU du client |
| 7 | 0x42855c | C3 : 3e champ (type destinataire ?) |
| 8 | 0x428568 | C3 : 4e champ |
| 9 | 0x428574 | C3 : 5e champ |
| 10 | 0x428598 | clé « taux AIB/ISB » (A, B, C, D... ; recopiée en 0x42858c) ; sert à C0 (dernier champ) et à l'affichage `Taux <AIB|ISB> <n>%` |
| 11 | (local) | référence de la facture d'origine (remboursement) : cherchée dans la base (§5) |
| 12 | 0x4285a4 | document à éditer (argument de `MCF-Print "..."`, 0x420068) |
Au-delà de 12, rien n'est lu. **Écart avec le manuel Bénin 2020** : le binaire lit trois colonnes de plus (7, 8, 9) entre l'IFU client et le taux AIB ; AIB passe de l'index 7 à 10, réf. remboursée de 8 à 11, document de 9 à 12. Les colonnes manuel 11 à 18 (date, code client, adresse, montant reçu, ...) ne sont pas lues. [L pour les index, S pour le manuel]

### 1.2 Lignes article (fcn.004136d0)
| idx | usage |
|---|---|
| 0 | régime fiscal (A..F ; vide → A/B automatique, §0.A) |
| 1 | désignation |
| 2 | quantité |
| 3 | PU HT |
| 4 | PU TTC |
| 5, 6, 7 | taxe spécifique HT, TTC, % (rôle exact [S]) |
Calculs de contrôle faits à la lecture : TVA ligne = round(qté×PU TTC − qté×PU HT), format `QLocale::toString(double,'f',0)` (0x413ab8) ; total affiché `%.4f` (0x41f148), cumul global 0x428430 (« Total facture: »). Rangement interne d'une ligne (QList) : [désignation, qté, PU HT, TVA, PU TTC, c5, c6, c7, régime]. [D]
La ligne est ajoutée dans la liste globale 0x4285c8. [L]

### 1.3 Lignes `#` (fcn.00414590)
Ligne `#;<clé>;<texte>` : découpée par `;`, champs 1 et 2 retenus (le champ 0 est le `#`), liste globale 0x4285d4 ; une clé hors {A..H} est ignorée sans message (vu en exécution le 2026-10-10). Envoyés par fcn.0040faf0 **uniquement en NE** : cmd **0x36**, données = `esc(a)` + `,` + `esc(b)` (D, ordre non vérifié). La clé doit appartenir à {A,B,C,D,E,F,G,H} (0x412b5c-0x412c44) ; sinon erreur « Impossible de soumettre un commentaire ». [D]

### 1.4 Arguments de l'exe (main 0x416b06-0x417756)
`argv[1]` entrée (ou `--start-server` : lance `php/php -S 0.0.0.0:801` avec `index.php`, `--stop-server` : `taskkill php.exe`) ; `argv[2]` sortie ; `argv[3]` port COM (valeur `0` = garder celui d'app.xml) ; `argv[4]` = `hide` → `FreeConsole` ; `argv[5]` → encodage (0x428608). [L pour 1, 2, 4 ; D pour 3, 5]

---
## 2. Configuration : `app.xml`

Fichier `<dossier exe>/app.xml` (0x420268), parsé avec QDomDocument ; **élément racine**, attributs (main 0x4170be-0x417590). Pas de registre. [L]

| attribut | rôle | défaut absent |
|---|---|---|
| `licence` | clé de licence (liste de UUID datés, fcn.00410c00) | vide |
| `pays` | `Bénin` ou `Niger` (comparé à `Bénin`/`Niger` UTF-8). Sert à choisir l'URL HTTP/le calcul AIB/ISB, pas la variante BJ/NE du protocole série | vide |
| `portMCF` | nom du port série (COMx). Vide → premier port disponible. `DEMO` → réponses simulées (si non licencié) | vide |
| `versionMCF` | lu, transmis à la routine de licence uniquement | vide |
| `encodage` | entier base 10 → `QStringConverter::Encoding` du flux d'entrée (0x417d54-0x417d7f) | encodage par défaut de Qt |
| `isf` | identifiant du logiciel de facturation envoyé dans C0 ; **vide → `ECOHADA`** (0x40a2b5-0x40a2ce) | `ECOHADA` |
| `modePrix` | `TTC` → prix TTC ; autre/vide → HT | HT |
| `modeMCF` | `Développement` → URLs de test ; sinon production (HTTP seulement) | production |
| `jeton` | jeton Bearer (`Authorization: Bearer ...`, 0x41fc34) pour le serveur HTTP | vide |
| `tolerance` | double, écart accepté entre total CSV et sous-total MCF (0x4284b8) | 0 |
Série : `QSerialPort`, **115200 bauds** (0x1c200, 0x411f86), ouverture lecture/écriture (mode 3), pas de réglage de parité lu. [L]
URLs HTTP (pour le mode serveur, non utilisé par le flux série) : 0x41ebc0 / 0x41ebec (Bénin prod/test), 0x41ec24 / 0x41ec50 (Niger prod/test). Clés JSON : `isf`, `mode`, `reference`, `items`, `client`, `operator`, `payment`, `taxSpecific`, `taxGroup`, `amount`, `price`, `quantity`, `uid`, `qrCode`, `codeMECeFDGI`, `codeSECeFDGI`, `counters`, `nim`, `dateTime`... [L]

---
## 3. Protocole série (Datecs-like)

### Trame (fcn.00415790 + fcn.0040d9d0) [L/D]
`0x01` | LEN = longueur_données + 0x24 | SEQ (0x20..0xFF, repart à 0x20 ; initialisé à 0x1F, 0x428068) | CMD | DATA (octet bas de chaque QChar, donc Latin-1 tronqué ; le caractère U+0152 est supprimé avant) | `0x05` | BCC (4 demi-octets ASCII +0x30) | `0x03`. Attente de réponse `waitForReadyRead(30000)` (0x7530) en boucle ; `0x16` ignoré, `0x15` → « NAK recu: Commande incorrecte. » ; la réponse = octets du rang 4 jusqu'au premier `0x04` (texte). Les réponses utiles sont ensuite découpées par `,`.

### 3.1 C1 (0xC1) état de la machine — fcn.0040fcc0, données vides
Réponse à 10 champs (BJ) : champ 1 → IFU (global 0x4284c0) ; champs 6..9 → A..D ; mappe aussi `AIB1`→"1", `AIB5`→"2" (0x428500) et taux AIB 1.0 / 5.0 (0x428504). Réponse à 29 champs (NE) : champ 1 → IFU ; champs 9..24 → A..P (voir §0.A) ; 0x428500 : A→"5", B→"2", C→"6", D→"7" ; 0x428504 (taux ISB) : A=2.0, B=5.0, C=0, D=0. Si ni 10 ni 29 champs : échec. [L pour les index, D pour la sémantique]

### 3.2 C2 (0xC2) état serveur — fcn.00411ea0 0x411ff9, données vides (n'est envoyée que si le flag `[objet+0x60]` est vrai, c.-à-d. chemin « sans fichier d'entrée »). [L]
### 3.3 2B (0x2B) infos société — fcn.0040f9b0 : 5 requêtes de données `I0`..`I4` (nom, adresse, ville, téléphone, email). [L]
### 3.4 C3 (0xC3) client — fcn.0040f5f0, **NE seulement** (`== "NE"` sinon rien n'est envoyé, retour vrai) [L]
```
data = esc(IFU_client) "," esc(nom_client) "," esc(c7) "," esc(c8) "," esc(c9)
```
(IFU = col. 6, nom = col. 5, c7..c9 = col. 7, 8, 9.) Succès si la réponse se découpe en exactement 1 champ (`cmp [liste+8],1` en 0x40f944). Appelée **avant** C0 (0x4121bd avant 0x41224f). [L]

### 3.5 C0 (0xC0) ouverture de facture, NE — fcn.00409fb0 [L]
```
data = esc(ID_vendeur=col3) "," esc(nom_vendeur=col2) "," esc(IFU lu par C1)
       "," col1(type)                       ; non échappé
       [ "," esc(NIM-TC d'origine) ]        ; si non vide
       "," modePrix   "," isf               ; app.xml, isf défaut ECOHADA
       "," col0(référence)
       [ "," esc(col10 clé taux) ]          ; si non vide
```
Succès si la réponse se découpe en **exactement** 7 champs, champs vides compris (`cmp [liste+8],7 ; sete` en 0x40a503, `split(',', KeepEmptyParts)`) ; corrigé le 2026-10-10 en exécution (8 champs → « Impossible de soumettre une facture »). [L pour l'ordre, D pour ID/nom (concat 0x40a059-0x40a122 : col3 puis col2)]
BJ : fcn.00408d50 (non lu).

### 3.6 31, 33, 35, 38
- **31** : voir §0.A (NE). BJ : fcn.004087e0 (non lu).
- **33 (0x33)** sous-total — fcn.00415a10 : données vides ; la réponse est découpée par `,`, il faut ≥ 9 champs ; champ 0 = total du MCF, comparé au total calculé (0x428430) avec la tolérance. Journal : « Difference facture: », « Total facture acceptable: », « Total facture inacceptable: ». Le champ 0 est ensuite repris comme montant de 35. [L/D]
- **35 (0x35)** : voir §0.C.
- **38 (0x38)** clôture — fcn.0040bee0 : données vides (`push 0x41eca2`, chaîne vide). [L]

### 4. Réponse de 38 (découpage par `,`) [L pour les index, D pour les noms]
- 6 champs → « La facture a ete annulee. » (rien enregistré).
- 7 champs → « La facture a ete validee. » avec :

| champ | contenu | colonne SQLite |
|---|---|---|
| f0 | compteur du type (ex. `82`) | entre dans `mecef_compt` |
| f1 | compteur total | **`mecef_tc`** |
| f2 | type de document (`FV`...) | entre dans `mecef_compt` |
| f3 | date-heure `yyyyMMddHHmmss` | **`mecef_date`** (affichée `dd/MM/yyyy HH:mm:ss`, 0x420014) |
| f4 | NIM | **`mecef_nim`** |
| f5 | IFU (13 chiffres) | seulement dans le QR |
| f6 | signature (24 car.) | **`mecef_sig`** |

- `mecef_compt` = `f0` + `/` + `f1` + ` ` + `f2` (ex. `82/87 FV`, valeur de démo en 0x4203dc). [L 0x40c3f0-0x40c4d6]
- `qrcode` = `F;` + f4 + `;` + f6 + `;` + f5 + `;` + f3 (ex. démo `F;<NIM>;<signature>;<IFU>;<date>`). [L 0x40c0..0x40c28c ; démo 0x420370]
- Ordre du vecteur retourné → `insert into facture (reference, qrcode, mecef_tc, mecef_sig, mecef_nim, mecef_compt, mecef_date) values('<réf>','<qr>','<f1>','<f6>','<f4>','<compt>','<f3>')` (fcn.0040b8e0, 0x41ff20). [D : l'ordre du vecteur [QR, f1, f6, f4, compt, f3] colle à celui des colonnes]
- Si la réponse a un autre nombre de champs, rien n'est inséré. Journal : « QR: ... ».

### 5. Base `mcf.s3db` et remboursement
- Avant traitement : `select qrcode, mecef_tc, mecef_sig, mecef_nim, mecef_compt, mecef_date from facture where reference = '<réf>'` (0x4204a8) ; si trouvée : « Cette facture est deja validee. » et rien n'est renvoyé au MCF, la sortie `.mcf` est rejouée depuis la base (fcn.0040caf0). [L]
- Colonne 11 (réf. d'origine) : `select mecef_nim, mecef_tc, mecef_sig from facture where reference = '<col11>'`. NE : valeur d'origine = `NIM` + `-` + `TC` (0x416433-0x4164c1) ; BJ : champ 2 (signature) (0x416325-0x416416) ; non trouvée : si la valeur saisie contient `-` elle est utilisée telle quelle (« Facture non retrouvee: »), sinon vide → message « (NIM-)TC de facture originale manquant. » [L/D]
- Sortie (`.mcf`) : écrite par fcn.0040caf0, séparateur TAB (0x420028) ; QR aussi en `.png`/`.svg`. [L]

---
## 4. Échappement `esc()` — fcn.004155a0 [L]
Dans l'ordre : CR (13) → `^xa;` ; LF (10) → `^xd;` (les deux sont **croisés** : CR donne `^xa;`, LF donne `^xd;`) ; `,` → `^x2c;` ; `<` → `^lt;` ; `>` → `^gt;` ; `&` → `^amp;` ; apostrophe `'` → espace. Le `\t` et `*`, `%` ne sont pas échappés. Appliqué à tous les champs texte de C0, C3, 31, 35 et au commentaire, mais pas au type (col. 1) de C0. Troncatures : désignation 64 caractères, code 24 (31).

## 5. Messages utiles
« Le port a ete ouvert. » · « Impossible d'ouvrir le port. » · « Aucun port de communication trouve. » · « Erreur: Impossible d'initialiser le MCF. » · « Erreur: Impossible d'enregistrer le client. » · « Erreur: Impossible de soumettre une facture / un article / un commentaire. » · « NAK recu: Commande incorrecte. » · « Aucune reponse. » · « Message non compris: » · « La version gratuite ne permet pas de valider les factures de plus de ... » (plafond en 0x428060 = 0x40d86a000000 ≈ 25,000,000 ? [S]) · « Votre licence ECOHADA MCF CLI a expiré ».
Mode licence : `portMCF=DEMO` sans licence renvoie des valeurs fixes (NIM, signature et IFU fixes de démonstration, compteur `82/87 FV`).

## 6. À vérifier en priorité sur trame
1. Champ après `%` de 31 et formules F1/F2 (§0.A) : comparer `Donnees:` avec un article simple (régime B, qté 1, PU HT 1000, PU TTC 1180, taxes spécifiques 0).
2. Rôle de c7, c8, c9 dans C3 (§0.B).
3. Ordre exact de la virgule du commentaire 0x36 et valeur de F3/F4 en mode HT.
4. Adresses de contrôle : fcn.004096b0 (31 NE), fcn.00409fb0 (C0 NE), fcn.0040f5f0 (C3), fcn.0040aa70 (35), fcn.00415a10 (33), fcn.0040bee0 (38), fcn.0040fcc0 (C1), fcn.00411ea0 (orchestration, lignes 0x4122d0-0x412d9a), fcn.00415dd0 / fcn.004136d0 (CSV).
