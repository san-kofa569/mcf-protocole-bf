# Exécution d'ECOHADA MCF CLI et lecture du calcul de l'article (2026-10-10)

Accord de l'opérateur (2026-10-10) : exécution sous Wine, isolée. Aucune donnée réelle : faux MCF à valeurs fictives.

## Bac à sable

`simulateur/bac_a_sable.sh` : bwrap, système en lecture seule, dossier personnel et `appareil/brut/` masqués,
`externe/wine/` seul en écriture, aucun réseau (seul `lo`). Prouvé par 5 tests et 3 contre-épreuves
(retrait de l'isolation réseau, du masquage du dossier personnel, du masquage des captures : chaque fois le
test tombe). Écran : un Xvfb privé lancé hors du bac (`:77`, sans TCP), dont seule la prise entre
(`SAB_ECRAN=:77`) ; Xvfb ne démarre pas dans le bac (erreur de segmentation).

## Obstacles levés

1. Sans pilote d'affichage, l'application Qt plante (c0000409) : elle crée une fenêtre.
2. Lecteur `Z:` supprimé : Wine ne trouve plus le dossier du CLI, Qt ne trouve plus son module
   « windows » et ouvre une boîte de dialogue qui attend un clic : blocage silencieux. Remède : lecteur
   `E:` limité à `externe/wine/`. La sortie du CLI est retenue en tampon tant qu'il tourne : `script -q -c`
   la rend visible.
3. COM1 : la clé `HKLM\Software\Wine\Ports` (COM1 = esclave du pty) est la seule qui tienne ; le lien posé
   à la main dans `dosdevices` est écrasé au démarrage.

## Liaison série : cause et remède (levés le 2026-10-10 au soir)

ECOHADA envoyait C1 et le faux MCF répondait, mais Qt ne voyait rien arriver (« Aucune reponse »).
Trace `WINEDEBUG=+comm` : à chaque `WaitCommEvent(EV_RXCHAR)`, `async_wait_proc` lit les lignes modem
(`TIOCMGET`). Un pty n'en a pas (ENOTTY) : Wine abandonne l'attente (« get_modem_status failed ») et
Qt n'est jamais prévenu de l'arrivée des octets. L'écriture, elle, n'en dépend pas.

Remède : `simulateur/modem_pty.c`, cale `LD_PRELOAD` compilée en i386 et x86_64 par `simulateur/cale.py`,
sans multilib (aucun en-tête système, liée à la libc de chaque architecture). Quand un terminal répond
ENOTTY à TIOCMGET/TIOCMSET/TIOCMBIS/TIOCMBIC, elle renvoie CTS, DSR et CD levés et DTR/RTS réglables.
Tout autre appel, et un vrai port série, passent tels quels. Piège : le `ntdll.so` i386 de Wine 10
(Debian) est compilé avec `time_t` 64 bits et importe `__ioctl_time64`, pas `ioctl`. La cale exporte
les deux.
Preuves : 6 tests (`tests/test_cale.py`, dont un témoin sans cale qui renvoie ENOTTY) ; 2 contre-épreuves
(sans le test « est-ce un terminal », sans les lignes levées : les tests attendus tombent) ; témoin
système `essai_ecohada --sans-cale` : « Aucune reponse » à nouveau.
Écran : 127 captures de l'écran virtuel pendant la matrice, toutes noires. Wine crée 6 à 8 fenêtres Qt
cachées, sans boîte de dialogue.

## Facture complète en exécution (NE)

Ordre émis par ECOHADA : C1 → C3 → C0 → 31 (une par article) → 36 (un par commentaire) → 33 → 35 → 38.
Le 35 n'est envoyé que si le sous-total est acceptable. Dans le cas contraire, et même après un C0
refusé, ECOHADA envoie quand même 38 (une facture sans paiement donne 6 champs, « annulée », selon
fcn.0040bee0).

Seuils de réponse relus au désassembleur (`sete` = égalité stricte) : C1 = 10 ou 29 champs ; C3 = 1 ;
**C0 = 7 exactement** ; **31 = 5 exactement** ; 33 ≥ 9 (`jl`) ; 35 commence par `R` ; 38 = 7 (validée)
ou 6 (annulée). Le découpage garde les champs vides. Un C0 à 8 champs (`1,3,,,,,,`, la réponse
transcrite de l'appareil le 2026-10-09) fait échouer ECOHADA : « Impossible de soumettre une facture ».
Il faut recompter cette réponse lundi sur une trame brute.

Contrôle du sous-total (fcn.00415a10, 0x415b32-0x415b6e) : acceptable si |champ 0 du 33 − total du CSV|
≤ tolérance. La tolérance vient de l'attribut `tolerance` d'`app.xml`. Quand elle vaut 0, ECOHADA prend
un cumul fait ligne par ligne à la lecture du CSV (0x428438, `addsd` en 0x4126cb) [D : probablement la
somme des quantités ; cas `decimales` : écart 0,25 accepté, cas `ts_ttc` : écart 10 refusé].
Total attendu du MCF : Σ TTC + colonne 7 (« TS ») + ISB (taux de la clé C0 appliqué au TTC de chaque
ligne : A = 2 %, B = 5 %). Le faux MCF ne calcule pas l'ISB ; `taux_a`, `taux_b` et `ts_ht` s'arrêtent
donc au 33.

## Matrice de variantes (boucle 004)

`simulateur/bac_a_sable.sh python3 -m simulateur.matrice` : 18 variantes, valeurs fictives, résumé complet
dans `externe/wine/essais/matrice.md` (hors dépôt, régénérable). Toutes les trames sont reproduites par
`appareil/formats.py` (`tests/test_formats.py`, classe `TemoinsExecution`).

| variante | ce qu'ECOHADA envoie |
|---|---|
| TTC de base | `31 ARTICLE UN\tB18.0%2360\t1180*2` ; `35 E2860` |
| HT | `C0 …,FV,HT,…` ; `31 ARTICLE UN\tB18.0%2000\t1000*2` : prix et montant HT |
| taxe spécifique, TTC | `31 …\tB18.0%2370\t1180*2;T50,59` : montant + col. 7 (10) ; `;T<col 5>,<col 6>` |
| taxe spécifique, HT | `31 …\tB18.0%2059\t1000*2;T50,59` : montant HT + col. 6 (59), col. 7 ignorée |
| client avec IFU | `C3 9999999999999,Societe Essai,PM,Adresse Essai,Contact Essai` |
| client vide | `C3 ,,,,` (envoyé quand même) |
| clé de taux A / B | C0 terminé par `,A` / `,B` ; console « Taux ISB 2 % / 5 % » |
| paiement M / X | `35 M2860` / `35 A2860` (mode inconnu → A) |
| décimales | `31 ARTICLE DEC\tB18.0%1499\t1000*1.5` : prix arrondi, quantité brute |
| régime vide | B si la ligne a de la TVA, sinon A |
| échappement | `CAFÉ^x2c; l essai ^amp; ^lt;test^gt;` ; `É` envoyé en Latin-1 (`C9`) |
| commentaire `#;A;texte` | `36 A,Commentaire essai`, après les 31, avant 33 ; clé hors A..H : rien |
| avoir | `C0 …,FA,XX99999999-3,TTC,…` : NIM-TC de la facture d'origine lu dans `mcf.s3db` |
| avoir, NIM-TC saisi | « Facture non retrouvee », valeur saisie envoyée telle quelle (elle contient `-`) |

## Calcul de l'article, lu dans le binaire

fcn.00411ea0, 0x4127cb-0x4128d1, quatre montants passés au constructeur de 31 :
F1 = round(PU TTC × qté + c7), F2 = round(PU HT × qté + c6), F3 = round(PU TTC), F4 = round(PU HT)
(round du C, puis `%.0f`). fcn.004096b0 : en mode TTC, prix = F3 et montant après `%` = F1 ; en HT,
F4 et F2 (`cmove` en 0x409701 et 0x40972d). Le montant après `%` est donc le total de la ligne, taxe
spécifique comprise. L'essai 5 du 2026-10-09 envoyait `%0` : écart expliqué.
Reproduction testée : `appareil/formats.py`, 13 tests dont un témoin (le C0 accepté par l'appareil),
2 contre-épreuves (montant = taxe seule, arrondi bancaire : les tests tombent).

## Suite

Plan de lundi : `docs/plan_essais_2026-10-12.md` (complété par les seuils et témoins ci-dessus).
