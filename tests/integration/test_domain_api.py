"""
Integration tests for Domain Management API
Tests against deployed AWS infrastructure
"""
import pytest
import time


# Generate unique test data
TEST_TIMESTAMP = int(time.time())
TEST_EMAIL = f"domain_test_{TEST_TIMESTAMP}@example.com"
TEST_PASSWORD = "TestPass123!@#"


@pytest.mark.integration
class TestDomainAPI:
    """Test suite for domain management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Create and login test user"""
        self.client = api_client
        
        # Register and login
        self.client.register(TEST_EMAIL, TEST_PASSWORD, first_name="Domain", last_name="Tester")
        tokens = self.client.login(TEST_EMAIL, TEST_PASSWORD)
        
        self.access_token = tokens['access_token']
        self.user_sub = tokens.get('user_sub')
        
        # Track created domains for cleanup
        self.created_domains = []
        
        yield
        
        # Cleanup: Delete created domains
        for domain_id in self.created_domains:
            try:
                self.client.delete(f'/domains/{domain_id}')
            except:
                pass  # Ignore cleanup errors
    
    def test_01_create_domain(self):
        """Test creating a new domain"""
        response = self.client.post('/domains', json={
            'name': 'AWS Certification',
            'description': 'AWS Solutions Architect certification prep'
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert 'domain_id' in data
        assert data['name'] == 'AWS Certification'
        assert data['description'] == 'AWS Solutions Architect certification prep'
        assert data['created_by'] == self.user_sub
        
        self.created_domains.append(data['domain_id'])
    
    def test_02_create_domain_missing_name(self):
        """Test that creating domain without name fails"""
        response = self.client.post('/domains', json={
            'description': 'Missing name'
        })
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_03_list_domains(self):
        """Test listing all domains"""
        # Create a test domain first
        create_response = self.client.post('/domains', json={
            'name': 'Test Domain for Listing'
        })
        domain_id = create_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # List domains
        response = self.client.get('/domains')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'domains' in data
        assert isinstance(data['domains'], list)
        assert len(data['domains']) > 0
        
        # Verify our domain is in the list
        domain_names = [d['name'] for d in data['domains']]
        assert 'Test Domain for Listing' in domain_names
    
    def test_04_get_domain_by_id(self):
        """Test retrieving a specific domain"""
        # Create domain
        create_response = self.client.post('/domains', json={
            'name': 'Specific Domain'
        })
        domain_id = create_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # Get domain
        response = self.client.get(f'/domains/{domain_id}')
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['domain_id'] == domain_id
        assert data['name'] == 'Specific Domain'
    
    def test_05_get_nonexistent_domain(self):
        """Test that getting non-existent domain returns 404"""
        response = self.client.get('/domains/00000000-0000-0000-0000-000000000000')
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
    
    def test_06_update_domain(self):
        """Test updating a domain"""
        # Create domain
        create_response = self.client.post('/domains', json={
            'name': 'Original Name',
            'description': 'Original description'
        })
        domain_id = create_response.json()['domain_id']
        self.created_domains.append(domain_id)
        
        # Update domain
        response = self.client.put(f'/domains/{domain_id}', json={
            'name': 'Updated Name',
            'description': 'Updated description'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['name'] == 'Updated Name'
        assert data['description'] == 'Updated description'
    
    def test_07_delete_domain(self):
        """Test deleting a domain"""
        # Create domain
        create_response = self.client.post('/domains', json={
            'name': 'Domain to Delete'
        })
        domain_id = create_response.json()['domain_id']
        
        # Delete domain
        response = self.client.delete(f'/domains/{domain_id}')
        
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = self.client.get(f'/domains/{domain_id}')
        assert get_response.status_code == 404
    
    def test_08_unauthorized_access(self):
        """Test that accessing domains without auth fails"""
        self.client.clear_auth_token()
        
        response = self.client.get('/domains')
        
        assert response.status_code == 401
    
    def test_09_create_domain_with_terms(self):
        """Test creating domain with terms"""
        response = self.client.post('/domains', json={
            'name': 'Python Basics',
            'description': 'Python programming fundamentals',
            'terms': [
                {
                    'term': 'Lambda',
                    'definition': 'Anonymous function in Python'
                },
                {
                    'term': 'List Comprehension',
                    'definition': 'Concise way to create lists'
                }
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert 'domain_id' in data
        self.created_domains.append(data['domain_id'])
        
        # Verify terms were created
        domain_response = self.client.get(f'/domains/{data["domain_id"]}')
        domain_data = domain_response.json()
        
        assert 'terms' in domain_data
        assert len(domain_data['terms']) == 2
    
    @pytest.mark.slow
    def test_10_list_domains_pagination(self):
        """Test domain listing with pagination"""
        # Create multiple domains
        for i in range(5):
            response = self.client.post('/domains', json={
                'name': f'Pagination Test Domain {i}'
            })
            self.created_domains.append(response.json()['domain_id'])
        
        # Test pagination
        response = self.client.get('/domains?limit=2&offset=0')
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'domains' in data
        assert len(data['domains']) <= 2
        assert 'total' in data or 'next_offset' in data
