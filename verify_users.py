from google.cloud import datastore

client = datastore.Client()
query = client.query(kind='users')

print("Verifying all user entities...")

for entity in query.fetch():
    key_id = entity.key.id
    sub = entity.get("sub")
    role = entity.get("role")
    print(f"User {key_id}: sub={sub}, role={role}")

    if sub is None or role is None:
        print(f"  ❌ MISSING FIELDS on user {key_id}")
