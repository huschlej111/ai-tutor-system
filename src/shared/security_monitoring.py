"""
Security monitoring and incident response for authentication events
Implements suspicious activity detection, alerting, and automated response triggers
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from database import get_db_connection
from security_controls import SecurityAuditLogger


class SecurityMonitor:
    """Security monitoring and threat detection"""
    
    # Threat detection thresholds
    SUSPICIOUS_ACTIVITY_THRESHOLDS = {
        'failed_logins_per_hour': 10,
        'failed_logins_per_day': 50,
        'multiple_ips_per_hour': 5,
        'rapid_succession_attempts': 5,  # attempts within 1 minute
        'geographic_anomaly_distance': 1000,  # km (placeholder for future geo detection)
        'unusual_user_agent_count': 3,  # different user agents per hour
    }
    
    # Risk score thresholds for automated actions
    RISK_THRESHOLDS = {
        'low': 30,
        'medium': 60,
        'high': 80,
        'critical': 95
    }
    
    @staticmethod
    def detect_suspicious_activity(email: str, hours: int = 24) -> Dict[str, Any]:
        """Detect suspicious activity patterns for a user"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get recent activity for the user
                cursor.execute("""
                    SELECT event_type, ip_address, user_agent, event_details, 
                           risk_score, created_at
                    FROM auth_audit_log
                    WHERE email = %s 
                    AND created_at > %s
                    ORDER BY created_at DESC
                """, (
                    email,
                    datetime.now(timezone.utc) - timedelta(hours=hours)
                ))
                
                events = cursor.fetchall()
                
                if not events:
                    return {'suspicious': False, 'patterns': []}
                
                # Analyze patterns
                patterns = []
                
                # Pattern 1: Excessive failed logins
                failed_logins = [e for e in events if 'failed' in e[0]]
                if len(failed_logins) >= SecurityMonitor.SUSPICIOUS_ACTIVITY_THRESHOLDS['failed_logins_per_hour']:
                    patterns.append({
                        'type': 'excessive_failed_logins',
                        'count': len(failed_logins),
                        'severity': 'high' if len(failed_logins) > 20 else 'medium',
                        'description': f'{len(failed_logins)} failed login attempts in {hours} hours'
                    })
                
                # Pattern 2: Multiple IP addresses
                unique_ips = set(str(e[1]) for e in events if e[1])
                if len(unique_ips) >= SecurityMonitor.SUSPICIOUS_ACTIVITY_THRESHOLDS['multiple_ips_per_hour']:
                    patterns.append({
                        'type': 'multiple_ip_addresses',
                        'count': len(unique_ips),
                        'severity': 'high',
                        'description': f'Login attempts from {len(unique_ips)} different IP addresses',
                        'ips': list(unique_ips)
                    })
                
                # Pattern 3: Rapid succession attempts
                rapid_attempts = SecurityMonitor._detect_rapid_attempts(events)
                if rapid_attempts['count'] >= SecurityMonitor.SUSPICIOUS_ACTIVITY_THRESHOLDS['rapid_succession_attempts']:
                    patterns.append({
                        'type': 'rapid_succession_attempts',
                        'count': rapid_attempts['count'],
                        'severity': 'high',
                        'description': f'{rapid_attempts["count"]} attempts within {rapid_attempts["timespan"]} seconds'
                    })
                
                # Pattern 4: Multiple user agents
                unique_agents = set(e[2] for e in events if e[2] and e[2] != 'Unknown')
                if len(unique_agents) >= SecurityMonitor.SUSPICIOUS_ACTIVITY_THRESHOLDS['unusual_user_agent_count']:
                    patterns.append({
                        'type': 'multiple_user_agents',
                        'count': len(unique_agents),
                        'severity': 'medium',
                        'description': f'Login attempts from {len(unique_agents)} different user agents'
                    })
                
                # Pattern 5: High risk score events
                high_risk_events = [e for e in events if e[4] >= SecurityMonitor.RISK_THRESHOLDS['high']]
                if high_risk_events:
                    patterns.append({
                        'type': 'high_risk_events',
                        'count': len(high_risk_events),
                        'severity': 'critical',
                        'description': f'{len(high_risk_events)} high-risk security events'
                    })
                
                # Calculate overall suspicion level
                is_suspicious = len(patterns) > 0
                overall_severity = 'low'
                
                if patterns:
                    severities = [p['severity'] for p in patterns]
                    if 'critical' in severities:
                        overall_severity = 'critical'
                    elif 'high' in severities:
                        overall_severity = 'high'
                    elif 'medium' in severities:
                        overall_severity = 'medium'
                
                return {
                    'suspicious': is_suspicious,
                    'severity': overall_severity,
                    'patterns': patterns,
                    'total_events': len(events),
                    'analysis_period_hours': hours
                }
                
        except Exception as e:
            return {
                'suspicious': False,
                'error': f'Failed to analyze activity: {str(e)}',
                'patterns': []
            }
    
    @staticmethod
    def _detect_rapid_attempts(events: List[Tuple]) -> Dict[str, Any]:
        """Detect rapid succession login attempts"""
        if len(events) < 2:
            return {'count': 0, 'timespan': 0}
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda x: x[5])  # created_at is index 5
        
        max_rapid_count = 0
        min_timespan = float('inf')
        
        # Look for clusters of attempts within short time windows
        for i in range(len(sorted_events)):
            count = 1
            start_time = sorted_events[i][5]
            
            for j in range(i + 1, len(sorted_events)):
                time_diff = (sorted_events[j][5] - start_time).total_seconds()
                
                if time_diff <= 60:  # Within 1 minute
                    count += 1
                else:
                    break
            
            if count > max_rapid_count:
                max_rapid_count = count
                if count > 1:
                    end_time = sorted_events[i + count - 1][5]
                    min_timespan = min(min_timespan, (end_time - start_time).total_seconds())
        
        return {
            'count': max_rapid_count,
            'timespan': int(min_timespan) if min_timespan != float('inf') else 0
        }
    
    @staticmethod
    def generate_security_alert(
        alert_type: str,
        email: str,
        severity: str,
        details: Dict[str, Any],
        user_id: str = None
    ) -> Dict[str, Any]:
        """Generate a security alert for suspicious activity"""
        alert = {
            'alert_id': f"SEC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(email) % 10000:04d}",
            'alert_type': alert_type,
            'severity': severity,
            'email': email,
            'user_id': user_id,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'active',
            'recommended_actions': SecurityMonitor._get_recommended_actions(alert_type, severity)
        }
        
        # Log the alert as a security event
        SecurityAuditLogger.log_auth_event(
            f'security_alert_{alert_type}',
            email=email,
            user_id=user_id,
            event_details=alert,
            risk_score=SecurityMonitor._severity_to_risk_score(severity)
        )
        
        return alert
    
    @staticmethod
    def _get_recommended_actions(alert_type: str, severity: str) -> List[str]:
        """Get recommended actions based on alert type and severity"""
        actions = []
        
        base_actions = {
            'excessive_failed_logins': [
                'Monitor user account for continued suspicious activity',
                'Consider temporary account lockout if pattern continues',
                'Notify user of suspicious login attempts'
            ],
            'multiple_ip_addresses': [
                'Verify user travel patterns or VPN usage',
                'Consider requiring additional authentication',
                'Monitor for account compromise indicators'
            ],
            'rapid_succession_attempts': [
                'Implement rate limiting for this user/IP',
                'Consider automated brute force protection',
                'Alert security team for manual review'
            ],
            'multiple_user_agents': [
                'Verify legitimate use of multiple devices/browsers',
                'Check for signs of automated attacks',
                'Consider device fingerprinting'
            ],
            'high_risk_events': [
                'Immediate security team notification',
                'Consider temporary account suspension',
                'Initiate incident response procedures'
            ]
        }
        
        actions.extend(base_actions.get(alert_type, ['Review activity manually']))
        
        if severity in ['high', 'critical']:
            actions.extend([
                'Escalate to security team immediately',
                'Consider automated protective measures',
                'Document incident for compliance reporting'
            ])
        
        return actions
    
    @staticmethod
    def _severity_to_risk_score(severity: str) -> int:
        """Convert severity level to risk score"""
        severity_scores = {
            'low': 30,
            'medium': 60,
            'high': 80,
            'critical': 95
        }
        return severity_scores.get(severity, 50)
    
    @staticmethod
    def check_and_alert_suspicious_activity(email: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Check for suspicious activity and generate alerts if needed"""
        analysis = SecurityMonitor.detect_suspicious_activity(email)
        
        if analysis['suspicious']:
            # Generate alert for suspicious activity
            alert = SecurityMonitor.generate_security_alert(
                'suspicious_activity_detected',
                email,
                analysis['severity'],
                {
                    'patterns': analysis['patterns'],
                    'total_events': analysis['total_events'],
                    'analysis_period_hours': analysis['analysis_period_hours']
                },
                user_id
            )
            
            # Trigger automated responses based on severity
            SecurityMonitor._trigger_automated_response(alert)
            
            return alert
        
        return None
    
    @staticmethod
    def _trigger_automated_response(alert: Dict[str, Any]) -> None:
        """Trigger automated security responses based on alert severity"""
        severity = alert['severity']
        email = alert['email']
        
        try:
            if severity == 'critical':
                # Critical: Immediate protective actions
                SecurityMonitor._execute_critical_response(alert)
            elif severity == 'high':
                # High: Enhanced monitoring and potential restrictions
                SecurityMonitor._execute_high_response(alert)
            elif severity == 'medium':
                # Medium: Increased monitoring
                SecurityMonitor._execute_medium_response(alert)
            
            # Log the automated response
            SecurityAuditLogger.log_auth_event(
                'automated_security_response',
                email=email,
                user_id=alert.get('user_id'),
                event_details={
                    'alert_id': alert['alert_id'],
                    'severity': severity,
                    'response_triggered': True
                },
                risk_score=SecurityMonitor._severity_to_risk_score(severity)
            )
            
        except Exception as e:
            # Log failed automated response
            SecurityAuditLogger.log_auth_event(
                'automated_response_failed',
                email=email,
                user_id=alert.get('user_id'),
                event_details={
                    'alert_id': alert['alert_id'],
                    'error': str(e)
                },
                risk_score=70
            )
    
    @staticmethod
    def _execute_critical_response(alert: Dict[str, Any]) -> None:
        """Execute critical severity automated response"""
        # In a production system, this would:
        # 1. Temporarily suspend the account
        # 2. Invalidate all active sessions
        # 3. Send immediate notifications to security team
        # 4. Create incident ticket
        # 5. Potentially block IP addresses
        
        # For now, we'll log the intended actions
        SecurityAuditLogger.log_auth_event(
            'critical_response_simulated',
            email=alert['email'],
            user_id=alert.get('user_id'),
            event_details={
                'intended_actions': [
                    'account_suspension',
                    'session_invalidation',
                    'security_team_notification',
                    'incident_creation'
                ],
                'alert_id': alert['alert_id']
            },
            risk_score=95
        )
    
    @staticmethod
    def _execute_high_response(alert: Dict[str, Any]) -> None:
        """Execute high severity automated response"""
        # In a production system, this would:
        # 1. Increase monitoring frequency
        # 2. Require additional authentication factors
        # 3. Notify security team
        # 4. Apply temporary rate limiting
        
        SecurityAuditLogger.log_auth_event(
            'high_response_simulated',
            email=alert['email'],
            user_id=alert.get('user_id'),
            event_details={
                'intended_actions': [
                    'enhanced_monitoring',
                    'additional_auth_required',
                    'security_notification',
                    'rate_limiting'
                ],
                'alert_id': alert['alert_id']
            },
            risk_score=80
        )
    
    @staticmethod
    def _execute_medium_response(alert: Dict[str, Any]) -> None:
        """Execute medium severity automated response"""
        # In a production system, this would:
        # 1. Flag account for manual review
        # 2. Increase logging detail
        # 3. Send notification to user
        
        SecurityAuditLogger.log_auth_event(
            'medium_response_simulated',
            email=alert['email'],
            user_id=alert.get('user_id'),
            event_details={
                'intended_actions': [
                    'manual_review_flagged',
                    'enhanced_logging',
                    'user_notification'
                ],
                'alert_id': alert['alert_id']
            },
            risk_score=60
        )


class SecurityReporting:
    """Security reporting and compliance audit trails"""
    
    @staticmethod
    def generate_security_summary(hours: int = 24) -> Dict[str, Any]:
        """Generate a security summary report"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                since = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                # Get event counts by type
                cursor.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM auth_audit_log
                    WHERE created_at > %s
                    GROUP BY event_type
                    ORDER BY count DESC
                """, (since,))
                
                event_counts = dict(cursor.fetchall())
                
                # Get risk score distribution
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN risk_score >= 80 THEN 'high'
                            WHEN risk_score >= 60 THEN 'medium'
                            WHEN risk_score >= 30 THEN 'low'
                            ELSE 'minimal'
                        END as risk_level,
                        COUNT(*) as count
                    FROM auth_audit_log
                    WHERE created_at > %s
                    GROUP BY 
                        CASE 
                            WHEN risk_score >= 80 THEN 'high'
                            WHEN risk_score >= 60 THEN 'medium'
                            WHEN risk_score >= 30 THEN 'low'
                            ELSE 'minimal'
                        END
                """, (since,))
                
                risk_distribution = dict(cursor.fetchall())
                
                # Get top IP addresses by activity
                cursor.execute("""
                    SELECT ip_address, COUNT(*) as count
                    FROM auth_audit_log
                    WHERE created_at > %s AND ip_address IS NOT NULL
                    GROUP BY ip_address
                    ORDER BY count DESC
                    LIMIT 10
                """, (since,))
                
                top_ips = [{'ip': str(row[0]), 'count': row[1]} for row in cursor.fetchall()]
                
                # Get failed login statistics
                cursor.execute("""
                    SELECT COUNT(*) as failed_logins
                    FROM auth_audit_log
                    WHERE created_at > %s 
                    AND event_type LIKE '%failed%'
                """, (since,))
                
                result = cursor.fetchone()
                failed_logins = result[0] if result else 0
                
                # Get successful login statistics
                cursor.execute("""
                    SELECT COUNT(*) as successful_logins
                    FROM auth_audit_log
                    WHERE created_at > %s 
                    AND event_type LIKE '%success%'
                """, (since,))
                
                result = cursor.fetchone()
                successful_logins = result[0] if result else 0
                
                return {
                    'report_period_hours': hours,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'summary': {
                        'total_events': sum(event_counts.values()),
                        'failed_logins': failed_logins,
                        'successful_logins': successful_logins,
                        'success_rate': (successful_logins / (successful_logins + failed_logins) * 100) 
                                      if (successful_logins + failed_logins) > 0 else 0
                    },
                    'event_breakdown': event_counts,
                    'risk_distribution': risk_distribution,
                    'top_active_ips': top_ips,
                    'security_alerts': SecurityReporting._count_security_alerts(since)
                }
                
        except Exception as e:
            return {
                'error': f'Failed to generate security report: {str(e)}',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
    
    @staticmethod
    def _count_security_alerts(since: datetime) -> Dict[str, int]:
        """Count security alerts by type"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM auth_audit_log
                    WHERE created_at > %s 
                    AND event_type LIKE 'security_alert_%'
                    GROUP BY event_type
                """, (since,))
                
                return dict(cursor.fetchall())
                
        except Exception:
            return {}
    
    @staticmethod
    def get_compliance_audit_trail(email: str, days: int = 90) -> List[Dict[str, Any]]:
        """Get compliance audit trail for a user"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT event_type, ip_address, user_agent, event_details, 
                           risk_score, created_at
                    FROM auth_audit_log
                    WHERE email = %s 
                    AND created_at > %s
                    ORDER BY created_at DESC
                """, (
                    email,
                    datetime.now(timezone.utc) - timedelta(days=days)
                ))
                
                results = cursor.fetchall()
                
                return [{
                    'event_type': row[0],
                    'ip_address': str(row[1]) if row[1] else None,
                    'user_agent': row[2],
                    'event_details': json.loads(row[3]) if row[3] else {},
                    'risk_score': row[4],
                    'timestamp': row[5].isoformat()
                } for row in results]
                
        except Exception:
            return []