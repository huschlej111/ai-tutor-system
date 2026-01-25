import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiClient, type DashboardData, type DomainProgress } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const Dashboard = () => {
  const { user } = useAuth()
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true)
        const data = await apiClient.getDashboard()
        setDashboardData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      fetchDashboard()
    }
  }, [user])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-6">
        <div className="text-center text-red-600">
          <p className="font-semibold">Error loading dashboard</p>
          <p className="text-sm mt-1">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="btn btn-primary mt-4"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const stats = dashboardData?.overall_stats

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">
          Welcome back! Here's your learning progress overview.
        </p>
      </div>
      
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-2 text-gray-700">Total Domains</h3>
          <p className="text-3xl font-bold text-primary-600">{dashboardData?.total_domains || 0}</p>
        </div>
        
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-2 text-gray-700">Total Terms</h3>
          <p className="text-3xl font-bold text-info-600">{stats?.total_terms || 0}</p>
        </div>
        
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-2 text-gray-700">Mastered Terms</h3>
          <p className="text-3xl font-bold text-success-600">{stats?.mastered_terms || 0}</p>
        </div>
        
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-2 text-gray-700">Overall Progress</h3>
          <p className="text-3xl font-bold text-warning-600">{stats?.overall_completion_percentage || 0}%</p>
        </div>
      </div>

      {/* Progress Chart */}
      {stats && stats.total_terms > 0 && (
        <div className="card p-6 mb-8">
          <h3 className="text-xl font-semibold mb-4">Learning Progress Breakdown</h3>
          <div className="space-y-4">
            <ProgressBar 
              label="Mastered" 
              value={stats.mastered_terms} 
              total={stats.total_terms} 
              color="bg-success-600" 
            />
            <ProgressBar 
              label="Proficient" 
              value={stats.proficient_terms} 
              total={stats.total_terms} 
              color="bg-info-600" 
            />
            <ProgressBar 
              label="Developing" 
              value={stats.developing_terms} 
              total={stats.total_terms} 
              color="bg-warning-600" 
            />
            <ProgressBar 
              label="Needs Practice" 
              value={stats.needs_practice_terms} 
              total={stats.total_terms} 
              color="bg-error-600" 
            />
            <ProgressBar 
              label="Not Attempted" 
              value={stats.not_attempted_terms} 
              total={stats.total_terms} 
              color="bg-gray-400" 
            />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Domain Progress */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold">Your Domains</h3>
            <Link to="/app/domains/create" className="btn btn-primary btn-sm">
              Create Domain
            </Link>
          </div>
          
          {dashboardData?.domains && dashboardData.domains.length > 0 ? (
            <div className="space-y-4">
              {dashboardData.domains.slice(0, 5).map((domain) => (
                <DomainCard key={domain.id} domain={domain} />
              ))}
              {dashboardData.domains.length > 5 && (
                <Link 
                  to="/app/domains" 
                  className="block text-center text-primary-600 hover:text-primary-700 font-medium py-2"
                >
                  View all {dashboardData.domains.length} domains →
                </Link>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No domains created yet</p>
              <Link to="/app/domains/create" className="btn btn-primary">
                Create Your First Domain
              </Link>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="card p-6">
          <h3 className="text-xl font-semibold mb-4">Recent Activity</h3>
          
          {dashboardData?.recent_activity && dashboardData.recent_activity.length > 0 ? (
            <div className="space-y-3">
              {dashboardData.recent_activity.map((activity, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{activity.term}</p>
                    <p className="text-xs text-gray-500">{activity.domain_name}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      activity.is_correct 
                        ? 'bg-success-100 text-success-800' 
                        : 'bg-error-100 text-error-800'
                    }`}>
                      {activity.is_correct ? 'Correct' : 'Incorrect'}
                    </span>
                    <span className="text-xs text-gray-500">
                      {Math.round(activity.similarity_score * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">No recent activity</p>
              <p className="text-sm text-gray-400 mt-1">Start a quiz to see your progress here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ProgressBarProps {
  label: string
  value: number
  total: number
  color: string
}

const ProgressBar = ({ label, value, total, color }: ProgressBarProps) => {
  const percentage = total > 0 ? (value / total) * 100 : 0

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3 flex-1">
        <span className="text-sm font-medium text-gray-700 w-24">{label}</span>
        <div className="flex-1 bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full ${color}`}
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
      </div>
      <div className="ml-4 text-sm text-gray-600">
        {value} / {total} ({Math.round(percentage)}%)
      </div>
    </div>
  )
}

interface DomainCardProps {
  domain: DomainProgress
}

const DomainCard = ({ domain }: DomainCardProps) => {
  return (
    <Link 
      to={`/app/quiz/${domain.id}`}
      className="block p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-gray-900">{domain.name}</h4>
        <span className="text-sm text-gray-500">{domain.term_count} terms</span>
      </div>
      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{domain.description}</p>
      
      <div className="flex items-center justify-between">
        <div className="flex-1 bg-gray-200 rounded-full h-2 mr-3">
          <div 
            className="h-2 bg-primary-600 rounded-full"
            style={{ width: `${domain.completion_percentage}%` }}
          ></div>
        </div>
        <span className="text-sm font-medium text-gray-700">
          {Math.round(domain.completion_percentage)}%
        </span>
      </div>
    </Link>
  )
}

export default Dashboard