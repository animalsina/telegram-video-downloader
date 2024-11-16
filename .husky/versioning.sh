#!/bin/sh

get_current_version() {
  VERSION=$(git describe --tags --abbrev=0 2>/dev/null)

  if [ -z "$VERSION" ]; then
    VERSION="v2.0.0" # Default version to start
  fi

  echo "$VERSION"
}

increment_version() {
  VERSION_NO_V=$(echo "$1" | sed 's/^v//')

  MAJOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 1)
  MINOR=$(echo "$VERSION_NO_V" | cut -d '.' -f 2)
  PATCH=$(echo "$VERSION_NO_V" | cut -d '.' -f 3)

  COMMIT_MSG=$(git log -1 --pretty=%B)

  if echo "$COMMIT_MSG" | grep -iq "feat"; then
    MINOR=$((MINOR + 1))
    PATCH=0  # Reset patch version
  elif echo "$COMMIT_MSG" | grep -iq "fix"; then
    PATCH=$((PATCH + 1))
  elif echo "$COMMIT_MSG" | grep -iq "breaking"; then
    MAJOR=$((MAJOR + 1))
    MINOR=0  # Reset minor version
    PATCH=0  # Reset patch version
  else
    echo "Commit type not detected, defaulting to PATCH increment."
    PATCH=$((PATCH + 1))
  fi

  echo "v$MAJOR.$MINOR.$PATCH"
}

CURRENT_VERSION=$(get_current_version)
echo "Current version: $CURRENT_VERSION"

NEW_VERSION=$(increment_version "$CURRENT_VERSION")
echo "New version: $NEW_VERSION"

if ! echo "$NEW_VERSION" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "Invalid version format: $NEW_VERSION, exiting."
  exit 1
fi

git tag "$NEW_VERSION"
echo "Tag $NEW_VERSION created."

echo "Commit with tag $NEW_VERSION created."
