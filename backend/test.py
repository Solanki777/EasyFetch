from googleapiclient.discovery import build
import google.auth

SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]

creds, project = google.auth.default(scopes=SCOPES)

service = build("drive", "v3", credentials=creds)

results = service.files().list(
    pageSize=10,
    fields="files(id, name, mimeType)"
).execute()

files = results.get("files", [])

print("\nFILES:\n")

for f in files:
    print(f"{f['name']}  |  {f['mimeType']}")