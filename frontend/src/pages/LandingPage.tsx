import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, Brain, TrendingUp } from 'lucide-react'

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white" style={{ minHeight: '100vh', background: 'linear-gradient(to bottom right, #eff6ff, white)' }}>
      {/* Header */}
      <header className="container py-6" style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 16px' }}>
        <nav className="flex items-center justify-between" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="text-2xl font-bold text-blue-600" style={{ fontSize: '24px', fontWeight: 'bold', color: '#2563eb' }}>
            Know-It-All Tutor
          </div>
          <Link 
            to="/auth" 
            className="btn btn-primary btn-md"
            style={{ 
              display: 'inline-flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              backgroundColor: '#2563eb',
              color: 'white',
              padding: '8px 16px',
              borderRadius: '6px',
              textDecoration: 'none',
              fontWeight: '500'
            }}
          >
            Get Started
          </Link>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="container py-20" style={{ maxWidth: '1200px', margin: '0 auto', padding: '80px 16px' }}>
        <div className="text-center max-w-4xl mx-auto" style={{ textAlign: 'center', maxWidth: '896px', margin: '0 auto' }}>
          <h1 className="text-5xl font-bold text-gray-900 mb-6" style={{ fontSize: '48px', fontWeight: 'bold', color: '#111827', marginBottom: '24px', lineHeight: '1.1' }}>
            Master Complex Terminology with 
            <span className="text-blue-600" style={{ color: '#2563eb' }}> AI-Powered Learning</span>
          </h1>
          
          <p className="text-xl text-gray-600 mb-8" style={{ fontSize: '20px', color: '#6b7280', marginBottom: '32px', lineHeight: '1.6' }}>
            Transform terminology-heavy subjects into interactive, hands-on tutorials. 
            Perfect for AWS certification, Python programming, and more.
          </p>
          
          <div className="flex items-center justify-center space-x-4" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
            <Link 
              to="/auth" 
              className="btn btn-primary btn-lg"
              style={{ 
                display: 'inline-flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                backgroundColor: '#2563eb',
                color: 'white',
                padding: '12px 24px',
                borderRadius: '6px',
                textDecoration: 'none',
                fontWeight: '500',
                fontSize: '16px'
              }}
            >
              Start Learning
              <ArrowRight size={20} style={{ marginLeft: '8px' }} />
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-20" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px', marginTop: '80px' }}>
          <div className="card p-6 text-center" style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textAlign: 'center' }}>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4" style={{ width: '48px', height: '48px', backgroundColor: '#dbeafe', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <BookOpen className="text-blue-600" size={24} style={{ color: '#2563eb' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>Domain-Agnostic Learning</h3>
            <p className="text-gray-600" style={{ color: '#6b7280', lineHeight: '1.5' }}>
              Create custom knowledge domains for any subject. From AWS to Python, 
              the platform adapts to your learning needs.
            </p>
          </div>
          
          <div className="card p-6 text-center" style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textAlign: 'center' }}>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4" style={{ width: '48px', height: '48px', backgroundColor: '#dbeafe', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <Brain className="text-blue-600" size={24} style={{ color: '#2563eb' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>Intelligent Evaluation</h3>
            <p className="text-gray-600" style={{ color: '#6b7280', lineHeight: '1.5' }}>
              AI-powered semantic answer evaluation provides fair, accurate feedback 
              on your understanding of complex terminology.
            </p>
          </div>
          
          <div className="card p-6 text-center" style={{ backgroundColor: 'white', padding: '24px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textAlign: 'center' }}>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4" style={{ width: '48px', height: '48px', backgroundColor: '#dbeafe', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <TrendingUp className="text-blue-600" size={24} style={{ color: '#2563eb' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>Progress Tracking</h3>
            <p className="text-gray-600" style={{ color: '#6b7280', lineHeight: '1.5' }}>
              Monitor your mastery level with detailed progress analytics and 
              personalized learning recommendations.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}

export default LandingPage