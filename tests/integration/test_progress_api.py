"""
Integration tests for Progress Tracking API
Tests against deployed AWS infrastructure
"""
import pytest
import time


# Generate unique test data
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"progress_test_{TEST_TIMESTAMP}@example.com"
TEST_PASSWORD = "TestPass123!@#"


@pytest.mark.integration
class TestProgressAPI:
    """Test suite for progress tracking endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Create test user, domain, and complete a quiz"""
        self.client = api_client
        
        # Register and login
        self.client.register(TEST_EMAIL, TEST_PASSWORD, first_name="Progress", last_name="Tester")
        tokens = self.client.login(TEST_EMAIL, TEST_PASSWORD)
        
        self.access_token = tokens['access_token']
        self.user_sub = tokens.get('user_sub')
        
        # Create test domain
        domain_response = self.client.post('/domains', json={
            'name': 'Progress Test Domain',
            'terms': [
                {'term': 'Test1', 'definition': 'Definition 1'},
                {'term': 'Test2', 'definition': 'Definition 2'}
            ]
        })
        self.domain_id = domain_response.json()['domain_id']
        
        yield
        
        # Cleanup
        try:
            self.client.delete(f'/domains/{self.domain_id}')
        except:
            pass
    
    def test_01_get_user_progress(self):
        """Test getting overall user progress"""
        response = self.client.get('/progress')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'total_domains' in data
        assert 'completed_domains' in data
        assert 'total_quizzes' in data
        assert 'average_score' in data
    
    def test_02_get_domain_progress(self):
        """Test getting progress for specific domain"""
        response = self.client.get(f'/progress/domain/{self.domain_id}')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'domain_id' in data
        assert 'quizzes_taken' in data
        assert 'best_score' in data
        assert 'mastery_level' in data
    
    def test_03_track_quiz_completion(self):
        """Test that completing quiz updates progress"""
        # Get initial progress
        initial_response = self.client.get('/progress')
        initial_quizzes = initial_response.json()['total_quizzes']
        
        # Complete a quiz
        start_response = self.client.post('/quiz/start', json={'domain_id': self.domain_id})
        session_id = start_response.json()['session_id']
        
        # Answer question
        question = start_response.json()['question']
        self.client.post(f'/quiz/{session_id}/answer', json={
            'term_id': question['term_id'],
            'answer': 'test answer'
        })
        
        # End quiz
        self.client.post(f'/quiz/{session_id}/end')
        
        # Check updated progress
        updated_response = self.client.get('/progress')
        updated_quizzes = updated_response.json()['total_quizzes']
        
        assert updated_quizzes == initial_quizzes + 1
    
    def test_04_get_progress_history(self):
        """Test getting progress history over time"""
        response = self.client.get('/progress/history')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'history' in data
        assert isinstance(data['history'], list)
    
    def test_05_get_domain_mastery(self):
        """Test getting mastery level for domain"""
        response = self.client.get(f'/progress/domain/{self.domain_id}/mastery')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'mastery_percentage' in data
        assert 'terms_mastered' in data
        assert 'total_terms' in data
    
    def test_06_unauthorized_progress_access(self):
        """Test that accessing progress without auth fails"""
        self.client.clear_auth_token()
        
        response = self.client.get('/progress')
        
        assert response.status_code == 401
