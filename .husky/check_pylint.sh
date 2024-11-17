#!/bin/sh

exit_if_error() {
  if [ $? -ne 0 ]; then
    echo "Error occurred, exiting."
    exit 1
  fi
}

# Version checked
PYTHON_VERSIONS="3.9 3.10 3.11 3.12"

INSTALLED_PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)

if echo "$PYTHON_VERSIONS" | grep -q "$INSTALLED_PYTHON_VERSION"; then
  echo "Verifying Python $INSTALLED_PYTHON_VERSION with pylint..."

  git ls-files '*.py' | xargs pylint
  exit_if_error
else
  echo "Python $INSTALLED_PYTHON_VERSION is not in the allowed versions list ($PYTHON_VERSIONS), skipping. Or add the version in list and check if that is valid!"
  #exit 1
  git ls-files '*.py' | xargs pylint
  exit_if_error
fi

echo "Pylint check completed."
