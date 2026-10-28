# Plan d'attaque du protocole FIS-NANO (2026-10-12)

Point de départ : C0 est connu (format Niger accepté). 31 (article) et C3 (client) refusent toutes les formes
essayées (recherche/2026-10-12_essais_appareil.md). Aucun document public ne décrit le protocole burkinabè.
On ne devine plus forme par forme : on change de méthode.

## Découverte qui change tout : le FIS-NANO est un terminal Android

Journal du noyau au branchement (2026-10-12, lecture passive, aucune trame) :

- USB `05c6:9018`, fabricant « QUALCOMM », produit « FIS-NANO » au démarrage puis « QCM2150-QRD ».
  QCM2150 = puce Qualcomm pour terminaux Android d'entrée de gamme ; « QRD » = conception de référence Qualcomm.
- Périphérique USB composite : interface 2 = stockage de masse (« Linux File-Stor Gadget », sans support),
  interface 4 = port série CDC ACM (`/dev/ttyACM0`, le port A du MCF). Interfaces 0, 1 et 3 : non liées à un
  pilote du PC, rôle inconnu (diagnostic Qualcomm, ADB, modem ?).
- Datamega : « Android fiscal POS », Android 7.1 personnalisé (manuel Éthiopie, help.datamega.tech).

Conséquence : le « MCF » est une application Android. Le format exact de 31 et de C3 est écrit dans son code.
Le lire = connaître le protocole à l'octet, messages d'erreur compris, sans essai à l'aveugle.

## Les pistes, de la plus décisive à la plus lente

### P1. Lire l'application du MCF (décisive)

1. Passif, sans trame (accord de l'opérateur, appareil branché) : décrire les interfaces USB
   `lsusb -v -d 05c6:9018 | grep -E "bInterface(Number|Class|SubClass|Protocol)|iInterface"`.
   Une interface de classe `ff`, sous-classe `42`, protocole `01` = ADB (pont de débogage Android).
2. Si ADB est présent (accord de l'opérateur ; l'appareil affiche une demande d'autorisation, l'opérateur l'accepte ou non) :
   lecture seule, `adb shell pm list packages -3`, `adb shell pm path <paquet>`, `adb pull <apk> externe/fisnano/`.
   Rien n'est installé, modifié ni effacé sur l'appareil ; la mémoire fiscale n'est pas touchée.
3. Analyse statique hors appareil (jadx), dans `externe/` (empreinte notée), sans réseau, jamais exécutée :
   chercher les chaînes déjà vues (« Erreur de type de destinataire », « Aucune donnée valide… »), remonter au
   code qui découpe les données de 31 et de C3.
   But : interopérabilité (faire parler un logiciel de facturation au MCF), pas contourner une sécurité.

Si ADB est absent ou refusé : P2 et P3.

**Résultat du 2026-10-12, 16:06 (`lsusb -v`, lancé par l'opérateur, lecture des descripteurs seulement)** : configuration
USB nommée `acm_tty`, 6 interfaces.

| Interface | Classe | Rôle probable |
|---|---|---|
| 0 | `ff/ff/30`, 2 bulk | diagnostic Qualcomm (DIAG) |
| 1 | `ff/00/00`, 1 interrupt + 2 bulk, descripteurs CDC | port série du fabricant (modem 4G ?) |
| 2 | `08/06/50` | stockage de masse (vide) |
| 3 | `ff/00/00`, comme 1 | second port série du fabricant |
| 4, 5 | CDC ACM « CDC Serial » | port A du MCF (`/dev/ttyACM0`) |

**Pas d'interface ADB** (`ff/42/01`) : la copie de l'application par USB est fermée dans cette configuration.
Le port DIAG et les ports du modem ne sont pas des pistes : ils parlent à la puce radio, pas à l'application
fiscale, et le DIAG Qualcomm permet d'écrire dans l'appareil. Refusé.
Reste, sans rien changer : regarder sur l'écran du MCF ce qu'Android laisse voir (nom et version de
l'application fiscale, « À propos de l'appareil ») pour chercher une mise à jour publique de cette application.

### P2. Sondes par saturation (quelques trames, une à la fois, lancées par l'opérateur)

Idée : au lieu de deviner la place d'un champ, remplir toutes les places à la fois. Si le message d'erreur
CHANGE, une étape du contrôle a été franchie et l'appareil nous dit laquelle.

| Sonde | Données | Ce qu'elle dit |
|---|---|---|
| `c3_s1_cc_partout_5` | `CC,CC,CC,CC,CC` | le type `CC` est-il accepté à l'une des 5 places ? |
| `c3_s2_un_partout_5` | `1,1,1,1,1` | même question pour le numéro `1` |
| `c3_s3_cc_partout_8` | `CC` × 8 | C3 burkinabè à plus de champs (IFU, RCCM, nom, tél., adresse, e-mail : §2.14) ? |
| `c3_s4_cc_seul` | `CC` | un client comptant se réduit-il au seul type ? |
| `a31_s1_virgules` | `ARTICLE TEST,B18.0%100,100*1` | séparateur virgule (comme C0 et C3) au lieu de tabulation ? |
| `a31_s2_datecs_decimales` | `ARTICLE TEST⇥B100.00*1.000` | prix et quantité à décimales (§6.1 : 2 et 3 chiffres) ? |
| `a31_s3_nom_seul` | `ARTICLE TEST` | message d'un article vide de tout : référence pour lire les autres |

Ordre : C3 (hors facture ouverte, sinon NAK), puis C0, puis les sondes 31. Chaque sonde est d'abord rejouée sur
le jumeau (`--variante FIS`) pour vérifier la trame. Arrêt dès qu'un message nouveau apparaît : on raffine
autour de lui au lieu de continuer la liste.

### P3. Ceux qui savent déjà

- Le premier logiciel burkinabè homologué (communiqué de presse du 2026-10-05) : son éditeur parle déjà au MCF.
- Des cabinets forment des acteurs à la conformité (presse, 2026-05-02).
- Le fournisseur du FIS-NANO (demande de documentation préparée, hors dépôt).
- Le comité d'homologation de la DGI (note 2025-0889 : le protocole est « défini par l'Administration », §2.1.8).

### P4. Le jumeau (fait le 2026-10-12)

`simulateur/faux_mcf.py --variante FIS` rend exactement ce que l'appareil a répondu, et `E:?? cas jamais observé`
pour tout le reste. Sert à : répéter chaque sonde avant l'appareil, développer un client série contre un MCF
fidèle, et savoir d'un coup d'œil ce qu'on ignore encore. Chaque réponse nouvelle de l'appareil y entre, avec
son test.

## Garde-fous (inchangés)

Aucune trame ni commande ADB sans accord de l'opérateur ; une à la fois ; aucun geste irréversible (activation,
personnalisation, réinitialisation, mise à jour, installation sur l'appareil). Logiciel tiers dans `externe/`,
empreinte notée, jamais exécuté sans isolation réseau.
