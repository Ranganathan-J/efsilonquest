from celery import shared_task

@shared_task
def test_task(name):
    print(f"Hello {name}, Celery task executed!")
    return "Done"


@shared_task
def process_feedback(feedback_id):
    """
    Task to process a single feedback entry asynchronously.
    1. Save/Update to DB (already exists)
    2. Placeholder for AI analysis
    """
    try:
        feedback = Feedback.objects.get(id=feedback_id)
        
        # Placeholder for AI analysis
        # e.g., feedback.sentiment = run_ai_analysis(feedback.text)
        feedback.status = 'processed'
        feedback.save()
        return f"Processed feedback {feedback_id}"
    except Feedback.DoesNotExist:
        return f"Feedback {feedback_id} does not exist"