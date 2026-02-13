"""
Integration tests for Batch Upload API
Tests against deployed AWS infrastructure
"""
import pytest
import time


# Generate unique test data
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"batch_test_{TEST_TIMESTAMP}@example.com"
TEST_PASSWORD = "TestPass123!@#"


@pytest.mark.integration
class TestBatchUploadAPI:
    """Test suite for batch upload endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Create test user"""
        self.client = api_client
        
        # Register and login
        self.client.register(TEST_EMAIL, TEST_PASSWORD, first_name="Batch", last_name="Tester")
        tokens = self.client.login(TEST_EMAIL, TEST_PASSWORD)
        
        self.access_token = tokens['access_token']
        self.created_domains = []
        
        yield
        
        # Cleanup
        for domain_id in self.created_domains:
            try:
                self.client.delete(f'/domains/{domain_id}')
            except:
                pass
    
    def test_01_batch_upload_domain(self):
        """Test uploading domain with multiple terms"""
        response = self.client.post('/batch/upload', json={
            'domain': {
                'name': 'Batch Upload Test',
                'description': 'Test domain created via batch upload'
            },
            'terms': [
                {'term': 'Term1', 'definition': 'Definition 1'},
                {'term': 'Term2', 'definition': 'Definition 2'},
                {'term': 'Term3', 'definition': 'Definition 3'}
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert 'domain_id' in data
        assert 'terms_created' in data
        assert data['terms_created'] == 3
        
        self.created_domains.append(data['domain_id'])
    
    def test_02_batch_upload_large_dataset(self):
        """Test uploading domain with many terms"""
        terms = [
            {'term': f'Term{i}', 'definition': f'Definition {i}'}
            for i in range(50)
        ]
        
        response = self.client.post('/batch/upload', json={
            'domain': {
                'name': 'Large Batch Upload'
            },
            'terms': terms
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['terms_created'] == 50
        self.created_domains.append(data['domain_id'])
    
    def test_03_batch_upload_validation_error(self):
        """Test that invalid batch data returns error"""
        response = self.client.post('/batch/upload', json={
            'domain': {
                'name': ''  # Invalid: empty name
            },
            'terms': []
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_04_batch_upload_duplicate_terms(self):
        """Test handling of duplicate terms in batch"""
        response = self.client.post('/batch/upload', json={
            'domain': {
                'name': 'Duplicate Terms Test'
            },
            'terms': [
                {'term': 'Duplicate', 'definition': 'First definition'},
                {'term': 'Duplicate', 'definition': 'Second definition'},
                {'term': 'Unique', 'definition': 'Unique definition'}
            ]
        })
        
        # Should either reject or handle duplicates gracefully
        assert response.status_code in [201, 400]
        
        if response.status_code == 201:
            data = response.json()
            self.created_domains.append(data['domain_id'])
    
    def test_05_batch_upload_missing_terms(self):
        """Test that batch upload without terms fails"""
        response = self.client.post('/batch/upload', json={
            'domain': {
                'name': 'No Terms Domain'
            },
            'terms': []
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_06_batch_upload_json_format(self):
        """Test batch upload with JSON file format"""
        json_data = {
            'domain': {
                'name': 'JSON Format Test',
                'description': 'Testing JSON batch upload'
            },
            'terms': [
                {
                    'term': 'JSON Term 1',
                    'definition': 'First JSON definition',
                    'examples': ['Example 1', 'Example 2']
                },
                {
                    'term': 'JSON Term 2',
                    'definition': 'Second JSON definition'
                }
            ]
        }
        
        response = self.client.post('/batch/upload', json=json_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['terms_created'] == 2
        self.created_domains.append(data['domain_id'])
    
    def test_07_batch_upload_progress(self):
        """Test getting batch upload progress"""
        # Start batch upload
        upload_response = self.client.post('/batch/upload', json={
            'domain': {'name': 'Progress Test'},
            'terms': [{'term': f'T{i}', 'definition': f'D{i}'} for i in range(20)]
        })
        
        assert upload_response.status_code == 201
        domain_id = upload_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # Verify all terms were created
        domain_response = self.client.get(f'/domains/{domain_id}')
        assert len(domain_response.json()['terms']) == 20
    
    def test_08_unauthorized_batch_upload(self):
        """Test that batch upload without auth fails"""
        self.client.clear_auth_token()
        
        response = self.client.post('/batch/upload', json={
            'domain': {'name': 'Test'},
            'terms': [{'term': 'T', 'definition': 'D'}]
        })
        
        assert response.status_code == 401
