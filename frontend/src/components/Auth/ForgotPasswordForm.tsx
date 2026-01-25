import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Loader2, KeyRound, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

interface ForgotPasswordFormData {
  username: string
}

interface ResetPasswordFormData {
  confirmationCode: string
  newPassword: string
  confirmPassword: string
}

interface ForgotPasswordFormProps {
  onBackToSignIn: () => void
  onResetSuccess: () => void
}

const ForgotPasswordForm: React.FC<ForgotPasswordFormProps> = ({ 
  onBackToSignIn, 
  onResetSuccess 
}) => {
  const { resetPassword, confirmResetPassword, isLoading } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [step, setStep] = useState<'request' | 'confirm'>('request')
  const [username, setUsername] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  const {
    register: registerRequest,
    handleSubmit: handleSubmitRequest,
    formState: { errors: requestErrors, isSubmitting: isRequestSubmitting },
  } = useForm<ForgotPasswordFormData>()

  const {
    register: registerReset,
    handleSubmit: handleSubmitReset,
    watch,
    formState: { errors: resetErrors, isSubmitting: isResetSubmitting },
  } = useForm<ResetPasswordFormData>()

  const newPassword = watch('newPassword')

  const onSubmitRequest = async (data: ForgotPasswordFormData) => {
    setError(null)
    setSuccess(null)
    
    const result = await resetPassword(data.username)
    
    if (result.success) {
      setUsername(data.username)
      setStep('confirm')
      setSuccess('Password reset code sent! Check your email.')
    } else {
      setError(result.error || 'Failed to send reset code')
    }
  }

  const onSubmitReset = async (data: ResetPasswordFormData) => {
    setError(null)
    setSuccess(null)
    
    const result = await confirmResetPassword(username, data.confirmationCode, data.newPassword)
    
    if (result.success) {
      setSuccess('Password reset successfully!')
      setTimeout(() => {
        onResetSuccess()
      }, 1500)
    } else {
      setError(result.error || 'Password reset failed')
    }
  }

  if (step === 'request') {
    return (
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <KeyRound className="w-8 h-8 text-primary-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Forgot your password?</h2>
          <p className="text-gray-600">
            Enter your email or username and we'll send you a code to reset your password.
          </p>
        </div>

        <form onSubmit={handleSubmitRequest(onSubmitRequest)} className="space-y-6">
          {error && (
            <div className="bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md">
              {success}
            </div>
          )}

          <div>
            <label htmlFor="username" className="form-label">
              Email or Username
            </label>
            <input
              id="username"
              type="text"
              className={`form-input ${requestErrors.username ? 'border-error-300 focus:ring-error-500' : ''}`}
              placeholder="Enter your email or username"
              {...registerRequest('username', {
                required: 'Email or username is required',
              })}
            />
            {requestErrors.username && (
              <p className="form-error">{requestErrors.username.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isRequestSubmitting || isLoading}
            className="btn btn-primary btn-lg w-full"
          >
            {isRequestSubmitting || isLoading ? (
              <>
                <Loader2 className="animate-spin h-4 w-4 mr-2" />
                Sending code...
              </>
            ) : (
              'Send Reset Code'
            )}
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={onBackToSignIn}
              className="text-primary-600 hover:text-primary-500 font-medium"
            >
              Back to sign in
            </button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <KeyRound className="w-8 h-8 text-primary-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Reset your password</h2>
        <p className="text-gray-600">
          Enter the code we sent to your email and choose a new password.
        </p>
      </div>

      <form onSubmit={handleSubmitReset(onSubmitReset)} className="space-y-6">
        {error && (
          <div className="bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md">
            {success}
          </div>
        )}

        <div>
          <label htmlFor="confirmationCode" className="form-label">
            Confirmation Code
          </label>
          <input
            id="confirmationCode"
            type="text"
            className={`form-input text-center text-lg tracking-widest ${resetErrors.confirmationCode ? 'border-error-300 focus:ring-error-500' : ''}`}
            placeholder="000000"
            maxLength={6}
            {...registerReset('confirmationCode', {
              required: 'Confirmation code is required',
              pattern: {
                value: /^\d{6}$/,
                message: 'Confirmation code must be 6 digits',
              },
            })}
          />
          {resetErrors.confirmationCode && (
            <p className="form-error">{resetErrors.confirmationCode.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="newPassword" className="form-label">
            New Password
          </label>
          <div className="relative">
            <input
              id="newPassword"
              type={showPassword ? 'text' : 'password'}
              className={`form-input pr-10 ${resetErrors.newPassword ? 'border-error-300 focus:ring-error-500' : ''}`}
              placeholder="Enter new password"
              {...registerReset('newPassword', {
                required: 'New password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
                pattern: {
                  value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                  message: 'Password must contain uppercase, lowercase, number, and special character',
                },
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
          {resetErrors.newPassword && (
            <p className="form-error">{resetErrors.newPassword.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="form-label">
            Confirm New Password
          </label>
          <div className="relative">
            <input
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              className={`form-input pr-10 ${resetErrors.confirmPassword ? 'border-error-300 focus:ring-error-500' : ''}`}
              placeholder="Confirm new password"
              {...registerReset('confirmPassword', {
                required: 'Please confirm your new password',
                validate: (value) => value === newPassword || 'Passwords do not match',
              })}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              {showConfirmPassword ? (
                <EyeOff className="h-4 w-4 text-gray-400" />
              ) : (
                <Eye className="h-4 w-4 text-gray-400" />
              )}
            </button>
          </div>
          {resetErrors.confirmPassword && (
            <p className="form-error">{resetErrors.confirmPassword.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isResetSubmitting || isLoading}
          className="btn btn-primary btn-lg w-full"
        >
          {isResetSubmitting || isLoading ? (
            <>
              <Loader2 className="animate-spin h-4 w-4 mr-2" />
              Resetting password...
            </>
          ) : (
            'Reset Password'
          )}
        </button>

        <div className="text-center">
          <button
            type="button"
            onClick={onBackToSignIn}
            className="text-primary-600 hover:text-primary-500 font-medium"
          >
            Back to sign in
          </button>
        </div>
      </form>
    </div>
  )
}

export default ForgotPasswordForm