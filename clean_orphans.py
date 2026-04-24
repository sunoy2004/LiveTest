import codecs
import json
import subprocess

wallets = codecs.open('wallets.txt', 'r', 'utf-16').read().split()
users = codecs.open('users.txt', 'r', 'utf-16').read().split()

wallet_uuids = [w for w in wallets if '-' in w and len(w)==36]
user_uuids = [u for u in users if '-' in u and len(u)==36]

missing = list(set(wallet_uuids) - set(user_uuids))

if missing:
    in_clause = ', '.join([f"'{m}'" for m in missing])
    ledger_cmd = f'docker compose exec -T postgres psql -U postgres -d gamification_db -c "DELETE FROM ledger_transactions WHERE user_id IN ({in_clause});"'
    wallet_cmd = f'docker compose exec -T postgres psql -U postgres -d gamification_db -c "DELETE FROM wallets WHERE user_id IN ({in_clause});"'
    
    subprocess.run(ledger_cmd, shell=True)
    subprocess.run(wallet_cmd, shell=True)
    print('Deleted', len(missing), 'orphaned wallets and ledger transactions.')
else:
    print('No missing found.')
