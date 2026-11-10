#!/usr/bin/env bash
# Vault-wachtwoord uit de macOS-sleutelhanger (voor --vault-password-file). Eenmalig instellen:
#   security add-generic-password -a "$USER" -s volvo-api-client-ansible-vault -w
# (vraagt het wachtwoord; niets hiervan komt in de repo).
exec security find-generic-password -a "$USER" -s volvo-api-client-ansible-vault -w
