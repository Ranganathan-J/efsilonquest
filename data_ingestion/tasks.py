from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import time
import logging
import random

logger = logging.getLogger(__name__)


# ==================== DAY 5: TEST TASKS ====================

@shared_task
def test_celery():
    """Simple test task to verify Celery is working"""
    logger.info("✅ Celery test task executed successfully!")
    return "Celery is working!"


@shared_task
def print_random_feedback():
    """
    Periodic task that prints a random feedback every 10 seconds.
    This is for Day 5 testing.
    """
    from data_ingestion.models import RawFeed
    
    try:
        # Get random feedback
        feedback = RawFeed.objects.order_by('?').first()
        
        if feedback:
            preview = feedback.text[:100] + '...' if len(feedback.text) > 100 else feedback.text
            logger.info(f"""
            ==================== PERIODIC FEEDBACK ====================
            ID: {feedback.id}
            Entity: {feedback.entity.name}
            Source: {feedback.source}
            Text: {preview}
            Status: {feedback.status}
            ===========================================================
            """)
            return f"Printed feedback #{feedback.id}"
        else:
            logger.info("No feedbacks found in database")
            return "No feedbacks available"
            
    except Exception as e:
        logger.error(f"Error in print_random_feedback: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def add_numbers(a, b):
    """Simple math task for testing"""
    result = a + b
    logger.info(f"Addition: {a} + {b} = {result}")
    return result


@shared_task
def long_running_task(duration=10):
    """Task that takes some time to complete"""
    logger.info(f"Starting long task ({duration} seconds)...")
    time.sleep(duration)
    logger.info("Long task completed!")
    return f"Completed after {duration} seconds"


# ==================== DAY 6-7: FEEDBACK PROCESSING ====================

@shared_task(bind=True, max_retries=3)
def process_feedback(self, feedback_id):
    """
    Main task to process a single feedback.
    
    This task:
    1. Updates status to 'processing'
    2. Performs AI analysis (placeholder for now)
    3. Creates ProcessedFeedback record
    4. Updates status to 'processed'
    
    Args:
        feedback_id: ID of the RawFeed to process
    """
    from data_ingestion.models import RawFeed
    from analysis.models import ProcessedFeedback
    
    start_time = time.time()
    
    try:
        # Get the raw feedback with lock
        raw_feed = RawFeed.objects.select_for_update().get(id=feedback_id)
        
        logger.info(f"📝 Processing feedback #{feedback_id}")
        
        # Update status to processing
        raw_feed.status = 'processing'
        raw_feed.save(update_fields=['status'])
        
        # ==================== PLACEHOLDER AI ANALYSIS ====================
        # For now, we'll use simple placeholder logic
        # In Week 2, we'll replace this with real AI models
        
        # Simulate processing time
        time.sleep(2)
        
        # Simple sentiment analysis (placeholder)
        text_lower = raw_feed.text.lower()
        
        # Determine sentiment based on keywords
        positive_words = ['great', 'excellent', 'amazing', 'love', 'perfect', 'good', 'best']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'poor', 'disappointed']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            sentiment_score = min(0.6 + (positive_count * 0.1), 0.95)
        elif negative_count > positive_count:
            sentiment = 'negative'
            sentiment_score = min(0.6 + (negative_count * 0.1), 0.95)
        else:
            sentiment = 'neutral'
            sentiment_score = 0.5
        
        # Extract simple topics (placeholder)
        topics = []
        if 'delivery' in text_lower:
            topics.append('delivery')
        if 'quality' in text_lower or 'product' in text_lower:
            topics.append('product_quality')
        if 'price' in text_lower or 'cost' in text_lower:
            topics.append('pricing')
        if 'service' in text_lower or 'support' in text_lower:
            topics.append('customer_service')
        
        if not topics:
            topics = ['general']
        
        # Simple embeddings (placeholder - just random numbers)
        embeddings = [random.random() for _ in range(10)]
        
        # Generate simple summary
        summary = raw_feed.text[:150] + '...' if len(raw_feed.text) > 150 else raw_feed.text
        
        # Key phrases (placeholder)
        key_phrases = topics[:3]
        
        # ==================== END PLACEHOLDER ====================
        
        processing_time = time.time() - start_time
        
        # Create or update ProcessedFeedback record
        with transaction.atomic():
            processed, created = ProcessedFeedback.objects.update_or_create(
                raw_feed=raw_feed,
                defaults={
                    'sentiment': sentiment,
                    'sentiment_score': sentiment_score,
                    'topics': topics,
                    'embeddings': embeddings,
                    'summary': summary,
                    'key_phrases': key_phrases,
                    'processing_time': processing_time,
                    'model_version': 'placeholder_v1.0'
                }
            )
            
            # Update raw feed status
            raw_feed.status = 'processed'
            raw_feed.processed_at = timezone.now()
            raw_feed.save(update_fields=['status', 'processed_at'])
        
        logger.info(
            f"✅ Processed feedback #{feedback_id} in {processing_time:.2f}s "
            f"- Sentiment: {sentiment} ({sentiment_score:.2f})"
        )
        
        return {
            'status': 'success',
            'feedback_id': feedback_id,
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'topics': topics,
            'processing_time': processing_time
        }
        
    except RawFeed.DoesNotExist:
        logger.error(f"❌ RawFeed #{feedback_id} not found")
        return {'status': 'error', 'message': 'Feedback not found'}
        
    except Exception as e:
        logger.error(f"❌ Error processing feedback #{feedback_id}: {str(e)}")
        
        # Update status to failed
        try:
            raw_feed = RawFeed.objects.get(id=feedback_id)
            raw_feed.status = 'failed'
            raw_feed.error_message = str(e)
            raw_feed.save(update_fields=['status', 'error_message'])
        except:
            pass
        
        # Retry the task with exponential backoff
        retry_delay = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
        raise self.retry(exc=e, countdown=retry_delay)


@shared_task
def process_bulk_feedbacks(feedback_ids):
    """
    Process multiple feedbacks in bulk.
    
    Args:
        feedback_ids: List of RawFeed IDs to process
    """
    logger.info(f"📦 Processing bulk upload: {len(feedback_ids)} feedbacks")
    
    results = {
        'total': len(feedback_ids),
        'queued': 0,
        'failed': 0,
        'task_ids': []
    }
    
    for feedback_id in feedback_ids:
        try:
            task = process_feedback.delay(feedback_id)
            results['task_ids'].append({
                'feedback_id': feedback_id,
                'task_id': task.id
            })
            results['queued'] += 1
        except Exception as e:
            logger.error(f"Failed to queue feedback #{feedback_id}: {str(e)}")
            results['failed'] += 1
    
    logger.info(
        f"✅ Bulk processing queued: {results['queued']} success, "
        f"{results['failed']} failed"
    )
    
    return results


@shared_task
def process_pending_feedbacks():
    """
    Periodic task to process all pending (new) feedbacks.
    Runs every minute via Celery Beat.
    """
    from data_ingestion.models import RawFeed
    
    try:
        # Get all feedbacks with 'new' status
        pending = RawFeed.objects.filter(status='new')
        count = pending.count()
        
        if count == 0:
            logger.info("📭 No pending feedbacks to process")
            return {'status': 'success', 'processed': 0}
        
        logger.info(f"📬 Found {count} pending feedbacks")
        
        # Queue each for processing
        queued = 0
        for feedback in pending[:100]:  # Process max 100 at a time
            try:
                process_feedback.delay(feedback.id)
                queued += 1
            except Exception as e:
                logger.error(f"Failed to queue feedback #{feedback.id}: {str(e)}")
        
        logger.info(f"✅ Queued {queued} feedbacks for processing")
        
        return {
            'status': 'success',
            'found': count,
            'queued': queued
        }
        
    except Exception as e:
        logger.error(f"❌ Error in process_pending_feedbacks: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def reprocess_failed_feedbacks():
    """
    Retry processing all failed feedbacks.
    Can be called manually or scheduled.
    """
    from data_ingestion.models import RawFeed
    
    try:
        failed = RawFeed.objects.filter(status='failed')
        count = failed.count()
        
        if count == 0:
            logger.info("No failed feedbacks to reprocess")
            return {'status': 'success', 'reprocessed': 0}
        
        logger.info(f"🔄 Reprocessing {count} failed feedbacks")
        
        # Reset status and queue for processing
        reprocessed = 0
        for feedback in failed:
            feedback.status = 'new'
            feedback.error_message = None
            feedback.save(update_fields=['status', 'error_message'])
            
            process_feedback.delay(feedback.id)
            reprocessed += 1
        
        logger.info(f"✅ Queued {reprocessed} failed feedbacks for reprocessing")
        
        return {
            'status': 'success',
            'reprocessed': reprocessed
        }
        
    except Exception as e:
        logger.error(f"Error in reprocess_failed_feedbacks: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_feedbacks():
    """
    Periodic task to clean up old processed feedbacks.
    Runs daily at 2 AM via Celery Beat.
    """
    from data_ingestion.models import RawFeed
    
    try:
        # Delete feedbacks older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        
        old_feedbacks = RawFeed.objects.filter(
            status='processed',
            processed_at__lt=cutoff_date
        )
        
        count = old_feedbacks.count()
        
        if count > 0:
            old_feedbacks.delete()
            logger.info(f"🗑️ Cleaned up {count} old feedbacks")
        else:
            logger.info("No old feedbacks to clean up")
        
        return {
            'status': 'success',
            'deleted_count': count
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_feedbacks: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def generate_daily_report():
    """
    Generate daily statistics report.
    Can be scheduled to run daily.
    """
    from data_ingestion.models import RawFeed, BusinessEntity
    from analysis.models import ProcessedFeedback
    from django.db.models import Count, Avg
    
    try:
        today = timezone.now().date()
        
        # Get today's statistics
        today_feedbacks = RawFeed.objects.filter(created_at__date=today)
        
        report = {
            'date': today.isoformat(),
            'total_feedbacks': today_feedbacks.count(),
            'by_status': dict(
                today_feedbacks.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')
            ),
            'by_source': dict(
                today_feedbacks.values('source').annotate(
                    count=Count('id')
                ).values_list('source', 'count')
            ),
            'average_rating': today_feedbacks.aggregate(
                avg=Avg('rating')
            )['avg'] or 0,
        }
        
        # Get sentiment breakdown
        today_processed = ProcessedFeedback.objects.filter(
            processed_at__date=today
        )
        
        report['sentiment_breakdown'] = dict(
            today_processed.values('sentiment').annotate(
                count=Count('id')
            ).values_list('sentiment', 'count')
        )
        
        logger.info(f"📊 Daily Report Generated: {report}")
        
        return {
            'status': 'success',
            'report': report
        }
        
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        return {'status': 'error', 'message': str(e)}