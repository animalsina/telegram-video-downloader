#!/bin/sh

get_current_version() {
  git fetch --tags
  VERSION=$(git describe --tags --abbrev=0 2>/dev/null)
  if [ -z "$VERSION" ]; then
    VERSION="v2.0.0"  # Versione di default
  fi
  echo "$VERSION"
}

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

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" != "V2" ]; then
  echo "Not on V2 branch. Skipping version increment and tag push."
  exit 0
fi

CURRENT_VERSION=$(get_current_version)
echo "Current version: $CURRENT_VERSION"

NEW_VERSION=$(increment_version "$CURRENT_VERSION")
echo "New version: $NEW_VERSION"

if ! echo "$NEW_VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Invalid version format: $NEW_VERSION, exiting."
  exit 1
fi

if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
  git fetch origin

  LOCAL_VS_REMOTE=$(git log HEAD..origin/V2 --oneline)
  if [ -n "$LOCAL_VS_REMOTE" ]; then
    echo "There are changes on the remote branch. Merging remote changes before pushing."
    git merge origin/V2
  fi

  sed -i "s/^version:.*/version: $NEW_VERSION/" .last_version
  echo "Updated .last_version file with the new version: $NEW_VERSION"

  sed -i "s/V [0-9]\+\.[0-9]\+\.[0-9]\+/V $NEW_VERSION/" README.md
  echo "Updated README.md with the new version: $NEW_VERSION"

  git add .last_version README.md
  git commit -m "Version: $CURRENT_VERSION -> $NEW_VERSION"

  git push origin V2 --no-verify

  # Check if the tag already exists
  if git rev-parse "$NEW_VERSION" >/dev/null 2>&1; then
    echo "Tag $NEW_VERSION already exists, skipping tag creation."
  else
    # Generate tag
    git tag "$NEW_VERSION"
    echo "Tag $NEW_VERSION created."

    # Push tags without triggering Husky
    git push --tags --no-verify
    echo "Tags pushed without triggering Husky.."
  fi
else
  echo "New version is the same as the current version, skipping tag push."
fi
