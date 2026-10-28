# Piste « APK EazSell » et clôture du SDK ECOHADA (2026-10-16)

But : trouver la 31 par tous les moyens ; session du 16 octobre consacrée à la voie « lire le code de
l'appareil » (plan d'attaque du 2026-10-12, P1). Aucune trame envoyée, aucun geste sur l'appareil.

## 1. Balayage web : l'app EazSell n'est pas publique

- `help.datamega.tech` = GitBook, un seul espace : le manuel Fis-NANO **Éthiopie** (7 chapitres). Pas de
  téléchargement. Le manuel décrit l'appareil utilisé comme **caisse fiscale complète** (ventes, PLU,
  départements, S mode...) : une autre configuration que notre « MCF pur ».
- **Découverte utile (manuel Éthiopie §3.7.2, « Connect to PC »)** : un logiciel PC **PC MANAGER** dialogue
  avec l'appareil par câble Micro USB **ou Wi-Fi** (« Use Micro USB cable... or open device WIFI... Click PC
  Connection switch to open it, then the PC MANAGER communication with device is connected »). Son manuel
  (« refer to related user manual of PC MANAGER ») est livré à part. Notre tableau de bord EazSell BF
  affiche « Connexion PC → Connecté » quand nous parlons au port : c'est très probablement le même canal.
  => **À demander au fournisseur avec l'appareil** : le logiciel PC MANAGER et son manuel. Ils documentent
  le dialogue PC ↔ appareil, donc une partie du protocole, peut-être au-delà de ce qu'ECOHADA connaît.
- `www.datamega.net` (corporate, Xiamen DataMega Technology Co., Ltd) : section Download = 1 PDF
  (DP-300, imprimante). Page produit Fis-NANO → lien « Fiscal Application only » :
  `eazsell.datamega.net` = **placeholder non publié** (Pineapple Builder). Les instantanés Wayback 2024-04
  et 2025-04 de ce domaine = site marketing (pas d'APK, pas de protocole).
- `eazsell.net` et `bf.eazsell.net` (2026) : sites marketing de l'éditeur **DataMega Technology** lui-même.
  `bf.eazsell.net` : guides FEC Burkina (lancement FEC 6 janvier 2026, obligation 1er juillet 2026) ;
  « l'intégration SFE/MCF doit être testée avec un partenaire local et confirmée par la DGI ; EazSell n'est
  pas présenté comme déjà homologué ». Pas d'APK. Contact public sur le site de DataMega.
- Stores : rien sur Google Play ; APKPure ne donne que des homonymes (EasySell, SalesPlay...) ; GitHub
  (recherche dépôts) : rien pour `eazsell` ni `datamega` en fiscal.
- Conclusion : l'application fiscale EazSell **n'est pas téléchargeable publiquement**. Elle est préchargée
  ou distribuée par le MDM DataMega (« DCloud »). La voie « mise à jour publique » est fermée tant que
  DataMega (ou le fournisseur local) ne répond pas.

## 2. SDK ECOHADA 23.0827 : analysé, rien pour la série (ferme la voie)

Le SDK était déjà extrait dans `externe/ecohada/x_sdk/app` (empreintes dans docs/EXTERNE.md). Ses outils
n'avaient pas été lus :

- `MCF.exe` (console, **wxWidgets 3.1.7 + libcurl**, pas Qt) : orchestrateur. Chaînes : « Impossible de
  joindre le serveur MCF: », `serveurMCF`, `transfererSortie`, `MCF-CLI "`, `MCF-Print "`, `.mcf"`.
  Il lance MCF-CLI et MCF-Print et parle à un serveur HTTP. Aucun protocole série propre.
- `MCF-Config.exe` (Qt) : éditeur graphique « Configuration ECOHADA MCF API » (logo, filtres, IFU,
  jeton e-MCF) : un éditeur d'app.xml.
- `MCF-Print.exe` (Qt) : mise en page du ticket à partir du fichier `.mcf` (Caissier, Carte Bancaire,
  Code client, Bon de commande...).
- `MCF-CLI.exe` du SDK (sha256 `64ad1ec5…`, cf. EXTERNE.md) : mêmes chaînes de protocole que le CLI
  23.04081 déjà cartographié (différence = certificats de signature seulement). Toujours deux variantes :
  BJ (10 champs C1) et NE (29 champs) — pas de Burkina.
- Les « Burkina » trouvés dans les binaires = tables de locales wxWidgets (« French (Burkina Faso) ») :
  faux positifs.

Conclusion : l'ensemble ECOHADA (CLI, Server, SDK) ne connaît que Bénin et Niger. La 31 burkinabè
d'EazSell ne s'y trouve pas. **Voie ECOHADA fermée.**

## 3. Ce qui reste pour trouver la 31 (état consolidé)

1. **Demander** (voie officielle, note 2025-0885 §2.2 f) :
   - à l'acquisiteur du MCF : les documents reçus avec l'appareil ;
   - au fournisseur (lettre préparée, hors dépôt, mise à jour ce jour) :
     protocole SFE-MCF BF, formats 31/33/35/38, commande d'annulation, **et le logiciel PC MANAGER avec
     son manuel** ;
   - à DataMega en dernier recours ;
   - aux éditeurs BF homologués et au comité d'homologation DGI.
2. **Lire l'application** (décisif) : activer le débogage USB depuis l'écran du MCF (Paramètres →
   options développeur ; réversible, accord de l'opérateur) puis `adb pull` de l'APK EazSell en lecture seule,
   analyse statique (jadx) hors appareil. ADB absent de la config USB actuelle, mais Android 10 montre
   les options développeur. Variante sans geste : l'export EazSell de la base des ventes (dossier
   `EAZSell`, 0 reçu pour l'instant) — donne la structure des articles, pas la trame.
3. **Sondes structurelles** (séance appareil, une à la fois) : 36 (commentaire ECOHADA : `A,texte`),
   2B `I5` et suivants, commandes voisines 30/32/34/37 — chercher un message nouveau qui renseigne le
   style du Burkina.

Garde-fous inchangés : aucune trame sans accord de l'opérateur ; aucun geste irréversible ; logiciels tiers
dans `externe/`, jamais exécutés sans isolation réseau ni accord.

## 4. Voie ADB : fermée par l'écran (2026-10-16, 16:11 heure MCF)

- Paramètres → « About device » : sept appuis ouvrent une fenêtre d'usine DataMega (« notice — Please select
  the test software you want to open » : **PRODUCTION TEST / AGING TEST**), pas les options pour les
  développeurs. Fenêtre fermée sans rien choisir (tests d'usine = risque sur un appareil activé).
- Identité logicielle relevée : micrologiciel `V1.1.58_BF_20260717.115015` (image Burkina, compilée le
  17 juillet 2026), « Custom build » `FIS-NANO_V1.0.0`, noyau `4.9.218-perf` (6 juillet 2026, CST).
- Recherche web du numéro de micrologiciel : aucun paquet de mise à jour public.
- Conclusion : pas d'APK ni d'image à analyser ; on ne contourne pas le verrou. Retour aux sondes
  structurelles (§3.3) : 2B `I5`, puis 36 `A,ESSAI` hors facture puis dans une facture ouverte.
  Charges utiles : `appareil/essais/sondes/s2b_i5.txt`, `s36_a_essai.txt`, `c0_facture_6.txt`.

## 5. Sondes série du 16 octobre soir (18:25–18:34, facture ESSAI-0006 ouverte, une trame à la fois, lancées par l'opérateur)

Captures : `appareil/brut/2026-10-16_sondes.txt` (hors dépôt).

| seq | Trame | Réponse |
|---|---|---|
| 70 | 2B `I5` | NAK, statut `a1` (nouveau ; `a2` pour C3 en facture) |
| 71, 73 | 36 `A,ESSAI` sans facture | `E:La commande C0 doit être soumise en premier` |
| 72 | C0 avec l'IFU littéral `XXXXXXXXX` (erreur de manipulation) | `E:La valeur IFU ne correspond pas`, rien d'ouvert |
| 74 | C0 `ESSAI-0006` | `1,3,,,,,,` (facture ouverte) |
| 75 | 36 `A,ESSAI` | **`R`** |
| 76 | 36 `ESSAI` | `E:Aucune donnée valide n'a été reçue` |
| 77 | 36 `Z,ESSAI` | idem |
| 78 | 36 `A,ESSAI,X` | idem |
| 79 | 33 | `E:Veuillez ajouter le produit en premier.` (point final : nouveau) |

Conclusions : la 36 burkinabè = forme ECOHADA NE (`clé,texte`). C'est la première commande de ligne acceptée.
Sa structure fautive donne « Aucune donnée valide », pas le message de format de la 31.
**La facture ESSAI-0006 reste ouverte** (C1 pour l'annuler).
Jumeau mis à jour (36, 2B I5, point final du 33) ; 168 tests.

Prochaine expérience : contrôle du point final (C1, C0, 33 sans 36). Puis 31 en gabarit « 36 » : `clé,texte` à deux champs,
dont le premier est une lettre et le second un texte libre, en variant la clé de A à P.
