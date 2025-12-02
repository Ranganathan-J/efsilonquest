# AI-Powered Feedback Analysis System - Setup Guide

## Overview
This system ingests customer feedback from multiple sources, analyzes it using AI (sentiment analysis, topic extraction), and generates actionable insights.

## Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Redis 7+
- Git

## Quick Start

### 1. Clone and Setup Virtual Environment

```bash
git clone <your-repo-url>
cd <project-directory>

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your credentials
# REQUIRED: Set DJANGO_SECRET_KEY, database credentials, API keys
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb ai_feedback_db

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Start Services

**Option A: Using Docker Compose (Recommended)**

```bash
docker-compose up -d
```

**Option B: Manual Start**

Terminal 1 - Django:
```bash
python manage.py runserver
```

Terminal 2 - Celery Worker:
```bash
celery -A core worker -l info
```

Terminal 3 - Celery Beat (for scheduled tasks):
```bash
celery -A core beat -l info
```

### 5. Access the Application

- API: http://localhost:8000
- Admin Panel: http://localhost:8000/admin
- API Documentation: http://localhost:8000/swagger/

## Initial Data Setup

### Create a Business Entity

```bash
python manage.py shell
```

```python
from data_ingestion.models import BusinessEntity

entity = BusinessEntity.objects.create(
    name="Acme Corp",
    description="Main business entity"
)
print(f"Created entity with ID: {entity.id}")
```

### Load Sample Feedback

```bash
cd data_ingestion
python ingest.py
```

## API Usage

### 1. Authentication

**Register a User:**
```bash
curl -X POST http://localhost:8000/api/users/signup/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst",
    "email": "analyst@example.com",
    "password": "SecurePass123",
    "role": "analyst"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst",
    "password": "SecurePass123"
  }'
```

Save the `access` token for subsequent requests.

### 2. Submit Single Feedback

```bash
curl -X POST http://localhost:8000/api/data-ingestion/feedbacks/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": 1,
    "text": "The product quality is excellent but delivery was slow.",
    "source": "website",
    "product_name": "SmartPhone X",
    "rating": 4
  }'
```

### 3. Bulk Upload CSV

```bash
curl -X POST http://localhost:8000/api/data-ingestion/bulk-upload/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@feedback.csv" \
  -F "entity_id=1" \
  -F "source=csv"
```

### 4. Get Statistics

```bash
curl -X GET "http://localhost:8000/api/data-ingestion/statistics/?entity_id=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. List Feedbacks with Filters

```bash
# Get all feedbacks for an entity
curl -X GET "http://localhost:8000/api/data-ingestion/feedbacks/?entity_id=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by status
curl -X GET "http://localhost:8000/api/data-ingestion/feedbacks/?status=processed" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Filter by rating
curl -X GET "http://localhost:8000/api/data-ingestion/feedbacks/?min_rating=4" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Search in text
curl -X GET "http://localhost:8000/api/data-ingestion/feedbacks/?search=battery" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## CSV File Format

Your CSV should have these columns:

```csv
text,source,product_name,customer_name,rating
"Great product, highly recommend!",website,SmartPhone X,John Doe,5
"Delivery was late",twitter,SmartPhone X,,2
```

**Required columns:**
- `text` or `feedback_text` or `feedback` - The feedback content

**Optional columns:**
- `source` - Where the feedback came from
- `product_name` - Product being reviewed
- `customer_name` - Customer who gave feedback
- `rating` - Rating from 1-5

## Configuration

### AI/ML Settings

Edit `core/settings.py` or set in `.env`:

```python
# Use OpenAI (requires API key)
OPENAI_API_KEY=your-key-here

# Or use HuggingFace (free, runs locally)
HUGGINGFACE_API_KEY=your-key-here  # Optional
```

### Celery Settings

Adjust task limits in `core/settings.py`:

```python
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_TRACK_STARTED = True
```

## Monitoring

### Check Celery Tasks

```bash
# View active tasks
celery -A core inspect active

# View registered tasks
celery -A core inspect registered

# View task stats
celery -A core inspect stats
```

### Check Database

```bash
python manage.py shell
```

```python
from data_ingestion.models import RawFeed, BusinessEntity
from analysis.models import ProcessedFeedback, Insight

# Check counts
print(f"Entities: {BusinessEntity.objects.count()}")
print(f"Raw Feeds: {RawFeed.objects.count()}")
print(f"Processed: {ProcessedFeedback.objects.count()}")
print(f"Insights: {Insight.objects.count()}")

# Check processing status
from django.db.models import Count
status_counts = RawFeed.objects.values('status').annotate(count=Count('id'))
print(status_counts)
```

## Troubleshooting

### Issue: Celery tasks not running

**Solution:**
1. Ensure Redis is running: `redis-cli ping` (should return "PONG")
2. Check Celery worker is running
3. Check logs: `celery -A core worker -l debug`

### Issue: Database connection errors

**Solution:**
1. Verify PostgreSQL is running
2. Check credentials in `.env`
3. Test connection: `psql -U postgres -d ai_feedback_db`

### Issue: AI processing fails

**Solution:**
1. Check API keys are set correctly
2. Install AI dependencies: `pip install torch transformers sentence-transformers`
3. Check logs for specific errors

### Issue: Migration errors

**Solution:**
```bash
# Delete all migrations (except __init__.py)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Recreate migrations
python manage.py makemigrations
python manage.py migrate
```

## Production Deployment

### Environment Variables to Set

```bash
ENV=production
DEBUG=False
DJANGO_SECRET_KEY=generate-secure-key
DATABASE_URL=postgresql://...
CELERY_BROKER_URL=redis://...
ALLOWED_HOSTS=yourdomain.com
```

### Run Migrations

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Start with Gunicorn

```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## Next Steps

1. **Set up frontend dashboard** - Connect to the API endpoints
2. **Configure email alerts** - Set EMAIL_* variables in settings
3. **Add more data sources** - Extend ingestion for Twitter, Reddit APIs
4. **Customize AI models** - Fine-tune models for your specific domain
5. **Set up monitoring** - Use Sentry, Prometheus, or similar tools

## Support

For issues or questions:
- Check the logs: `logs/django.log`
- Review Swagger docs: http://localhost:8000/swagger/
- Check Celery status: `celery -A core inspect stats`
