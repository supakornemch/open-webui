#!/usr/bin/env python3
import psycopg2, json

conn = psycopg2.connect(
    host='psql-entchat-qas.postgres.database.azure.com',
    port=5432,
    dbname='open_webui',
    user='entchatadm',
    password='5gUFYZ!3jeCnAo',
    connect_timeout=15,
    sslmode='require'
)
cur = conn.cursor()

# 1. Update model base_model_id from nano to mini
cur.execute("""
    UPDATE model 
    SET base_model_id = 'genie.deploy-gpt-5.4-mini'
    WHERE id = 'procurement-price-assistant'
""")
print(f"Updated model procurement-price-assistant base_model_id: {cur.rowcount} row(s)")

# 2. Update function (Pipe) valves: LLM_MODEL = 'deploy-gpt-5.4-mini'
cur.execute("SELECT id, valves FROM function WHERE id = 'procurement_price_pipe'")
fid, valves_str = cur.fetchone()
valves = json.loads(valves_str) if isinstance(valves_str, str) else valves_str
valves['LLM_MODEL'] = 'deploy-gpt-5.4-mini'
cur.execute("UPDATE function SET valves = %s WHERE id = %s", (json.dumps(valves), fid))
print(f"Updated function procurement_price_pipe LLM_MODEL: {cur.rowcount} row(s)")

# 3. Enable and set context compaction at 50,000 tokens
cur.execute("UPDATE config SET value = %s WHERE key = 'chat.context_compaction.enable'", (json.dumps(True),))
cur.execute("UPDATE config SET value = %s WHERE key = 'chat.context_compaction.token_threshold'", (json.dumps(50000),))
cur.execute("UPDATE config SET value = %s WHERE key = 'chat.context_compaction.model'", (json.dumps("deploy-gpt-5.4-mini"),))
print("Updated context compaction config: enable=true, token_threshold=50000, model=deploy-gpt-5.4-mini")

conn.commit()

# Verify
print("\n--- Verification ---")
cur.execute("SELECT id, name, base_model_id FROM model WHERE id = 'procurement-price-assistant'")
print("Model:", cur.fetchone())

cur.execute("SELECT id, valves FROM function WHERE id = 'procurement_price_pipe'")
fid, v = cur.fetchone()
vd = json.loads(v) if isinstance(v, str) else v
print("Function valve LLM_MODEL:", vd.get('LLM_MODEL'))

cur.execute("SELECT key, value FROM config WHERE key LIKE 'chat.context_compaction%' ORDER BY key")
for r in cur.fetchall():
    print(f"Config: {r[0]} = {r[1]}")

conn.close()
