gcloud builds submit --tag gcr.io/cover-letter-ai-generator/cover-letter-ai-generator

gcloud run deploy cover-letter-ai-generator \
  --image gcr.io/cover-letter-ai-generator/cover-letter-ai-generator \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated