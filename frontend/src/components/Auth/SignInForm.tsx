import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

interface SignInFormData {
  username: string
  password: string
}

interface SignInFormProps {
  onSwitchToSignUp: () => void
  onSwitchToForgotPassword: () => void
}

const SignInForm: React.FC<SignInFormProps> = ({ onSwitchToSignUp, onSwitchToForgotPassword }) => {
  const { signIn, isLoading } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignInFormData>()

  const onSubmit = async (data: SignInFormData) => {
    setError(null)
    
    try {
      const result = await signIn(data.username, data.password)
      
      if (!result.success) {
        setError(result.error || 'Sign in failed - AWS Cognito not configured yet. This is expected in development mode.')
      }
    } catch (error) {
      console.error('Sign in error:', error)
      setError('Sign in failed - AWS Cognito not configured yet. This is expected in development mode.')
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome back</h2>
        <p className="text-gray-600">Sign in to your account to continue learning</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="username" className="form-label">
            Email Address
          </label>
          <input
            id="username"
            type="email"
            className={`form-input ${errors.username ? 'border-error-300 focus:ring-error-500' : ''}`}
            placeholder="Enter your email address"
            {...register('username', {
              required: 'Email or username is required',
            })}
          />
          {errors.username && (
            <p className="form-error">{errors.username.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="form-label">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              className={`form-input pr-10 ${errors.password ? 'border-error-300 focus:ring-error-500' : ''}`}
              placeholder="Enter your password"
              {...register('password', {
                required: 'Password is required',
              })}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-gray-400" />
              ) : (
                <Eye className="h-4 w-4 text-gray-400" />
              )}
            </button>
          </div>
          {errors.password && (
            <p className="form-error">{errors.password.message}</p>
          )}
        </div>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onSwitchToForgotPassword}
            className="text-sm text-primary-600 hover:text-primary-500"
          >
            Forgot your password?
          </button>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || isLoading}
          className="btn btn-primary btn-lg w-full"
        >
          {isSubmitting || isLoading ? (
            <>
              <Loader2 className="animate-spin h-4 w-4 mr-2" />
              Signing in...
            </>
          ) : (
            'Sign In'
          )}
        </button>

        <div className="text-center">
          <p className="text-sm text-gray-600">
            Don't have an account?{' '}
            <button
              type="button"
              onClick={onSwitchToSignUp}
              className="text-primary-600 hover:text-primary-500 font-medium"
            >
              Sign up
            </button>
          </p>
        </div>
      </form>
    </div>
  )
}

export default SignInForm