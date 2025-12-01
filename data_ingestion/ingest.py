import os
import django
import csv
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from data_ingestion.models import RawFeed, BusinessEntity

def ingest_csv(file_path, entity_name="Default Entity", source="csv"):
    entity, created = BusinessEntity.objects.get_or_create(name=entity_name)
    
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            text = row.get('text') or row.get('content')
            if text:
                RawFeed.objects.create(text=text, source=source, entity=entity)
                print(f"Ingested: {text[:50]}...")

if __name__ == "__main__":
    ingest_csv("feedback.csv", entity_name="Acme Corp")
