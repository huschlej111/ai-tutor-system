import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Loader2, Mail } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

interface ConfirmSignUpFormData {
  confirmationCode: string
}

interface ConfirmSignUpFormProps {
  username: string
  onConfirmationSuccess: () => void
  onBackToSignUp: () => void
}

const ConfirmSignUpForm: React.FC<ConfirmSignUpFormProps> = ({ 
  username, 
  onConfirmationSuccess, 
  onBackToSignUp 
}) => {
  const { confirmSignUp, resendConfirmationCode, isLoading } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isResending, setIsResending] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ConfirmSignUpFormData>()

  const onSubmit = async (data: ConfirmSignUpFormData) => {
    setError(null)
    setSuccess(null)
    
    const result = await confirmSignUp(username, data.confirmationCode)
    
    if (result.success) {
      setSuccess('Account confirmed successfully!')
      setTimeout(() => {
        onConfirmationSuccess()
      }, 1500)
    } else {
      setError(result.error || 'Confirmation failed')
    }
  }

  const handleResendCode = async () => {
    setIsResending(true)
    setError(null)
    setSuccess(null)
    
    const result = await resendConfirmationCode(username)
    
    if (result.success) {
      setSuccess('Confirmation code sent! Check your email.')
    } else {
      setError(result.error || 'Failed to resend code')
    }
    
    setIsResending(false)
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Mail className="w-8 h-8 text-primary-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Check your email</h2>
        <p className="text-gray-600">
          We've sent a confirmation code to your email address. Enter the code below to verify your account.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
            className={`form-input text-center text-lg tracking-widest ${errors.confirmationCode ? 'border-error-300 focus:ring-error-500' : ''}`}
            placeholder="000000"
            maxLength={6}
            {...register('confirmationCode', {
              required: 'Confirmation code is required',
              pattern: {
                value: /^\d{6}$/,
                message: 'Confirmation code must be 6 digits',
              },
            })}
          />
          {errors.confirmationCode && (
            <p className="form-error">{errors.confirmationCode.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting || isLoading}
          className="btn btn-primary btn-lg w-full"
        >
          {isSubmitting || isLoading ? (
            <>
              <Loader2 className="animate-spin h-4 w-4 mr-2" />
              Confirming...
            </>
          ) : (
            'Confirm Account'
          )}
        </button>

        <div className="text-center space-y-2">
          <p className="text-sm text-gray-600">
            Didn't receive the code?{' '}
            <button
              type="button"
              onClick={handleResendCode}
              disabled={isResending}
              className="text-primary-600 hover:text-primary-500 font-medium disabled:opacity-50"
            >
              {isResending ? 'Sending...' : 'Resend code'}
            </button>
          </p>
          
          <p className="text-sm text-gray-600">
            <button
              type="button"
              onClick={onBackToSignUp}
              className="text-primary-600 hover:text-primary-500 font-medium"
            >
              Back to sign up
            </button>
          </p>
        </div>
      </form>
    </div>
  )
}

export default ConfirmSignUpForm