# Pistes sur le protocole SFE-MCF (recherche du 2026-10-08)

Hors dépôt. Hypothèses à confirmer par un document officiel ou par l'appareil, jamais à coder telles quelles.

## 1. Où sont les accès : la plateforme GDSECeF
- Gestion de distribution SECeF (DGI + CCI-BF) : https://dgi.bf/ventesecef/ (demande : /demande, connexion : /connexion,
  mot de passe oublié : /mot-de-passe/oublie). Connexion par adresse e-mail + mot de passe (compte créé à la demande
  d'acquisition). Types d'acquéreur : éditeur de logiciel de facturation (MCF), client d'éditeur homologué (MCF),
  contribuable avec logiciel propre (MCF), contribuable sans logiciel (UF).
- C'est très probablement « leur site » où sont les accès de l'appareil et la documentation des éditeurs.

## 2. Textes publics DGI (officiel/, empreintes dans EMPREINTES.sha256)
- Notes 0885 (procédures), 0887 (SECeF), 0889 (SFE), comité d'homologation, trois arrêtés FEC. Protocole absent.
- 0885 §2.2 f : le fournisseur du MCF dépose guide d'installation, manuel d'utilisation, manuel d'ACTIVATION, logiciels.

## 3. Référence béninoise (système d'origine probable : même vocabulaire SECeF/MECeF, NIM, ISF, groupes A-P,
   types FV/FA/EV/EA, clients CC/PM/PP/PC)
Source : github.com/cresshounnoukon/mcf-invoice-reform-api (Java, 2024-03, MCF physique en série ; code lu, non exécuté,
copie dans le bloc-notes de session). Protocole de type « imprimante fiscale » (famille Datecs) :
- Trame : 01 | LEN = 0x20 + len(données) + 4 | SEQ (0x20..0xFE) | CMD | DONNÉES ASCII séparées par des virgules | 05 |
  BCC = somme des octets de LEN à 05, en 4 quartets + 0x30 | 03.
- Réponses : 15 (NAK) = renvoyer ; 16 (SYN) = attendre ; réponse terminée par 04 (puis statut, 05, BCC, 03).
- Commandes vues : C1 état (IFU, NIM?, date, compteurs, taux A-D) ; C2 serveur (envoyés, total, DATE DU DERNIER CONTACT
  AVEC LE SERVEUR, erreur) => SFE §2.31 ; 2B infos société (I0 nom commercial, I1 adresse, I2 ville, I3 tél, I4 email) ;
  C0 ouverture facture (opérateur, IFU, taux, type FV/FA..., référence de la facture d'origine, client, AIB) ;
  31 ajout d'article ; 33 sous-total ; 35 total ; 38 clôture => compteurs, type, date AAAAMMJJhhmmss, NIM, IFU, signature.
- Code MECeF/DGI = signature de 24 caractères, imprimée en 6 blocs de 4 séparés par des tirets.
- QR : "F;<NIM>;<signature>;<IFU>;<date AAAAMMJJhhmmss>".
- Équivalent burkinabè probable de l'AIB béninoise : PSVB (SFE §2.16).

## 4. À vérifier
- Le FIS-NANO (Android, LTE) parle-t-il ce protocole, et sur quel transport (USB CDC série, TCP sur le réseau local) ?
- Activation et personnalisation : qui, comment, réversibilité, mode d'essai.
- Un premier SFE burkinabè homologué (attestation de la DGI du 22/06/2026) : aucun détail technique public trouvé.
