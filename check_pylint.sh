#!/bin/bash

# Elenco delle versioni di Python da controllare
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12")

# Controlla pylint per ogni versione di Python
for version in "${PYTHON_VERSIONS[@]}"; do
  echo "Verifying Python $version with pylint..."

  # Verifica se la versione di Python è installata
  if command -v python$version &>/dev/null; then
    python$version -m pylint --errors-only . || exit 1
  else
    echo "Python $version is not installed, skipping."
  fi
done

echo "Pylint check passed for all versions."
