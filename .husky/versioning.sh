#!/bin/sh

# Funzione per ottenere la versione attuale
get_current_version() {
  git fetch --tags
  VERSION=$(git describe --tags --abbrev=0 2>/dev/null)
  if [ -z "$VERSION" ]; then
    VERSION="v2.0.0"  # Versione di default
  fi
  echo "$VERSION"
}

# Funzione per calcolare la nuova versione basata sull'ultimo commit
increment_version() {
  VERSION_NO_V=$(echo "$1" | sed 's/^v//')

  MAJOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 1)
  MINOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 2)
  PATCH=$(echo "$VERSION_NO_V" | cut -d '.' -f 3)

  # Ottieni l'ultimo commit
  LAST_COMMIT_MSG=$(git log -1 --pretty=%B)

  # Incrementa il PATCH se c'è un fix
  if echo "$LAST_COMMIT_MSG" | grep -iq "fix:"; then
    PATCH=$((PATCH + 1))
  # Incrementa il MINOR se c'è una nuova feature
  elif echo "$LAST_COMMIT_MSG" | grep -iq "feat:"; then
    MINOR=$((MINOR + 1))
    PATCH=0  # Reset il PATCH se si aumenta il MINOR
  fi

  echo "v$MAJOR.$MINOR.$PATCH"
}

# Ottieni la versione attuale
CURRENT_VERSION=$(get_current_version)
echo "Current version: $CURRENT_VERSION"

# Calcola la nuova versione
NEW_VERSION=$(increment_version "$CURRENT_VERSION")
echo "New version: $NEW_VERSION"

# Controlla il formato della versione
if ! echo "$NEW_VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Invalid version format: $NEW_VERSION, exiting."
  exit 1
fi

# Crea il tag
git tag "$NEW_VERSION"
echo "Tag $NEW_VERSION created."

# Push dei tag senza innescare Husky
git push --tags --no-verify
echo "Tags pushed without triggering Husky."
