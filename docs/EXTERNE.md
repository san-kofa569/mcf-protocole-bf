# Logiciels et documents tiers (rangés dans `externe/`, hors dépôt)

Téléchargés le 2026-10-10. Jamais exécutés hors d'une isolation réseau et sans accord.

| Fichier | Source | sha256 |
|---|---|---|
| `ecohada/mcfcli/ECOHADA_MCF_CLI_23.04081.zip` | https://www.ecohada.com/download?app=mcfcli | `b70f767b173c4dccb273c0caeb572df1f8941ec2959d6daa1a06d7012fac5770` |
| `ecohada/mcfserver/ECOHADA_MCF_Server_23.04081.exe` | https://www.ecohada.com/download?app=mcfserver | `e1958ca40165289a8a399551ca07f73c08448191c003942159e56edb2d422ddd` |
| `ecohada/mcfsdk/ECOHADA_MCF_SDK_23.0827.exe` | https://www.ecohada.com/download?app=mcfsdk | `030b461c50841e5b1697224ff853335f77ddb313faf2a3b1ce5d3fd22a4b26c8` |

Page source : https://www.ecohada.com/?page=dev&country=bf (mêmes versions que pour le Niger et le Bénin).
Extraction : `unzip` (CLI), `innoextract` (Server, SDK). Le Server n'est qu'un `index.php` qui écrit
`input.csv`, lance `MCF-CLI.exe` et renvoie `input.csv.mcf`. Les trois `MCF-CLI.exe` diffèrent :

| Copie | sha256 |
|---|---|
| CLI | `6d629a6eae4b85d622bfb1dfacd8e762ee551ed83616c3517fc68284924f1015` |
| Server | `3dc763b4499423c5c77b1fb9e4cb3e87acfdc50ca18095be210353cd3d8115ba` |
| SDK | `64ad1ec59d213b1e8c89dec93a04937342f58efbb1b490feb5c46c0427bdc9c9` |

Outils du SDK lus le 2026-10-16 (`recherche/2026-10-16_apk_eazsell_et_sdk.md`) : `MCF.exe` = orchestrateur
wxWidgets + libcurl (HTTP, lance MCF-CLI et MCF-Print) ; `MCF-Config.exe` = éditeur d'app.xml ;
`MCF-Print.exe` = mise en page du ticket `.mcf`. Le `MCF-CLI.exe` du SDK a les mêmes chaînes de protocole
que le 23.04081 cartographié ; ECOHADA ne connaît que BJ/NE, pas le Burkina.

## Documents (`externe/docs/`)

| Fichier | Source | sha256 |
|---|---|---|
| `manuel-mcf.pdf` (2 p., 2020, Bénin) | https://www.ecohada.com/pdf/manuel-mcf.pdf | `d89f06dd2903b78ede69b6d13bf55b261c88db52fb05e95d3cf7ecf183588fb8` |
| `ecohada_secef.pdf` | https://www.ecohada.com/pdf/ecohada_secef.pdf | `2ad6193daaf00042d18b666242abb7dad3b365f23b5627fdc5acdd4b7debe914` |
| `ecohada_mecef.pdf` | https://www.ecohada.com/pdf/ecohada_mecef.pdf | `e161c01730a3a35a54711bc2cdbfba623e8651f9fa3ab071eb2d1e21a006687f` |
| `ecohada_emecef.pdf` | https://www.ecohada.com/pdf/ecohada_emecef.pdf | `1cf8fab2bb8b35fe8f2424351f86b320286294fb8e7325131a262eabf2d00ca1` |
| `ecohada.pdf` | https://www.ecohada.com/pdf/ecohada.pdf | `4bddf4c650fbd9e7715876cac3e646b1c7226c1a38bcddaa97ea3ebb1934f4ad` |
| `ne_circ75_spec_mcfuf.pdf` (1 p. scannée, lettre d'envoi) | web.archive.org 20210909130322, impots.gouv.ne/media/telech/CircN°75-241220202-SPEC-MCFUF.pdf | `983d26fa71a7380f3a966c7e6549e48c3eeb822a3cab327558e7d04a2d84d9eb` |
| `ne_circ74_spec_sfe.pdf` (1 p. scannée, lettre d'envoi) | web.archive.org 20210909130313, impots.gouv.ne/media/telech/CircN°74-241220202-SPECSFE.pdf | `2f94b900369cd88ba72400ef6efc4915b6821ebadb26af714783012b0b1996b7` |

Code tiers béninois copié pour lecture (`scorp_mecef/`, `java_mcf/`, `eltrade_go/`) : empreintes dans
`recherche/2026-10-10_documents_protocole.md`.
