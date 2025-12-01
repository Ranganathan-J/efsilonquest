import os
import django
import csv
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from data_ingestion.models import RawFeed, BusinessEntity


def ingest_csv(file_path, entity_name="Default Entity", source="csv"):
    print(f"\n🚀 Starting ingestion from: {file_path}")
    print(f"🔍 Checking/creating BusinessEntity: {entity_name}")

    entity, created = BusinessEntity.objects.get_or_create(name=entity_name)

    if created:
        print(f"✅ Created new BusinessEntity: '{entity_name}'\n")
    else:
        print(f"ℹ️ Using existing BusinessEntity: '{entity_name}'\n")

    count = 0

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for index, row in enumerate(reader, start=1):

            text = row.get('feedback_text')

            if not text:
                print(f"⚠️ Row {index} skipped (no feedback_text column).")
                continue

            # Optional fields (only if your model supports them)
            product_name = row.get('product_name') or None
            customer_name = row.get('customer_name') or None
            rating = row.get('rating') or None
            timestamp = row.get('timestamp')

            # Convert timestamp string → datetime if needed
            if timestamp:
                try:
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except:
                    timestamp = None

            feed = RawFeed.objects.create(
                text=text,
                source=row.get('source') or source,
                entity=entity,
                product_name=product_name,
                customer_name=customer_name,
                rating=rating,
                timestamp=timestamp,
            )

            print(f"[Row {index}] Saved RawFeed(ID={feed.id})")
            print(f"   ➤ Text: {text[:80]}{'...' if len(text) > 80 else ''}")
            print(f"   ➤ Product: {product_name}")
            print(f"   ➤ Rating: {rating}")
            print(f"   ➤ Source: {row.get('source')}")
            print(f"   ➤ Timestamp: {timestamp}\n")

            count += 1

    print("🎉 Ingestion completed!")
    print(f"👉 Total rows ingested: {count}")


if __name__ == "__main__":
    ingest_csv("feedback.csv", entity_name="Acme Corp")
