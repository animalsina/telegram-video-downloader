#!/bin/sh

# Funzione per ottenere la versione corrente dal repository
get_current_version() {
  git fetch --tags
  VERSION=$(git describe --tags --abbrev=0 2>/dev/null)
  if [ -z "$VERSION" ]; then
    VERSION="v2.0.0"  # Versione di default
  fi
  echo "$VERSION"
}

# Funzione per incrementare la versione in base ai commit (fix o feat)
increment_version() {
  VERSION_NO_V=$(echo "$1" | sed 's/^v//')

  MAJOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 1)
  MINOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 2)
  PATCH=$(echo "$VERSION_NO_V" | cut -d '.' -f 3)

  LAST_COMMIT_MSG=$(git log -1 --pretty=%B)

  if echo "$LAST_COMMIT_MSG" | grep -iq "fix:"; then
    PATCH=$((PATCH + 1))
  elif echo "$LAST_COMMIT_MSG" | grep -iq "feat:"; then
    MINOR=$((MINOR + 1))
    PATCH=0  # Reset il PATCH se si aumenta il MINOR
  fi

  echo "v$MAJOR.$MINOR.$PATCH"
}

# Controlla che la branch corrente sia "V2"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" != "V2" ]; then
  echo "Not on V2 branch. Skipping version increment and tag push."
  exit 0
fi

# Ottieni la versione corrente e incrementa la versione
CURRENT_VERSION=$(get_current_version)
echo "Current version: $CURRENT_VERSION"

NEW_VERSION=$(increment_version "$CURRENT_VERSION")
echo "New version: $NEW_VERSION"

# Verifica che il formato della versione sia corretto
if ! echo "$NEW_VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Invalid version format: $NEW_VERSION, exiting."
  exit 1
fi

# Se la nuova versione è diversa da quella corrente
if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
  git fetch origin

  # Unisci i cambiamenti dal ramo remoto se ci sono modifiche
  LOCAL_VS_REMOTE=$(git log HEAD..origin/V2 --oneline)
  if [ -n "$LOCAL_VS_REMOTE" ]; then
    echo "There are changes on the remote branch. Merging remote changes before committing."
    git merge origin/V2
  fi

  # Aggiorna i file .last_version e README.md con la nuova versione
  sed -i "s/^version:.*/version: $NEW_VERSION/" .last_version
  echo "Updated .last_version file with the new version: $NEW_VERSION"

  sed -i "s/V [0-9]\+\.[0-9]\+\.[0-9]\+/V $NEW_VERSION/" README.md
  echo "Updated README.md with the new version: $NEW_VERSION"

  git add .last_version README.md
  git commit -m "Version: $CURRENT_VERSION -> $NEW_VERSION"

else
  echo "New version is the same as the current version, skipping tag push."
fi

exit 0
