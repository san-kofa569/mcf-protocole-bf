#!/bin/sh
# Lance une commande sous bwrap pour exécuter un logiciel tiers sans risque :
# système en lecture seule, dossier personnel masqué, code du projet en lecture,
# captures réelles masquées, externe/wine/ seul en écriture, aucun réseau.
set -eu
PROJET=$(cd "$(dirname "$0")/.." && pwd)
W="$PROJET/externe/wine"
mkdir -p "$W/home"
# Écran virtuel facultatif : SAB_ECRAN=:77 fait entrer la seule prise d'un Xvfb privé.
ECRAN=""
if [ -n "${SAB_ECRAN:-}" ]; then
  N=${SAB_ECRAN#:}
  ECRAN="--ro-bind /tmp/.X11-unix/X$N /tmp/.X11-unix/X$N --setenv DISPLAY :$N"
fi
# shellcheck disable=SC2086
exec bwrap \
  --ro-bind / / \
  --tmpfs "$HOME" \
  --ro-bind "$PROJET" "$PROJET" \
  --tmpfs "$PROJET/appareil/brut" \
  --bind "$W" "$W" \
  --dev /dev --proc /proc --tmpfs /tmp --tmpfs /run --perms 1777 --dir /tmp/.X11-unix --tmpfs /dev/shm \
  --unshare-all --die-with-parent --new-session \
  --clearenv \
  --setenv PATH /usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  --setenv HOME "$W/home" --setenv LANG C.UTF-8 --setenv USER ans \
  --setenv XDG_RUNTIME_DIR /tmp \
  --setenv WINEPREFIX "$W/prefix" --setenv WINEDEBUG -all \
  --setenv WINEDLLOVERRIDES "mscoree,mshtml=" \
  $ECRAN \
  --chdir "$PROJET" "$@"
