"""
Configuration for Answer Evaluator
Thresholds and feedback messages can be easily modified without rebuilding containers
"""
import os

# Configurable thresholds (can be overridden by env vars)
THRESHOLDS = {
    'excellent': float(os.getenv('THRESHOLD_EXCELLENT', '0.85')),
    'good': float(os.getenv('THRESHOLD_GOOD', '0.70')),
    'partial': float(os.getenv('THRESHOLD_PARTIAL', '0.50'))
}

# Feedback messages (can be localized, personalized, etc.)
FEEDBACK_MESSAGES = {
    'excellent': "Excellent! Your answer matches the expected response.",
    'good': "Good answer, but could be more precise.",
    'partial': "Partially correct. Review the key concepts.",
    'incorrect': "Incorrect. Please review the material."
}

# Domain-specific threshold overrides (future enhancement)
# Can be loaded from DynamoDB for dynamic configuration
DOMAIN_THRESHOLDS = {
    # Example:
    # 'aws-certification': {'excellent': 0.90, 'good': 0.75, 'partial': 0.55},
    # 'python-basics': {'excellent': 0.80, 'good': 0.65, 'partial': 0.45},
}

def get_thresholds(domain_id: str = None) -> dict:
    """Get thresholds for a specific domain or default"""
    if domain_id and domain_id in DOMAIN_THRESHOLDS:
        return DOMAIN_THRESHOLDS[domain_id]
    return THRESHOLDS

def generate_feedback(similarity: float, domain_id: str = None) -> str:
    """Generate feedback based on similarity score and optional domain"""
    thresholds = get_thresholds(domain_id)
    
    if similarity >= thresholds['excellent']:
        return FEEDBACK_MESSAGES['excellent']
    elif similarity >= thresholds['good']:
        return FEEDBACK_MESSAGES['good']
    elif similarity >= thresholds['partial']:
        return FEEDBACK_MESSAGES['partial']
    else:
        return FEEDBACK_MESSAGES['incorrect']
