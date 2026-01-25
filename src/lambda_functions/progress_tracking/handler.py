"""
Progress Tracking Lambda Function Handler
Handles progress recording, mastery calculation, and progress aggregation
Requirements: 4.1, 4.4, 4.5
"""
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from shared.database import get_db_cursor, execute_query, execute_query_one
from shared.response_utils import create_response, handle_error
from shared.auth_utils import extract_user_from_cognito_event

logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for progress tracking operations
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # Verify authentication for all progress operations using Cognito
        auth_result = extract_user_from_cognito_event(event)
        if not auth_result['valid']:
            return create_response(401, {'error': 'Unauthorized'})
        
        user_id = auth_result['user_id']
        
        if http_method == 'POST':
            if '/progress/record' in path:
                return handle_record_attempt(event, user_id)
        elif http_method == 'GET':
            if '/progress/dashboard' in path:
                return handle_get_dashboard(event, user_id)
            elif '/progress/domain/' in path:
                return handle_get_domain_progress(event, user_id)
            elif '/progress/term/' in path:
                return handle_get_term_progress(event, user_id)
            elif '/progress/mastery' in path:
                return handle_get_mastery_levels(event, user_id)
        
        return create_response(404, {'error': 'Endpoint not found'})
        
    except Exception as e:
        logger.error(f"Progress tracking error: {str(e)}")
        return handle_error(e)


def handle_record_attempt(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Record a quiz attempt with similarity score and update mastery level
    Requirements: 4.1, 4.4, 4.5
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required_fields = ['term_id', 'student_answer', 'correct_answer', 'similarity_score', 'is_correct']
        for field in required_fields:
            if field not in body:
                return create_response(400, {'error': f'{field} is required'})
        
        term_id = body['term_id']
        student_answer = body['student_answer']
        correct_answer = body['correct_answer']
        similarity_score = float(body['similarity_score'])
        is_correct = bool(body['is_correct'])
        session_id = body.get('session_id')  # Optional
        feedback = body.get('feedback', '')
        
        # Validate similarity score range
        if not (0.0 <= similarity_score <= 1.0):
            return create_response(400, {'error': 'similarity_score must be between 0.0 and 1.0'})
        
        # Verify term exists and get domain info
        term_query = """
            SELECT t.id, t.data->>'term' as term, t.parent_id as domain_id,
                   d.data->>'name' as domain_name, d.user_id as domain_owner
            FROM tree_nodes t
            JOIN tree_nodes d ON t.parent_id = d.id
            WHERE t.id = %s AND t.node_type = 'term' AND d.node_type = 'domain'
        """
        term_result = execute_query_one(term_query, (term_id,))
        
        if not term_result:
            return create_response(404, {'error': 'Term not found'})
        
        domain_id = term_result[2]
        domain_owner = term_result[4]
        
        # Check if user has access to this domain (owner or public access)
        # For now, only allow access to own domains
        if domain_owner != user_id:
            return create_response(403, {'error': 'Access denied to this domain'})
        
        # Get current attempt number for this term
        attempt_count_query = """
            SELECT COALESCE(MAX(attempt_number), 0) + 1
            FROM progress_records
            WHERE user_id = %s AND term_id = %s
        """
        attempt_number = execute_query_one(attempt_count_query, (user_id, term_id))[0]
        
        # Record the attempt
        record_id = str(uuid.uuid4())
        insert_query = """
            INSERT INTO progress_records (
                id, user_id, term_id, session_id, student_answer, correct_answer,
                is_correct, similarity_score, attempt_number, feedback
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        execute_query(insert_query, (
            record_id, user_id, term_id, session_id, student_answer, correct_answer,
            is_correct, similarity_score, attempt_number, feedback
        ))
        
        # Calculate updated mastery level for this term
        mastery_level = calculate_term_mastery(user_id, term_id)
        
        # Get progress statistics for this term
        term_stats = get_term_statistics(user_id, term_id)
        
        return create_response(200, {
            'record_id': record_id,
            'attempt_number': attempt_number,
            'mastery_level': mastery_level,
            'term_statistics': term_stats,
            'message': 'Progress recorded successfully'
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ValueError as e:
        return create_response(400, {'error': f'Invalid data format: {str(e)}'})
    except Exception as e:
        logger.error(f"Error recording progress: {str(e)}")
        return handle_error(e)


def calculate_term_mastery(user_id: str, term_id: str) -> Dict[str, Any]:
    """
    Calculate mastery level for a specific term based on performance history
    Requirements: 4.4, 4.5
    
    Mastery calculation considers:
    - Recent performance (last 5 attempts weighted more heavily)
    - Consistency across attempts
    - Improvement trend
    - Similarity scores (not just correct/incorrect)
    """
    try:
        # Get all attempts for this term, ordered by recency
        attempts_query = """
            SELECT similarity_score, is_correct, created_at, attempt_number
            FROM progress_records
            WHERE user_id = %s AND term_id = %s
            ORDER BY attempt_number DESC
            LIMIT 10
        """
        attempts = execute_query(attempts_query, (user_id, term_id))
        
        if not attempts:
            return {
                'level': 'not_attempted',
                'score': 0.0,
                'confidence': 0.0,
                'attempts_count': 0,
                'recent_performance': 0.0
            }
        
        total_attempts = len(attempts)
        
        # Calculate weighted average with recent attempts having more weight
        weighted_scores = []
        weights = []
        
        for i, (similarity_score, is_correct, created_at, attempt_num) in enumerate(attempts):
            # Recent attempts get higher weight (exponential decay)
            weight = 2.0 ** (-i * 0.3)  # Recent attempts weighted more heavily
            
            # Convert similarity score to mastery contribution
            # Correct answers get full similarity score, incorrect get reduced score
            mastery_contribution = float(similarity_score) if is_correct else float(similarity_score) * 0.7
            
            weighted_scores.append(mastery_contribution * weight)
            weights.append(weight)
        
        # Calculate weighted average
        if sum(weights) > 0:
            weighted_average = sum(weighted_scores) / sum(weights)
        else:
            weighted_average = 0.0
        
        # Calculate consistency (lower variance = higher consistency)
        if total_attempts > 1:
            scores = [float(score) for score, _, _, _ in attempts]
            mean_score = sum(scores) / len(scores)
            variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
            consistency = max(0.0, 1.0 - variance)  # Higher consistency = lower variance
        else:
            consistency = 1.0 if total_attempts == 1 else 0.0
        
        # Calculate improvement trend (comparing first half vs second half of attempts)
        if total_attempts >= 4:
            mid_point = total_attempts // 2
            recent_scores = [float(score) for score, _, _, _ in attempts[:mid_point]]
            older_scores = [float(score) for score, _, _, _ in attempts[mid_point:]]
            
            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)
            improvement = max(0.0, min(1.0, (recent_avg - older_avg) + 0.5))  # Normalize to 0-1
        else:
            improvement = 0.5  # Neutral for insufficient data
        
        # Calculate final mastery score (0.0 to 1.0)
        # Weighted combination of performance, consistency, and improvement
        mastery_score = (
            weighted_average * 0.6 +      # 60% performance
            consistency * 0.25 +          # 25% consistency  
            improvement * 0.15            # 15% improvement trend
        )
        
        # Determine mastery level
        if mastery_score >= 0.85:
            level = 'mastered'
        elif mastery_score >= 0.70:
            level = 'proficient'
        elif mastery_score >= 0.50:
            level = 'developing'
        elif mastery_score >= 0.30:
            level = 'beginner'
        else:
            level = 'needs_practice'
        
        # Calculate confidence based on number of attempts and consistency
        confidence = min(1.0, (total_attempts / 5.0) * consistency)
        
        # Recent performance (last 3 attempts)
        recent_attempts = attempts[:3]
        if recent_attempts:
            recent_performance = sum(float(score) for score, _, _, _ in recent_attempts) / len(recent_attempts)
        else:
            recent_performance = 0.0
        
        return {
            'level': level,
            'score': round(mastery_score, 3),
            'confidence': round(confidence, 3),
            'attempts_count': total_attempts,
            'recent_performance': round(recent_performance, 3),
            'consistency': round(consistency, 3),
            'improvement_trend': round(improvement, 3)
        }
        
    except Exception as e:
        logger.error(f"Error calculating term mastery: {str(e)}")
        return {
            'level': 'error',
            'score': 0.0,
            'confidence': 0.0,
            'attempts_count': 0,
            'recent_performance': 0.0
        }


def get_term_statistics(user_id: str, term_id: str) -> Dict[str, Any]:
    """Get detailed statistics for a specific term"""
    try:
        stats_query = """
            SELECT 
                COUNT(*) as total_attempts,
                COUNT(*) FILTER (WHERE is_correct = true) as correct_attempts,
                AVG(similarity_score) as avg_similarity,
                MAX(similarity_score) as best_similarity,
                MIN(created_at) as first_attempt,
                MAX(created_at) as last_attempt
            FROM progress_records
            WHERE user_id = %s AND term_id = %s
        """
        stats = execute_query_one(stats_query, (user_id, term_id))
        
        if not stats or stats[0] == 0:
            return {
                'total_attempts': 0,
                'correct_attempts': 0,
                'accuracy_percentage': 0.0,
                'avg_similarity': 0.0,
                'best_similarity': 0.0,
                'first_attempt': None,
                'last_attempt': None
            }
        
        total_attempts = stats[0]
        correct_attempts = stats[1]
        avg_similarity = float(stats[2]) if stats[2] else 0.0
        best_similarity = float(stats[3]) if stats[3] else 0.0
        first_attempt = stats[4]
        last_attempt = stats[5]
        
        accuracy_percentage = (correct_attempts / total_attempts) * 100 if total_attempts > 0 else 0.0
        
        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'accuracy_percentage': round(accuracy_percentage, 1),
            'avg_similarity': round(avg_similarity, 3),
            'best_similarity': round(best_similarity, 3),
            'first_attempt': first_attempt.isoformat() if first_attempt else None,
            'last_attempt': last_attempt.isoformat() if last_attempt else None
        }
        
    except Exception as e:
        logger.error(f"Error getting term statistics: {str(e)}")
        return {
            'total_attempts': 0,
            'correct_attempts': 0,
            'accuracy_percentage': 0.0,
            'avg_similarity': 0.0,
            'best_similarity': 0.0,
            'first_attempt': None,
            'last_attempt': None
        }


def handle_get_dashboard(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Generate progress dashboard data with completion percentages
    Requirements: 4.2, 4.3
    """
    try:
        # Get all domains for the user
        domains_query = """
            SELECT id, data->>'name' as name, data->>'description' as description,
                   COALESCE(metadata->>'term_count', '0')::int as term_count
            FROM tree_nodes
            WHERE user_id = %s AND node_type = 'domain'
            ORDER BY created_at DESC
        """
        domains = execute_query(domains_query, (user_id,))
        
        dashboard_data = {
            'user_id': user_id,
            'total_domains': len(domains),
            'domains': [],
            'overall_stats': {
                'total_terms': 0,
                'mastered_terms': 0,
                'proficient_terms': 0,
                'developing_terms': 0,
                'needs_practice_terms': 0,
                'not_attempted_terms': 0,
                'overall_completion_percentage': 0.0,
                'overall_mastery_percentage': 0.0
            },
            'recent_activity': [],
            'learning_streaks': calculate_learning_streaks(user_id)
        }
        
        total_terms_across_domains = 0
        total_mastered_terms = 0
        total_proficient_terms = 0
        
        for domain in domains:
            domain_id = domain[0]
            domain_name = domain[1]
            domain_description = domain[2]
            term_count = domain[3]
            
            # Get progress for all terms in this domain
            domain_progress = calculate_domain_progress(user_id, domain_id)
            
            total_terms_across_domains += term_count
            total_mastered_terms += domain_progress['mastery_breakdown']['mastered']
            total_proficient_terms += domain_progress['mastery_breakdown']['proficient']
            
            dashboard_data['domains'].append({
                'id': domain_id,
                'name': domain_name,
                'description': domain_description,
                'term_count': term_count,
                'completion_percentage': domain_progress['completion_percentage'],
                'mastery_percentage': domain_progress['mastery_percentage'],
                'mastery_breakdown': domain_progress['mastery_breakdown'],
                'last_activity': domain_progress['last_activity']
            })
        
        # Calculate overall statistics
        if total_terms_across_domains > 0:
            dashboard_data['overall_stats']['total_terms'] = total_terms_across_domains
            dashboard_data['overall_stats']['mastered_terms'] = total_mastered_terms
            dashboard_data['overall_stats']['proficient_terms'] = total_proficient_terms
            dashboard_data['overall_stats']['overall_completion_percentage'] = round(
                ((total_mastered_terms + total_proficient_terms) / total_terms_across_domains) * 100, 1
            )
            dashboard_data['overall_stats']['overall_mastery_percentage'] = round(
                (total_mastered_terms / total_terms_across_domains) * 100, 1
            )
        
        # Get recent activity (last 10 attempts across all domains)
        recent_activity_query = """
            SELECT pr.created_at, pr.is_correct, pr.similarity_score,
                   t.data->>'term' as term, d.data->>'name' as domain_name
            FROM progress_records pr
            JOIN tree_nodes t ON pr.term_id = t.id
            JOIN tree_nodes d ON t.parent_id = d.id
            WHERE pr.user_id = %s
            ORDER BY pr.created_at DESC
            LIMIT 10
        """
        recent_attempts = execute_query(recent_activity_query, (user_id,))
        
        for attempt in recent_attempts:
            dashboard_data['recent_activity'].append({
                'timestamp': attempt[0].isoformat(),
                'is_correct': attempt[1],
                'similarity_score': round(float(attempt[2]), 2),
                'term': attempt[3],
                'domain_name': attempt[4]
            })
        
        return create_response(200, dashboard_data)
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        return handle_error(e)


def calculate_domain_progress(user_id: str, domain_id: str) -> Dict[str, Any]:
    """
    Calculate progress aggregation for a specific domain
    Requirements: 4.2, 4.3
    """
    try:
        # Get all terms in the domain
        terms_query = """
            SELECT id, data->>'term' as term
            FROM tree_nodes
            WHERE parent_id = %s AND node_type = 'term'
        """
        terms = execute_query(terms_query, (domain_id,))
        
        if not terms:
            return {
                'completion_percentage': 0.0,
                'mastery_percentage': 0.0,
                'mastery_breakdown': {
                    'mastered': 0,
                    'proficient': 0,
                    'developing': 0,
                    'beginner': 0,
                    'needs_practice': 0,
                    'not_attempted': 0
                },
                'last_activity': None
            }
        
        total_terms = len(terms)
        mastery_breakdown = {
            'mastered': 0,
            'proficient': 0,
            'developing': 0,
            'beginner': 0,
            'needs_practice': 0,
            'not_attempted': 0
        }
        
        last_activity = None
        
        for term in terms:
            term_id = term[0]
            mastery = calculate_term_mastery(user_id, term_id)
            
            # Count mastery levels
            mastery_level = mastery['level']
            if mastery_level in mastery_breakdown:
                mastery_breakdown[mastery_level] += 1
            else:
                mastery_breakdown['not_attempted'] += 1
            
            # Track most recent activity
            term_stats = get_term_statistics(user_id, term_id)
            if term_stats['last_attempt']:
                attempt_time = datetime.fromisoformat(term_stats['last_attempt'].replace('Z', '+00:00'))
                if not last_activity or attempt_time > last_activity:
                    last_activity = attempt_time
        
        # Calculate percentages
        # Completion = mastered + proficient + developing (some level of competency)
        completed_terms = mastery_breakdown['mastered'] + mastery_breakdown['proficient'] + mastery_breakdown['developing']
        completion_percentage = (completed_terms / total_terms) * 100 if total_terms > 0 else 0.0
        
        # Mastery = only mastered terms
        mastery_percentage = (mastery_breakdown['mastered'] / total_terms) * 100 if total_terms > 0 else 0.0
        
        return {
            'completion_percentage': round(completion_percentage, 1),
            'mastery_percentage': round(mastery_percentage, 1),
            'mastery_breakdown': mastery_breakdown,
            'last_activity': last_activity.isoformat() if last_activity else None
        }
        
    except Exception as e:
        logger.error(f"Error calculating domain progress: {str(e)}")
        return {
            'completion_percentage': 0.0,
            'mastery_percentage': 0.0,
            'mastery_breakdown': {
                'mastered': 0,
                'proficient': 0,
                'developing': 0,
                'beginner': 0,
                'needs_practice': 0,
                'not_attempted': 0
            },
            'last_activity': None
        }


def calculate_learning_streaks(user_id: str) -> Dict[str, Any]:
    """Calculate learning streaks and achievement tracking"""
    try:
        # Get daily activity for the last 30 days
        streak_query = """
            SELECT DATE(created_at) as activity_date, 
                   COUNT(*) as attempts,
                   COUNT(*) FILTER (WHERE is_correct = true) as correct_attempts
            FROM progress_records
            WHERE user_id = %s 
            AND created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY activity_date DESC
        """
        daily_activity = execute_query(streak_query, (user_id,))
        
        # Calculate current streak
        current_streak = 0
        today = datetime.now().date()
        
        for activity in daily_activity:
            activity_date = activity[0]
            days_diff = (today - activity_date).days
            
            if days_diff == current_streak:
                current_streak += 1
            else:
                break
        
        # Calculate longest streak in the last 30 days
        longest_streak = 0
        temp_streak = 0
        prev_date = None
        
        for activity in reversed(daily_activity):
            activity_date = activity[0]
            
            if prev_date is None or (activity_date - prev_date).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
            
            prev_date = activity_date
        
        # Calculate total activity stats
        total_attempts = sum(activity[1] for activity in daily_activity)
        total_correct = sum(activity[2] for activity in daily_activity)
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'total_attempts_30_days': total_attempts,
            'total_correct_30_days': total_correct,
            'active_days_30_days': len(daily_activity),
            'accuracy_30_days': round((total_correct / total_attempts) * 100, 1) if total_attempts > 0 else 0.0
        }
        
    except Exception as e:
        logger.error(f"Error calculating learning streaks: {str(e)}")
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_attempts_30_days': 0,
            'total_correct_30_days': 0,
            'active_days_30_days': 0,
            'accuracy_30_days': 0.0
        }


def handle_get_domain_progress(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle getting detailed progress for a specific domain"""
    try:
        # Extract domain_id from path
        path_segments = event.get('path', '').split('/')
        domain_id = None
        
        for i, segment in enumerate(path_segments):
            if segment == 'domain' and i + 1 < len(path_segments):
                domain_id = path_segments[i + 1]
                break
        
        if not domain_id:
            return create_response(400, {'error': 'Domain ID is required'})
        
        # Verify domain exists and user owns it
        domain_query = """
            SELECT id, data->>'name' as name, data->>'description' as description
            FROM tree_nodes
            WHERE id = %s AND user_id = %s AND node_type = 'domain'
        """
        domain = execute_query_one(domain_query, (domain_id, user_id))
        
        if not domain:
            return create_response(404, {'error': 'Domain not found'})
        
        # Get detailed progress for this domain
        domain_progress = calculate_domain_progress(user_id, domain_id)
        
        # Get term-level details
        terms_query = """
            SELECT id, data->>'term' as term, data->>'definition' as definition
            FROM tree_nodes
            WHERE parent_id = %s AND node_type = 'term'
            ORDER BY created_at
        """
        terms = execute_query(terms_query, (domain_id,))
        
        term_details = []
        for term in terms:
            term_id = term[0]
            term_name = term[1]
            term_definition = term[2]
            
            mastery = calculate_term_mastery(user_id, term_id)
            stats = get_term_statistics(user_id, term_id)
            
            term_details.append({
                'id': term_id,
                'term': term_name,
                'definition': term_definition,
                'mastery': mastery,
                'statistics': stats
            })
        
        response_data = {
            'domain': {
                'id': domain[0],
                'name': domain[1],
                'description': domain[2]
            },
            'progress': domain_progress,
            'terms': term_details
        }
        
        return create_response(200, response_data)
        
    except Exception as e:
        logger.error(f"Error getting domain progress: {str(e)}")
        return handle_error(e)


def handle_get_term_progress(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle getting detailed progress for a specific term"""
    try:
        # Extract term_id from path
        path_segments = event.get('path', '').split('/')
        term_id = None
        
        for i, segment in enumerate(path_segments):
            if segment == 'term' and i + 1 < len(path_segments):
                term_id = path_segments[i + 1]
                break
        
        if not term_id:
            return create_response(400, {'error': 'Term ID is required'})
        
        # Verify term exists and user has access
        term_query = """
            SELECT t.id, t.data->>'term' as term, t.data->>'definition' as definition,
                   d.id as domain_id, d.data->>'name' as domain_name, d.user_id
            FROM tree_nodes t
            JOIN tree_nodes d ON t.parent_id = d.id
            WHERE t.id = %s AND t.node_type = 'term' AND d.node_type = 'domain'
        """
        term = execute_query_one(term_query, (term_id,))
        
        if not term or term[5] != user_id:
            return create_response(404, {'error': 'Term not found'})
        
        # Get detailed progress for this term
        mastery = calculate_term_mastery(user_id, term_id)
        stats = get_term_statistics(user_id, term_id)
        
        # Get attempt history
        history_query = """
            SELECT student_answer, correct_answer, is_correct, similarity_score,
                   feedback, attempt_number, created_at
            FROM progress_records
            WHERE user_id = %s AND term_id = %s
            ORDER BY attempt_number DESC
        """
        attempts = execute_query(history_query, (user_id, term_id))
        
        attempt_history = []
        for attempt in attempts:
            attempt_history.append({
                'student_answer': attempt[0],
                'correct_answer': attempt[1],
                'is_correct': attempt[2],
                'similarity_score': round(float(attempt[3]), 3),
                'feedback': attempt[4],
                'attempt_number': attempt[5],
                'timestamp': attempt[6].isoformat()
            })
        
        response_data = {
            'term': {
                'id': term[0],
                'term': term[1],
                'definition': term[2],
                'domain_id': term[3],
                'domain_name': term[4]
            },
            'mastery': mastery,
            'statistics': stats,
            'attempt_history': attempt_history
        }
        
        return create_response(200, response_data)
        
    except Exception as e:
        logger.error(f"Error getting term progress: {str(e)}")
        return handle_error(e)


def handle_get_mastery_levels(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle getting mastery levels across all terms"""
    try:
        # Get all terms for user's domains
        terms_query = """
            SELECT t.id, t.data->>'term' as term, 
                   d.id as domain_id, d.data->>'name' as domain_name
            FROM tree_nodes t
            JOIN tree_nodes d ON t.parent_id = d.id
            WHERE d.user_id = %s AND t.node_type = 'term' AND d.node_type = 'domain'
            ORDER BY d.data->>'name', t.data->>'term'
        """
        terms = execute_query(terms_query, (user_id,))
        
        mastery_data = []
        
        for term in terms:
            term_id = term[0]
            term_name = term[1]
            domain_id = term[2]
            domain_name = term[3]
            
            mastery = calculate_term_mastery(user_id, term_id)
            
            mastery_data.append({
                'term_id': term_id,
                'term': term_name,
                'domain_id': domain_id,
                'domain_name': domain_name,
                'mastery': mastery
            })
        
        return create_response(200, {
            'user_id': user_id,
            'mastery_levels': mastery_data
        })
        
    except Exception as e:
        logger.error(f"Error getting mastery levels: {str(e)}")
        return handle_error(e)