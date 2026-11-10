#!/usr/bin/env bash
# Gebruik: ./deploy.sh install|deploy|update|rollback [extra ansible-playbook opties]
#   install   server inrichten (venv, gebruiker, mappen, config, systemd-timer, volvo-authenticate),
#             oude cron weghalen + tokens.json overnemen, en eerste deploy
#   deploy    huidige lokale code uitrollen als nieuwe release (+ één run als controle)
#   update    python3 en de pip-afhankelijkheden bijwerken
#   rollback  terug naar vorige release (of: rollback -e release=<id>)
# Opnieuw inloggen bij Volvo ID (interactief) doe je op de server: volvo-authenticate
# Vault-wachtwoord: uit de macOS-sleutelhanger als dat is ingesteld (zie vault-pass.sh),
# anders wordt het gevraagd. ANSIBLE_VAULT_PASSWORD_FILE of eigen vault-opties gaan voor.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

cmd="${1:-}"
case "$cmd" in
  install|deploy|update|rollback) shift ;;
  *) sed -n '2,10p' "$0" >&2; exit 1 ;;
esac

if [ "$cmd" = deploy ] || [ "$cmd" = install ]; then
  (cd .. && python3 -c "import ast,sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]" \
     volvo_battery_mqtt.py authenticate.py volvo_api/*.py)
fi

vault=()
if [ -f group_vars/all/vault.yml ] && [ -z "${ANSIBLE_VAULT_PASSWORD_FILE:-}" ] \
   && ! printf '%s\n' "$@" | grep -q -- '--ask-vault-pass\|--vault-password-file'; then
  if command -v security >/dev/null && ./vault-pass.sh >/dev/null 2>&1; then
    vault=(--vault-password-file ./vault-pass.sh)
  else
    vault=(--ask-vault-pass)
  fi
fi

exec ansible-playbook "$cmd.yml" "${vault[@]+"${vault[@]}"}" "$@"
