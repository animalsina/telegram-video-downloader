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

# Funzione per calcolare la nuova versione
increment_version() {
  VERSION_NO_V=$(echo "$1" | sed 's/^v//')

  MAJOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 1)
  MINOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 2)
  PATCH=$(echo "$VERSION_NO_V" | cut -d '.' -f 3)

  COMMITS=$(git log --oneline --no-merges)
  FEAT_COUNT=$(echo "$COMMITS" | grep -i "feat:" | wc -l)
  FIX_COUNT=$(echo "$COMMITS" | grep -i "fix:" | wc -l)

  if [ "$FEAT_COUNT" -gt 0 ]; then
    MINOR=$((MINOR + 1))
    PATCH=0  # Resetta la patch se aumenta il minor
  fi

  PATCH=$((PATCH + FIX_COUNT))

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

# Aggiungi una variabile di ambiente per evitare loop
if [ "$GIT_PUSH_TAG" != "true" ]; then
  git push --tags
  echo "Tags pushed."
  export GIT_PUSH_TAG=true
fi