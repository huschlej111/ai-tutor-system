"""
Integration tests for Quiz Engine API
Tests against deployed AWS infrastructure
"""
import pytest
import time


# Generate unique test data
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"quiz_test_{TEST_TIMESTAMP}@example.com"
TEST_PASSWORD = "TestPass123!@#"


@pytest.mark.integration
class TestQuizAPI:
    """Test suite for quiz engine endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Create test user, domain, and terms"""
        self.client = api_client
        
        # Register and login
        self.client.register(TEST_EMAIL, TEST_PASSWORD, first_name="Quiz", last_name="Tester")
        tokens = self.client.login(TEST_EMAIL, TEST_PASSWORD)
        
        self.access_token = tokens['access_token']
        self.user_sub = tokens.get('user_sub')
        
        # Create test domain with terms
        domain_response = self.client.post('/domains', json={
            'name': 'Quiz Test Domain',
            'description': 'Domain for quiz testing',
            'terms': [
                {'term': 'Lambda', 'definition': 'Serverless compute service'},
                {'term': 'S3', 'definition': 'Object storage service'},
                {'term': 'EC2', 'definition': 'Virtual server in the cloud'}
            ]
        })
        self.domain_id = domain_response.json()['domain_id']
        
        # Track quiz sessions for cleanup
        self.quiz_sessions = []
        
        yield
        
        # Cleanup: End quiz sessions and delete domain
        for session_id in self.quiz_sessions:
            try:
                self.client.post(f'/quiz/{session_id}/end')
            except:
                pass
        
        try:
            self.client.delete(f'/domains/{self.domain_id}')
        except:
            pass
    
    def test_01_start_quiz(self):
        """Test starting a new quiz session"""
        response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id,
            'quiz_type': 'practice'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'session_id' in data
        assert 'question' in data
        assert data['question']['term'] in ['Lambda', 'S3', 'EC2']
        assert 'question_number' in data
        assert data['question_number'] == 1
        
        self.quiz_sessions.append(data['session_id'])
    
    def test_02_start_quiz_invalid_domain(self):
        """Test that starting quiz with invalid domain fails"""
        response = self.client.post('/quiz/start', json={
            'domain_id': '00000000-0000-0000-0000-000000000000'
        })
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
    
    def test_03_submit_answer(self):
        """Test submitting an answer to a quiz question"""
        # Start quiz
        start_response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id = start_response.json()['session_id']
        question = start_response.json()['question']
        self.quiz_sessions.append(session_id)
        
        # Submit answer
        response = self.client.post(f'/quiz/{session_id}/answer', json={
            'term_id': question['term_id'],
            'answer': 'Serverless compute service'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'similarity_score' in data
        assert 'feedback' in data
        assert 'correct' in data
        assert 'next_question' in data or 'quiz_complete' in data
    
    def test_04_submit_correct_answer(self):
        """Test submitting a correct answer"""
        # Start quiz
        start_response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id = start_response.json()['session_id']
        question = start_response.json()['question']
        self.quiz_sessions.append(session_id)
        
        # Get the correct definition for the term
        domain_response = self.client.get(f'/domains/{self.domain_id}')
        terms = domain_response.json()['terms']
        correct_term = next(t for t in terms if t['term_id'] == question['term_id'])
        
        # Submit correct answer
        response = self.client.post(f'/quiz/{session_id}/answer', json={
            'term_id': question['term_id'],
            'answer': correct_term['definition']
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['similarity_score'] >= 0.85  # High similarity for exact match
        assert data['correct'] == True
    
    def test_05_submit_incorrect_answer(self):
        """Test submitting an incorrect answer"""
        # Start quiz
        start_response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id = start_response.json()['session_id']
        question = start_response.json()['question']
        self.quiz_sessions.append(session_id)
        
        # Submit wrong answer
        response = self.client.post(f'/quiz/{session_id}/answer', json={
            'term_id': question['term_id'],
            'answer': 'This is completely wrong'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['similarity_score'] < 0.5  # Low similarity
        assert data['correct'] == False
        assert 'feedback' in data
    
    def test_06_get_quiz_status(self):
        """Test getting current quiz session status"""
        # Start quiz
        start_response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id = start_response.json()['session_id']
        self.quiz_sessions.append(session_id)
        
        # Get status
        response = self.client.get(f'/quiz/{session_id}/status')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'session_id' in data
        assert 'domain_id' in data
        assert 'questions_answered' in data
        assert 'total_questions' in data
        assert 'score' in data
    
    def test_07_end_quiz(self):
        """Test ending a quiz session"""
        # Start quiz
        start_response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id = start_response.json()['session_id']
        
        # End quiz
        response = self.client.post(f'/quiz/{session_id}/end')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'final_score' in data
        assert 'questions_answered' in data
        assert 'correct_answers' in data
        assert 'completion_time' in data
    
    def test_08_complete_full_quiz(self):
        """Test completing an entire quiz session"""
        # Start quiz
        start_response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id = start_response.json()['session_id']
        self.quiz_sessions.append(session_id)
        
        # Get all terms for correct answers
        domain_response = self.client.get(f'/domains/{self.domain_id}')
        terms = {t['term_id']: t['definition'] for t in domain_response.json()['terms']}
        
        # Answer all questions
        quiz_complete = False
        questions_answered = 0
        
        while not quiz_complete and questions_answered < 10:  # Safety limit
            # Get current question
            status_response = self.client.get(f'/quiz/{session_id}/status')
            if status_response.json().get('quiz_complete'):
                break
            
            current_question = status_response.json().get('current_question')
            if not current_question:
                break
            
            # Submit answer
            answer_response = self.client.post(f'/quiz/{session_id}/answer', json={
                'term_id': current_question['term_id'],
                'answer': terms[current_question['term_id']]
            })
            
            questions_answered += 1
            quiz_complete = answer_response.json().get('quiz_complete', False)
        
        # Verify quiz completion
        assert questions_answered == len(terms)
        
        # Get final results
        end_response = self.client.post(f'/quiz/{session_id}/end')
        assert end_response.status_code == 200
        assert end_response.json()['questions_answered'] == len(terms)
    
    def test_09_unauthorized_quiz_access(self):
        """Test that accessing quiz without auth fails"""
        self.client.clear_auth_token()
        
        response = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        
        assert response.status_code == 401
    
    def test_10_quiz_session_isolation(self):
        """Test that quiz sessions are isolated per user"""
        # Start first quiz
        response1 = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id1 = response1.json()['session_id']
        self.quiz_sessions.append(session_id1)
        
        # Start second quiz
        response2 = self.client.post('/quiz/start', json={
            'domain_id': self.domain_id
        })
        session_id2 = response2.json()['session_id']
        self.quiz_sessions.append(session_id2)
        
        # Verify different sessions
        assert session_id1 != session_id2
        
        # Verify both sessions are active
        status1 = self.client.get(f'/quiz/{session_id1}/status')
        status2 = self.client.get(f'/quiz/{session_id2}/status')
        
        assert status1.status_code == 200
        assert status2.status_code == 200
