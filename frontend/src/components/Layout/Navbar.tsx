import { Link } from 'react-router-dom'
import { User, LogOut } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

const Navbar = () => {
  const { user, signOut } = useAuth()

  const handleSignOut = async () => {
    await signOut()
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <Link to="/app/dashboard" className="text-xl font-bold text-primary-600">
          Know-It-All Tutor
        </Link>
        
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-600">
            Welcome, {user?.username || user?.email || 'User'}
          </span>
          
          <Link 
            to="/app/profile" 
            className="p-2 text-gray-600 hover:text-primary-600 transition-colors"
          >
            <User size={20} />
          </Link>
          
          <button
            onClick={handleSignOut}
            className="p-2 text-gray-600 hover:text-error-600 transition-colors"
          >
            <LogOut size={20} />
          </button>
        </div>
      </div>
    </nav>
  )
}

export default Navbar