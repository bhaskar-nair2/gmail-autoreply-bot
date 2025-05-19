gcloud functions deploy gmail-agent-processor-polling \
  --gen2 \
  --runtime python312 \
  --region us-central1 \
  --source . \
  --entry-point process_scheduled_email_check \
  --env-vars-file env.yaml \
  --timeout 540s \
  --service-account gmail-bot-sa@vraie-3a692.iam.gserviceaccount.com \
  --memory 512MiB \
