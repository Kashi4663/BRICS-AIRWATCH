# Deploy BRICS AIRWATCH on Google Cloud Run

1. Create a project at https://console.cloud.google.com and link a billing account.
2. Get a Gemini API key at https://aistudio.google.com/apikey
3. Open **Cloud Shell** (the `>_` icon, top right). Upload the zip (⋮ menu → Upload), then:

```
unzip brics_airwatch.zip && cd brics_airwatch
gcloud run deploy brics-airwatch --source . --region asia-south1 --allow-unauthenticated --max-instances 1 --memory 1Gi --set-env-vars "GEMINI_API_KEY=PASTE_KEY,DJANGO_SECRET_KEY=any-long-random-text"
```
Answer **Y** to enabling APIs / creating the Artifact Registry repository. After 3–5 minutes it prints the live URL
(https://brics-airwatch-xxxxx.asia-south1.run.app).

Optional LIVE services (add to --set-env-vars or edit the service → Variables):
- GOOGLE_TRANSLATE_API_KEY — enable "Cloud Translation API", create an API key (APIs & Services → Credentials)
- VERTEX_PROJECT_ID, VERTEX_ENDPOINT_ID — deployed Vertex AI model endpoint
- EARTH_ENGINE_PROJECT, BIGQUERY_PROJECT_ID, FIREBASE_PROJECT_ID

Update after code changes: run the same `gcloud run deploy` command again.

Note: the demo database (SQLite) is recreated from the demo dataset each time the container starts;
`--max-instances 1` keeps every visitor on the same data. Use Cloud SQL for persistent storage.
