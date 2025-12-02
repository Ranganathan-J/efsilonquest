from celery import shared_task
from django.utils import timezone
from django.db import transaction
import time
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_raw_feedback(self, feedback_id):
    """
    Process a single raw feedback entry with AI analysis.
    
    This task:
    1. Updates status to 'processing'
    2. Performs sentiment analysis
    3. Extracts topics/keywords
    4. Generates embeddings
    5. Creates ProcessedFeedback record
    6. Updates status to 'processed'
    """
    from data_ingestion.models import RawFeed
    from analysis.models import ProcessedFeedback
    # from analysis.ai_processor import AIProcessor  # You'll create this
    
    start_time = time.time()
    
    try:
        # Get the raw feedback
        raw_feed = RawFeed.objects.select_for_update().get(id=feedback_id)
        
        # Update status
        raw_feed.status = 'processing'
        raw_feed.save(update_fields=['status'])
        
        logger.info(f"Processing feedback #{feedback_id}")
        
        # Initialize AI processor
        processor = AIProcessor()
        
        # Perform AI analysis
        sentiment_result = processor.analyze_sentiment(raw_feed.text)
        topics = processor.extract_topics(raw_feed.text)
        embeddings = processor.generate_embeddings(raw_feed.text)
        summary = processor.generate_summary(raw_feed.text)
        key_phrases = processor.extract_key_phrases(raw_feed.text)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create ProcessedFeedback record
        with transaction.atomic():
            processed_feedback = ProcessedFeedback.objects.create(
                raw_feed=raw_feed,
                sentiment=sentiment_result['label'],
                sentiment_score=sentiment_result['score'],
                topics=topics,
                embeddings=embeddings,
                summary=summary,
                key_phrases=key_phrases,
                processing_time=processing_time,
                model_version="v1.0"
            )
            
            # Update raw feed status
            raw_feed.status = 'processed'
            raw_feed.processed_at = timezone.now()
            raw_feed.save(update_fields=['status', 'processed_at'])
        
        logger.info(
            f"Successfully processed feedback #{feedback_id} "
            f"in {processing_time:.2f}s"
        )
        
        # Trigger insight generation if needed
        if sentiment_result['label'] == 'negative' and sentiment_result['score'] > 0.8:
            generate_insights.delay(processed_feedback.id)
        
        return {
            'status': 'success',
            'feedback_id': feedback_id,
            'sentiment': sentiment_result['label'],
            'processing_time': processing_time
        }
        
    except RawFeed.DoesNotExist:
        logger.error(f"RawFeed #{feedback_id} not found")
        return {'status': 'error', 'message': 'Feedback not found'}
        
    except Exception as e:
        logger.error(f"Error processing feedback #{feedback_id}: {str(e)}")
        
        # Update status to failed
        try:
            raw_feed = RawFeed.objects.get(id=feedback_id)
            raw_feed.status = 'failed'
            raw_feed.error_message = str(e)
            raw_feed.save(update_fields=['status', 'error_message'])
        except:
            pass
        
        # Retry the task
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def process_bulk_feedback(feedback_ids):
    """
    Process multiple feedback entries in bulk.
    
    Args:
        feedback_ids: List of RawFeed IDs to process
    """
    results = []
    
    for feedback_id in feedback_ids:
        result = process_raw_feedback.delay(feedback_id)
        results.append({
            'feedback_id': feedback_id,
            'task_id': result.id
        })
    
    logger.info(f"Queued {len(feedback_ids)} feedbacks for processing")
    return results


@shared_task
def generate_insights(processed_feedback_id):
    """
    Generate insights from processed feedback.
    
    This task:
    1. Analyzes processed feedback
    2. Identifies patterns and trends
    3. Creates Insight records
    4. Triggers alerts if critical
    """
    from analysis.models import ProcessedFeedback, Insight, Alert
    from analysis.insight_generator import InsightGenerator  # You'll create this
    
    try:
        processed = ProcessedFeedback.objects.select_related(
            'raw_feed', 'raw_feed__entity'
        ).get(id=processed_feedback_id)
        
        generator = InsightGenerator()
        
        # Generate insights
        insights_data = generator.analyze(processed)
        
        created_insights = []
        for insight_data in insights_data:
            insight = Insight.objects.create(
                entity=processed.raw_feed.entity,
                processed_feedback=processed,
                insight_type=insight_data['type'],
                priority=insight_data['priority'],
                title=insight_data['title'],
                text=insight_data['text'],
                recommendation=insight_data.get('recommendation'),
                confidence_score=insight_data['confidence_score'],
                impact_score=insight_data.get('impact_score', 0.0)
            )
            created_insights.append(insight)
            
            # Create alert if critical
            if insight.priority == 'critical':
                Alert.objects.create(
                    entity=processed.raw_feed.entity,
                    insight=insight,
                    message=f"Critical issue detected: {insight.title}"
                )
                
                # Send notification
                send_alert_notification.delay(insight.id)
        
        logger.info(
            f"Generated {len(created_insights)} insights for "
            f"feedback #{processed_feedback_id}"
        )
        
        return {
            'status': 'success',
            'insights_count': len(created_insights)
        }
        
    except Exception as e:
        logger.error(
            f"Error generating insights for #{processed_feedback_id}: {str(e)}"
        )
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_alert_notification(insight_id):
    """
    Send notification for critical alerts.
    """
    from analysis.models import Insight, Alert
    from django.core.mail import send_mail
    from django.conf import settings
    
    try:
        insight = Insight.objects.select_related(
            'entity', 'alert'
        ).get(id=insight_id)
        
        alert = insight.alert
        
        # Send email
        subject = f"Critical Alert: {insight.title}"
        message = f"""
        A critical issue has been detected:
        
        Entity: {insight.entity.name}
        Priority: {insight.priority}
        
        {insight.text}
        
        Recommendation: {insight.recommendation or 'N/A'}
        
        Please review and take action.
        """
        
        # You would configure recipient emails in settings
        recipient_list = [settings.EMAIL_HOST_USER]  # Replace with actual recipients
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        
        # Update alert status
        alert.is_sent = True
        alert.sent_at = timezone.now()
        alert.save(update_fields=['is_sent', 'sent_at'])
        
        logger.info(f"Sent alert notification for insight #{insight_id}")
        
        return {'status': 'success', 'insight_id': insight_id}
        
    except Exception as e:
        logger.error(f"Error sending alert for insight #{insight_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_feedbacks():
    """
    Periodic task to clean up old processed feedbacks.
    Run this with Celery Beat.
    """
    from datetime import timedelta
    from data_ingestion.models import RawFeed
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_feedbacks = RawFeed.objects.filter(
        status='processed',
        processed_at__lt=cutoff_date
    )
    
    count = old_feedbacks.count()
    old_feedbacks.delete()
    
    logger.info(f"Cleaned up {count} old feedbacks")
    
    return {'status': 'success', 'deleted_count': count}