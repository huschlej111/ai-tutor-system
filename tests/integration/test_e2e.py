"""
End-to-end integration tests
Tests complete user journeys through the application
"""
import pytest
import time


# Generate unique test data
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"e2e_test_{TEST_TIMESTAMP}@example.com"
TEST_PASSWORD = "TestPass123!@#"


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndUserJourney:
    """Test complete user workflows from registration to quiz completion"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup test client"""
        self.client = api_client
        self.created_domains = []
        
        yield
        
        # Cleanup
        for domain_id in self.created_domains:
            try:
                self.client.delete(f'/domains/{domain_id}')
            except:
                pass
    
    def test_complete_user_journey(self):
        """
        Test complete user journey:
        1. Register new user
        2. Login
        3. Create domain with terms
        4. Start quiz
        5. Answer questions
        6. Complete quiz
        7. View progress
        """
        
        # Step 1: Register
        register_response = self.client.register(
            TEST_EMAIL,
            TEST_PASSWORD,
            first_name="E2E",
            last_name="Tester"
        )
        assert 'user_sub' in register_response
        user_sub = register_response['user_sub']
        
        # Step 2: Login
        login_response = self.client.login(TEST_EMAIL, TEST_PASSWORD)
        assert 'access_token' in login_response
        assert self.client.access_token is not None  # Auto-set by client
        
        # Step 3: Create domain with terms
        domain_response = self.client.post('/domains', json={
            'name': 'AWS Services E2E Test',
            'description': 'End-to-end test domain',
            'terms': [
                {
                    'term': 'Lambda',
                    'definition': 'Serverless compute service that runs code in response to events'
                },
                {
                    'term': 'S3',
                    'definition': 'Object storage service for storing and retrieving data'
                },
                {
                    'term': 'DynamoDB',
                    'definition': 'Fully managed NoSQL database service'
                }
            ]
        })
        assert domain_response.status_code == 201
        domain_id = domain_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # Verify domain was created
        get_domain_response = self.client.get(f'/domains/{domain_id}')
        assert get_domain_response.status_code == 200
        assert len(get_domain_response.json()['terms']) == 3
        
        # Step 4: Start quiz
        start_quiz_response = self.client.post('/quiz/start', json={
            'domain_id': domain_id,
            'quiz_type': 'practice'
        })
        assert start_quiz_response.status_code == 200
        session_id = start_quiz_response.json()['session_id']
        first_question = start_quiz_response.json()['question']
        
        # Step 5: Answer questions
        # Answer first question
        answer1_response = self.client.post(f'/quiz/{session_id}/answer', json={
            'term_id': first_question['term_id'],
            'answer': 'Serverless compute service'
        })
        assert answer1_response.status_code == 200
        assert 'similarity_score' in answer1_response.json()
        
        # Continue answering remaining questions
        quiz_complete = answer1_response.json().get('quiz_complete', False)
        questions_answered = 1
        
        while not quiz_complete and questions_answered < 10:
            status_response = self.client.get(f'/quiz/{session_id}/status')
            if status_response.json().get('quiz_complete'):
                break
            
            current_question = status_response.json().get('current_question')
            if not current_question:
                break
            
            answer_response = self.client.post(f'/quiz/{session_id}/answer', json={
                'term_id': current_question['term_id'],
                'answer': 'test answer'
            })
            
            questions_answered += 1
            quiz_complete = answer_response.json().get('quiz_complete', False)
        
        # Step 6: Complete quiz
        end_quiz_response = self.client.post(f'/quiz/{session_id}/end')
        assert end_quiz_response.status_code == 200
        final_results = end_quiz_response.json()
        
        assert 'final_score' in final_results
        assert 'questions_answered' in final_results
        assert final_results['questions_answered'] >= 1
        
        # Step 7: View progress
        progress_response = self.client.get('/progress')
        assert progress_response.status_code == 200
        progress_data = progress_response.json()
        
        assert progress_data['total_quizzes'] >= 1
        assert 'average_score' in progress_data
        
        # View domain-specific progress
        domain_progress_response = self.client.get(f'/progress/domain/{domain_id}')
        assert domain_progress_response.status_code == 200
        domain_progress = domain_progress_response.json()
        
        assert domain_progress['quizzes_taken'] >= 1
    
    def test_multiple_quiz_sessions(self):
        """Test user taking multiple quizzes on same domain"""
        
        # Register and login
        email = f"multi_quiz_{int(time.time())}@example.com"
        self.client.register(email, TEST_PASSWORD)
        self.client.login(email, TEST_PASSWORD)
        
        # Create domain
        domain_response = self.client.post('/domains', json={
            'name': 'Multi-Quiz Test',
            'terms': [
                {'term': 'T1', 'definition': 'D1'},
                {'term': 'T2', 'definition': 'D2'}
            ]
        })
        domain_id = domain_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # Take first quiz
        quiz1 = self.client.post('/quiz/start', json={'domain_id': domain_id})
        session1 = quiz1.json()['session_id']
        
        # Answer and end
        q1 = quiz1.json()['question']
        self.client.post(f'/quiz/{session1}/answer', json={
            'term_id': q1['term_id'],
            'answer': 'answer'
        })
        self.client.post(f'/quiz/{session1}/end')
        
        # Take second quiz
        quiz2 = self.client.post('/quiz/start', json={'domain_id': domain_id})
        session2 = quiz2.json()['session_id']
        
        # Verify different sessions
        assert session1 != session2
        
        # Check progress shows multiple quizzes
        progress = self.client.get(f'/progress/domain/{domain_id}')
        assert progress.json()['quizzes_taken'] >= 1
    
    def test_batch_upload_and_quiz(self):
        """Test creating domain via batch upload then taking quiz"""
        
        # Register and login
        email = f"batch_quiz_{int(time.time())}@example.com"
        self.client.register(email, TEST_PASSWORD)
        self.client.login(email, TEST_PASSWORD)
        
        # Batch upload domain
        batch_response = self.client.post('/batch/upload', json={
            'domain': {
                'name': 'Batch Upload Quiz Test'
            },
            'terms': [
                {'term': 'BatchTerm1', 'definition': 'Batch definition 1'},
                {'term': 'BatchTerm2', 'definition': 'Batch definition 2'},
                {'term': 'BatchTerm3', 'definition': 'Batch definition 3'}
            ]
        })
        assert batch_response.status_code == 201
        domain_id = batch_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # Start quiz on batch-uploaded domain
        quiz_response = self.client.post('/quiz/start', json={'domain_id': domain_id})
        assert quiz_response.status_code == 200
        
        # Verify question is from uploaded terms
        question = quiz_response.json()['question']
        assert question['term'] in ['BatchTerm1', 'BatchTerm2', 'BatchTerm3']
