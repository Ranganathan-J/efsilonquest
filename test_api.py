"""
Test script for Users and Data Ingestion APIs
Run this after starting the Django server to verify everything works.

Usage:
    python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def log(message, color=None):
    """Print colored log message"""
    if color:
        print(f"{color}{message}{END}")
    else:
        print(message)

def test_api():
    """Test all major API endpoints"""
    
    print("\n" + "="*60)
    log("🚀 Testing Users & Data Ingestion APIs", BLUE)
    print("="*60 + "\n")
    
    # Test data
    test_user = {
        "username": f"testuser_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "email": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
        "password": "TestPass123!",
        "password_confirm": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
        "role": "analyst",
        "company": "Test Corp"
    }
    
    access_token = None
    refresh_token = None
    entity_id = None
    feedback_id = None
    
    # ==================== USER AUTHENTICATION ====================
    log("\n📝 Testing User Registration", YELLOW)
    try:
        response = requests.post(
            f"{API_BASE}/users/register/",
            json=test_user
        )
        if response.status_code == 201:
            data = response.json()
            access_token = data['tokens']['access']
            refresh_token = data['tokens']['refresh']
            log(f"✅ User registered: {data['user']['username']}", GREEN)
            log(f"   Access token: {access_token[:20]}...", GREEN)
        else:
            log(f"❌ Registration failed: {response.text}", RED)
            return
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
        return
    
    # Headers with auth token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    log("\n👤 Testing Get Profile", YELLOW)
    try:
        response = requests.get(
            f"{API_BASE}/users/profile/",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Profile retrieved: {data['username']} ({data['role']})", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    log("\n🔄 Testing Update Profile", YELLOW)
    try:
        response = requests.patch(
            f"{API_BASE}/users/profile/",
            headers=headers,
            json={"phone": "+1234567890"}
        )
        if response.status_code == 200:
            log("✅ Profile updated successfully", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    # ==================== BUSINESS ENTITY ====================
    log("\n🏢 Testing Create Business Entity", YELLOW)
    try:
        response = requests.post(
            f"{API_BASE}/data-ingestion/entities/",
            headers=headers,
            json={
                "name": f"Test Entity {datetime.now().strftime('%Y%m%d%H%M%S')}",
                "description": "Test business entity",
                "is_active": True
            }
        )
        if response.status_code == 201:
            data = response.json()
            entity_id = data['id']
            log(f"✅ Entity created: {data['name']} (ID: {entity_id})", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
            return
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
        return
    
    log("\n📋 Testing List Entities", YELLOW)
    try:
        response = requests.get(
            f"{API_BASE}/data-ingestion/entities/",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Retrieved {len(data.get('results', data))} entities", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    # ==================== FEEDBACKS ====================
    log("\n💬 Testing Submit Single Feedback", YELLOW)
    try:
        response = requests.post(
            f"{API_BASE}/data-ingestion/feedbacks/",
            headers=headers,
            json={
                "entity": entity_id,
                "text": "This is a test feedback with good quality.",
                "source": "website",
                "product_name": "Test Product",
                "customer_name": "John Doe",
                "rating": 5
            }
        )
        if response.status_code == 201:
            data = response.json()
            feedback_id = data['id']
            log(f"✅ Feedback created (ID: {feedback_id})", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    log("\n📝 Testing Submit Multiple Feedbacks", YELLOW)
    feedbacks_data = [
        {
            "text": "Excellent product quality!",
            "rating": 5,
            "source": "website"
        },
        {
            "text": "Delivery was slow but product is good.",
            "rating": 3,
            "source": "twitter"
        },
        {
            "text": "Customer service needs improvement.",
            "rating": 2,
            "source": "app_store"
        }
    ]
    
    created_count = 0
    for fb in feedbacks_data:
        try:
            response = requests.post(
                f"{API_BASE}/data-ingestion/feedbacks/",
                headers=headers,
                json={
                    "entity": entity_id,
                    "product_name": "Test Product",
                    **fb
                }
            )
            if response.status_code == 201:
                created_count += 1
        except Exception as e:
            log(f"   ⚠️ Error: {str(e)}", YELLOW)
    
    log(f"✅ Created {created_count}/{len(feedbacks_data)} feedbacks", GREEN)
    
    log("\n📋 Testing List Feedbacks", YELLOW)
    try:
        response = requests.get(
            f"{API_BASE}/data-ingestion/feedbacks/?entity_id={entity_id}",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', data))
            log(f"✅ Retrieved {count} feedbacks", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    log("\n🔍 Testing Feedback Filters", YELLOW)
    filters_to_test = [
        ("status=new", "Status filter"),
        ("min_rating=4", "Rating filter"),
        ("search=quality", "Search filter"),
        ("source=website", "Source filter"),
    ]
    
    for filter_param, description in filters_to_test:
        try:
            response = requests.get(
                f"{API_BASE}/data-ingestion/feedbacks/?entity_id={entity_id}&{filter_param}",
                headers=headers
            )
            if response.status_code == 200:
                log(f"✅ {description} works", GREEN)
            else:
                log(f"❌ {description} failed", RED)
        except Exception as e:
            log(f"❌ Error: {str(e)}", RED)
    
    if feedback_id:
        log("\n🔍 Testing Get Feedback Detail", YELLOW)
        try:
            response = requests.get(
                f"{API_BASE}/data-ingestion/feedbacks/{feedback_id}/",
                headers=headers
            )
            if response.status_code == 200:
                log("✅ Feedback details retrieved", GREEN)
            else:
                log(f"❌ Failed: {response.text}", RED)
        except Exception as e:
            log(f"❌ Error: {str(e)}", RED)
        
        log("\n✏️ Testing Update Feedback", YELLOW)
        try:
            response = requests.patch(
                f"{API_BASE}/data-ingestion/feedbacks/{feedback_id}/",
                headers=headers,
                json={"rating": 4}
            )
            if response.status_code == 200:
                log("✅ Feedback updated", GREEN)
            else:
                log(f"❌ Failed: {response.text}", RED)
        except Exception as e:
            log(f"❌ Error: {str(e)}", RED)
    
    # ==================== STATISTICS ====================
    log("\n📊 Testing Statistics", YELLOW)
    try:
        response = requests.get(
            f"{API_BASE}/data-ingestion/statistics/?entity_id={entity_id}",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Statistics retrieved:", GREEN)
            log(f"   Total: {data.get('total_feedbacks', 0)}", GREEN)
            log(f"   New: {data.get('new_feedbacks', 0)}", GREEN)
            log(f"   Avg Rating: {data.get('average_rating', 0):.2f}", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    log("\n📊 Testing Entity Statistics", YELLOW)
    try:
        response = requests.get(
            f"{API_BASE}/data-ingestion/entities/{entity_id}/statistics/",
            headers=headers
        )
        if response.status_code == 200:
            log("✅ Entity statistics retrieved", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    # ==================== TOKEN REFRESH ====================
    log("\n🔄 Testing Token Refresh", YELLOW)
    try:
        response = requests.post(
            f"{API_BASE}/users/token/refresh/",
            json={"refresh": refresh_token}
        )
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Token refreshed: {data['access'][:20]}...", GREEN)
        else:
            log(f"❌ Failed: {response.text}", RED)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)
    
    # ==================== SUMMARY ====================
    print("\n" + "="*60)
    log("✅ All Tests Completed!", GREEN)
    log(f"🔑 Access Token: {access_token[:30]}...", BLUE)
    log(f"🏢 Entity ID: {entity_id}", BLUE)
    log(f"💬 Sample Feedback ID: {feedback_id}", BLUE)
    print("="*60 + "\n")
    
    log("📚 Next steps:", YELLOW)
    print("1. Visit http://localhost:8000/swagger/ for API docs")
    print("2. Try bulk upload with CSV/Excel files")
    print("3. Test with Postman or your frontend")
    print()

if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(BASE_URL, timeout=2)
        test_api()
    except requests.exceptions.ConnectionError:
        log("❌ Cannot connect to server. Make sure Django is running:", RED)
        log("   python manage.py runserver", YELLOW)
    except Exception as e:
        log(f"❌ Error: {str(e)}", RED)