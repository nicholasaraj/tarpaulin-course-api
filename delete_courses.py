from google.cloud import datastore

client = datastore.Client()
query = client.query(kind='courses')
for entity in query.fetch():
    print(f"Deleting course {entity.key.id}")
    client.delete(entity.key)
