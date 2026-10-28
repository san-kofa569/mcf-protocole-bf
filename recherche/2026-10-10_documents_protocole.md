# Documents publics sur le protocole SFE / MCF — carte du 2026-10-10

Résultat net : aucun texte officiel (Niger ou Bénin) n'a pu être récupéré. Les formats de 31, 33, 35 et 38 ne sont connus que par du code tiers béninois (version ancienne du protocole). Le format de C3 et le champ « type de destinataire » ne figurent dans aucune source trouvée. Les messages `E:…` ne sont pas catalogués.

Degrés de certitude : [OFFICIEL] texte de l'autorité ; [CODE TIERS] code public d'un éditeur ; [DEDUCTION] inférence de ma part.

## 1. « SECeF Niger — Protocole entre SFE et MCF » (docplayer.fr/206969300)

- URL : https://docplayer.fr/206969300-Secef-niger-protocole-entre-sfe-et-mcf.html
- Non récupéré : WebFetch répond `getaddrinfo ENOTFOUND docplayer.fr` ; l'API Wayback (`archive.org/wayback/available`) ne renvoie aucun instantané pour les deux formes d'URL ; l'index CDX ne donne rien pour `docplayer.fr/206969300*` ; `web.archive.org/web/2023/...` répond 404. Deux recherches web sur le titre ne remontent aucune page docplayer.
- Rien à dire de C3, C0, 31, 33, 35, 38 pour cette source.

## 2. Guide nigérien des éditeurs de SFE (impots.gouv.ne, PDF 33 p.)

- Non retrouvé aujourd'hui. L'index CDX de web.archive.org pour `impots.gouv.ne` (formulaires, lois, imprimés) ne contient aucune URL avec « sfe », « secef », « editeur » ou « guide ». Il faudrait l'URL exacte de la veille.
- Rien à dire des commandes.

## 3. PDF ECOHADA (fichiers dans `externe/docs/`)

| Fichier | URL | sha256 |
|---|---|---|
| ecohada_secef.pdf (52 p.) | https://www.ecohada.com/pdf/ecohada_secef.pdf | 2ad6193daaf00042d18b666242abb7dad3b365f23b5627fdc5acdd4b7debe914 |
| ecohada_mecef.pdf (23 p.) | https://www.ecohada.com/pdf/ecohada_mecef.pdf | e161c01730a3a35a54711bc2cdbfba623e8651f9fa3ab071eb2d1e21a006687f |
| ecohada_emecef.pdf (24 p.) | https://www.ecohada.com/pdf/ecohada_emecef.pdf | 1cf8fab2bb8b35fe8f2424351f86b320286294fb8e7325131a262eabf2d00ca1 |
| ecohada.pdf (17 p.) | https://www.ecohada.com/pdf/ecohada.pdf | 4bddf4c650fbd9e7715876cac3e646b1c7226c1a38bcddaa97ea3ebb1934f4ad |

Contenu (pdftotext) :
- `ecohada_secef.pdf` (Niger) : essentiellement des factures normalisées d'exemple (société d'exemple, Niamey), répétées. Un « CODE SECeF/DGI » de la forme `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX` apparaît ; cela ressemble à la signature en groupes de 4 caractères séparés par des tirets.
- `ecohada_mecef.pdf` (Bénin) et `ecohada_emecef.pdf` (Bénin, e-MECeF) : « L'auto-déclaration de SFE » (types de factures générés, groupes d'impôt gérés). Ce n'est pas la description du protocole.
- `ecohada.pdf` : plaquette commerciale.
- Aucun ne décrit de commande (C3, C0, 31, 33, 35, 38), ni de CSV d'entrée, ni d'erreur `E:`. Les pages `?page=documentation&country=bf|ne` n'ont pas été consultées (WebFetch non appelé sur ces pages faute de temps) ; à faire si on veut compléter.
- Certitude : [OFFICIEL ECOHADA], sans valeur pour le protocole. Le Bénin est mélangé au Niger dans ces PDF : mecef/emecef = Bénin.

## 4. Document béninois « MECeF_MCF_SFE_Protocole_v2.pdf »

- Non téléchargé : recherche web sans résultat, CDX Wayback sans résultat pour `*MECeF_MCF_SFE*`.
- Seule trace : le pilote Go (section 4c) cite ce nom dans un commentaire de `lib/request.go` (« MECeF_MCF_SFE_Protocole_v2.pdf »), donc le document existe et sa trame est celle décrite ci-dessous.

### 4a. C# `scorp-gitcontainer/mecef` — BÉNIN, version ancienne du protocole

- Dépôt : https://github.com/scorp-gitcontainer/mecef (copie locale `externe/docs/scorp_mecef/`)
- sha256 : CommandString_v4.cs `67db8239434b3927d0936302c0e1ad366f938a403f52ac4cda197d5bcdb34755` ; CoreEngine.V9.cs `a64dd121d4d5e6b3d15267d95a0f15c6c099086980ab38922ef34536296dbf7d` ; ExceptionString.cs `341aa5707fbf9083ec77e13dd329ac1e6e1cd7301183583d9149bfa7227bbc77` ; README.md `2e873edcb653b9eec8b69ca55f21c9181f4d45477ded9b4a6223fe7b4d1d240b`
- Certitude : [CODE TIERS], protocole béninois d'origine (4 groupes de taxe A B C D).
- Codes : `0xC1` état, `0xC2` serveur, `0x2B` info contribuable, `0xC0`, `0x31`, `0x33`, `0x35`, `0x38`. Pas de C3.
- **C0** (`cmdDebutFacture`) : `$"{numoperateur},{opnom},{ifu},{TAXA},{TAXB},{TAXC},{TAXD}"` puis `,{typeFactureV}` (FV, CV) ou `,{typeFactureR},{serialnumber}` (FR avec référence obligatoire), puis, si les trois sont renseignés, `,{customerIFU},{customerName},{AIB}`. Nom d'opérateur tronqué à 32. Constantes : types `FV`, `CV`, `FR` ; AIB `""`, `AIB1`, `AIB2` ; `TAXC="0.00"`, `TAXD="18.00"`. Ce format a 4 taux, donc diffère du format Niger accepté par l'appareil burkinabè (sans taux).
- **31** (`cmdAddArticle`) : `$"{nomArticle}{nomArticleComplement}\t{TaxAorB}{PriceTTC}"` + `*{Quantite}` si présente + `;{TaxeSpec}` si présente. `nomArticle` tronqué à 30 caractères ; le complément (30 max) est précédé d'un `\n` (0Ah). Séparateur nom/prix : TAB (`\t`) ; la lettre du groupe de taxe est collée au prix.
- **33** : aucune donnée (message de 4 octets).
- **35** : aucune donnée dans ce code (`buildMessage(4, 1, commandData, "")`), donc pas de moyens de paiement.
- **38** : aucune donnée.
- Réponses : décodées dans une autre classe, non publiée ici. Messages `E:` : absents (`ExceptionString.cs` ne contient que des messages d'erreur applicatifs en français).

### 4b. Java `cresshounnoukon/mcf-invoice-reform-api` — BÉNIN

- Dépôt : https://github.com/cresshounnoukon/mcf-invoice-reform-api (copie locale `externe/docs/java_mcf/`, 13 fichiers sous `src/main/java/tech/omeganumeric/sfe/`)
- sha256 : MecefService.java `27772ba12394a4baad9ca9fbef69b58342a34c10a956728fa05db2e9f7619f5e` ; OpenSellInvoiceRequest.java `389fab0ef6bb3bad4fea12f52e718572e11a6014d9432c3e7d5baef3fcf59b53` ; Item.java `057e786d660fd01fce4e3a0d47b3670ee31ef46266db510085fc62f6bafbe47c` ; Client.java `27a23e28d838206f75a667d365f0ba559aa4377d070f9aadfd345a01ee593cb9` ; MecefReference.java `6bf86f6cf786ea813023914613a360d15af8e47f5902cccae944b72794bacc3e` ; CloseInvoiceResponse.java `755dd9a983247c6d8e121c749903e722edd74e8d3c92aec4aac0173f9f9a3849` ; SubTotalResponse.java `083f09651159e3a58ffa062488cfe98914e8c25cce1e73fdbcd27637a4162589` ; OpenInvoiceResponse.java `f2015b02bc22162f8bbc391f1de19812b0f304a665805d5572f05c2bea07fecd` ; MCFServerResponse.java `b97cd22f5d822977e93ee6e1b4dfec5e23b102b2f6466ee215786591493cf185` ; Payment.java `3f355a590f57cec6b713907889ce6c160865ebefae824ae574c72cd4ef3aed00` ; Utils.java `49c9d237a81cc8e25b2e0138a98b13eaf14e6642ae62220097db8ab5ea615ed0` ; CommandRunnner.java `a1c29b70972b5d4b93675d77ead3c29c78db6c3887acd437d4e1c308eeed0b6c` ; Action.java `09baf8e0b603b467fb068296ee38b98ee55a258590dd9a7e2c673bfdfbdb0fd4`
- Certitude : [CODE TIERS], Bénin.
- **C0** : `operator.convertToString() + "," + ifu + "," + taxGroupString + "," + typeInvoice` + `"," + mecefReference` si non vide + `"," + ifuClient + "," + nomClient` si client + `"," + aib` si AIB. `taxGroupString` = valeurs de config séparées par des virgules. Le client est donc passé dans C0 (`ifu,nom`), sans commande C3.
- **31** (`Item.convertToString`) : `"[ " + code + " ]" + nom` (accents retirés, majuscules), puis `" \t"`, puis `groupeTaxe + prix + "*" + quantité`, puis, si taxe spécifique > 0, `";" + quantité*taxeSpécifique + ","`. Exemple construit : `[ P01 ]SAC DE RIZ \tB5000*2.0`. Prix entiers.
- Échappements (`Utils.replaceSpeciacharAccordingMecef`) : `,` -> `^x2c;`, `<` -> `^lt;`, `>` -> `^gt;`, `&` -> `^amp;`, `\r` -> `^xa;`. Utile : la virgule est interdite dans les noms.
- **33** : sans donnée. Réponse découpée par `,` : `[0]` total facture ; `[1]..[6]` sous-totaux groupes A à F ; `[7]..[12]` montants de taxe A à F ; `[13]` total AIB ; `[14]` total taxe spécifique.
- **35** : envoyée sans donnée dans ce code (mode CONFIRM), réponse ignorée. Pas de paiements ici.
- **38** : sans donnée. Réponse découpée par `,` : `[0]` compteur factures de vente ; `[1]` compteur total ; `[2]` type de facture ; `[3]` date `yyyyMMddHHmmss` ; `[4]` NIM (n° appareil) ; `[5]` IFU ; `[6]` signature. QR reconstruit : `"F;" + NIM + ";" + signature + ";" + IFU + ";" + date`. Signature affichée en groupes de 4/5 : tirets insérés aux positions 4, 9, 14, 19, 24.
- Réponse de C0 : `compteurVentes,compteurTotal[,erreur]` (2 ou 3 champs). Réponse de C2 : `nbEnvoyés,nbDocuments,dateDernierContact(yyyyMMddHHmmss),erreur`.

### 4c. Go `issotina/eltrade-cc300-driver` — BÉNIN (Eltrade CC300), sources 2020

- Dépôt : https://github.com/issotina/eltrade-cc300-driver (copie locale `externe/docs/eltrade_go/`)
- sha256 : app.go `4617a9b0575022413aa0eeff7aaa7e4f871a3a9aa607dff41ae9aefac1478091` ; request.go `ecd4a6d885a86ddfda44f4c4fc900435cc4f28f11535498dfe3c20eec74274de` ; response.go `6effa07bae83fd4c2eaf2dd6cad8cf32b196bfc2bb2afe3e9d788eb135bf67bf` ; device.go `25383718e5d255c267de5d187eb6b191ae3bd8a87c1fc5e25a7b0f785cf270ed` ; bill.go `f6f028c90cdf45772fa02befdd01fdeaacc00c166fe8c181e1c96cba5e0fe8df` ; bill.spec.json `50245bde8489098e027d78b11fe416c5a4b7579714e3b0727fb2d857953b8d33` ; Readme.md `8d6a35e8fb2ca6e48e7cc17b2d5c032ef2da706a6653792fa2436e9c6300c034`
- Certitude : [CODE TIERS], Bénin. Seule source qui montre les paiements.
- Trame : requête `<01><LEN><SEQ><CMD><DATA><05><BCC><03>`, LEN = 0x24 + longueur des données, SEQ de 0x20 à 0xFF, données <= 200 octets. Réponse `<01><LEN><SEQ><CMD><DATA><04><STATUS><05><BCC><03>` ; NAK 0x15, SYN 0x16.
- **C0** (séparateur `,` via `Append`) : `idVendeur,nomVendeur,IFU,TaxA,TaxB,TaxC,TaxD,VT,RT,RN,IFUacheteur,nomAcheteur[,AIB]` (AIB omis si « N/A »). Les taux viennent de la lecture d'état C1. Ordre vérifié dans `app.go` lignes 121-137. Détection d'erreur : la réponse contient `E:`.
- **31** : `label` [+ `"\n"+codeBarre`] + `\t` + `groupeTaxe` + `prix` (`%f`) + `*` + `quantité` (`%f`) [+ `;taxeSpécifique` + description] [+ `\t prixOriginal` + `,` + explication du changement de prix].
- **33** : commentaire `TODO: call 33h` : non utilisé.
- **35** : une commande par moyen de paiement : `{mode}{montant}` (`%s%f`), répétée jusqu'à 2 fois ; arrêt quand la réponse commence par `R`. Modes (bill.spec.json) : `V` virement, `C` carte bancaire, `M` mobile money, `D` chèque, `E` espèces, `A` autre. Exemple construit : `E1000.000000`.
- **38** : données vides en pratique (réutilise la dernière chaîne, bug probable). Réponse >= 7 champs séparés par `,` ; QR = `F;` + champ[4] + `;` + champ[6] + `;` + champ[5] + `;` + champ[3], ce qui confirme l'ordre du Java : [3] date, [4] NIM, [5] IFU, [6] signature. Exemple du Readme : `F;<NIM 10 car.>;<signature 24 car.>;<IFU 13 chiffres>;<AAAAMMJJhhmmss>`.
- Réponse de l'info (README) : NIM, IFU, TIME, COUNTER, SellBillCounter, SettlementBillCounter, TaxA..D, nom/adresse/ville/téléphone/email société, LastConnectionToServer, DocumentOnDeviceCount, UploadedDocumentCount.
- Types de facture (`rt`) : exemple `FA`; non listés.

## 5. Synthèse pour C3 et les erreurs

- **C3** : aucune des sources ne l'utilise ni ne le cite. Dans le code béninois, le client passe dans C0 (`ifu,nom`). Le champ « type de destinataire » (CC/PM/PP/PC) vient donc uniquement de l'observation de l'appareil ; rien de public trouvé ne le confirme. [aucune source]
- **Erreurs `E:`** : seule trace, la détection `strings.Contains(res, "E:")` après C0 (Go). Aucun catalogue de codes.
- **Hypothèses [DEDUCTION]** à tester sur l'appareil : (a) 31 : même forme que Bénin `nom\tGROUPE+prix*quantité;taxe` ; (b) 35 : `{mode}{montant}` avec modes V/C/M/D/E/A, mais le Niger/BF peuvent avoir d'autres codes ; (c) réponse de 38 : `compteurVentes,compteurTotal,type,date,NIM,IFU,signature`, et au Niger le nombre de champs ou leur ordre peut différer (le Bénin v2 ajoute des champs selon le Go qui exige >= 7).

## 6. Pistes restantes

1. Retrouver l'URL exacte du guide nigérien de la veille (son sha256 n'est pas dans le dépôt) et le placer dans `externe/docs/`.
2. Consulter `https://www.ecohada.com/?page=documentation&country=bf` et `country=ne` (non fait).
3. Chercher d'autres pilotes SECeF/MECeF sur GitHub contenant « C3 » (recherche de code GitHub nécessite une connexion).
