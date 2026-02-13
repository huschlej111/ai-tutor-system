"""
Integration tests for Answer Evaluation API
Tests against deployed AWS infrastructure
"""
import pytest
import time


# Generate unique test data
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"eval_test_{TEST_TIMESTAMP}@example.com"
TEST_PASSWORD = "TestPass123!@#"


@pytest.mark.integration
class TestAnswerEvaluationAPI:
    """Test suite for answer evaluation endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Create test user"""
        self.client = api_client
        
        # Register and login
        self.client.register(TEST_EMAIL, TEST_PASSWORD, first_name="Eval", last_name="Tester")
        tokens = self.client.login(TEST_EMAIL, TEST_PASSWORD)
        
        self.access_token = tokens['access_token']
    
    def test_01_evaluate_exact_match(self):
        """Test evaluation with exact matching answer"""
        response = self.client.post('/answer/evaluate', json={
            'answer': 'AWS Lambda is a serverless compute service',
            'correct_answer': 'AWS Lambda is a serverless compute service'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'similarity' in data
        assert data['similarity'] >= 0.95  # Very high similarity
        assert 'feedback' in data
    
    def test_02_evaluate_similar_answer(self):
        """Test evaluation with semantically similar answer"""
        response = self.client.post('/answer/evaluate', json={
            'answer': 'Lambda is serverless computing',
            'correct_answer': 'AWS Lambda is a serverless compute service'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'similarity' in data
        assert 0.6 <= data['similarity'] <= 0.9  # Good similarity
        assert 'feedback' in data
    
    def test_03_evaluate_incorrect_answer(self):
        """Test evaluation with incorrect answer"""
        response = self.client.post('/answer/evaluate', json={
            'answer': 'S3 is object storage',
            'correct_answer': 'Lambda is serverless compute'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'similarity' in data
        assert data['similarity'] < 0.5  # Low similarity
        assert 'feedback' in data
    
    def test_04_evaluate_empty_answer(self):
        """Test that empty answer returns error"""
        response = self.client.post('/answer/evaluate', json={
            'answer': '',
            'correct_answer': 'Some answer'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_05_evaluate_missing_fields(self):
        """Test that missing fields return error"""
        response = self.client.post('/answer/evaluate', json={
            'answer': 'Some answer'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_06_evaluate_long_answer(self):
        """Test evaluation with long answer"""
        long_answer = ' '.join(['word'] * 100)
        
        response = self.client.post('/answer/evaluate', json={
            'answer': long_answer,
            'correct_answer': 'Short answer'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert 'similarity' in data
    
    def test_07_evaluate_special_characters(self):
        """Test evaluation with special characters"""
        response = self.client.post('/answer/evaluate', json={
            'answer': 'Lambda: serverless compute (AWS)',
            'correct_answer': 'Lambda is serverless compute from AWS'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'similarity' in data
        assert data['similarity'] > 0.7  # Should handle punctuation
    
    def test_08_unauthorized_evaluation(self):
        """Test that evaluation without auth fails"""
        self.client.clear_auth_token()
        
        response = self.client.post('/answer/evaluate', json={
            'answer': 'test',
            'correct_answer': 'test'
        })
        
        assert response.status_code == 401
    
    @pytest.mark.slow
    def test_09_batch_evaluation(self):
        """Test evaluating multiple answers"""
        answers = [
            ('Lambda is serverless', 'Lambda is serverless compute'),
            ('S3 stores objects', 'S3 is object storage'),
            ('EC2 is virtual machine', 'EC2 provides virtual servers')
        ]
        
        results = []
        for answer, correct in answers:
            response = self.client.post('/answer/evaluate', json={
                'answer': answer,
                'correct_answer': correct
            })
            assert response.status_code == 200
            results.append(response.json()['similarity'])
        
        # All should have reasonable similarity
        assert all(score > 0.6 for score in results)
