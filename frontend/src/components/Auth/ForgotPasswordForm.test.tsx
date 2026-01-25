import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ForgotPasswordForm from './ForgotPasswordForm'
import { useAuth } from '../../contexts/AuthContext'

// Mock the AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

describe('ForgotPasswordForm', () => {
  const mockOnBackToSignIn = vi.fn()
  const mockOnResetSuccess = vi.fn()
  const mockResetPassword = vi.fn()
  const mockConfirmResetPassword = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      resetPassword: mockResetPassword,
      confirmResetPassword: mockConfirmResetPassword,
      isLoading: false,
      user: null,
      isAuthenticated: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
    })
  })

  describe('Request Reset Step', () => {
    it('renders password reset request form', () => {
      render(
        <ForgotPasswordForm
          onBackToSignIn={mockOnBackToSignIn}
          onResetSuccess={mockOnResetSuccess}
        />
      )

      expect(screen.getByText('Forgot your password?')).toBeInTheDocument()
      expect(screen.getByText(/Enter your email or username/)).toBeInTheDocument()
      expect(screen.getByLabelText('Email or Username')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Send Reset Code' })).toBeInTheDocument()
      expect(screen.getByText('Back to sign in')).toBeInTheDocument()
    })

    it('validates required username field', async () => {
      const user = userEvent.setup()
      render(
        <ForgotPasswordForm
          onBackToSignIn={mockOnBackToSignIn}
          onResetSuccess={mockOnResetSuccess}
        />
      )

      await user.click(screen.getByRole('button', { name: 'Send Reset Code' }))

      await waitFor(() => {
        expect(screen.getByText('Email or username is required')).toBeInTheDocument()
      })
    })

    it('submits reset request with valid username', async () => {
      const user = userEvent.setup()
      mockResetPassword.mockResolvedValue({ success: true })

      render(
        <ForgotPasswordForm
          onBackToSignIn={mockOnBackToSignIn}
          onResetSuccess={mockOnResetSuccess}
        />
      )

      await user.type(screen.getByLabelText('Email or Username'), 'testuser')
      await user.click(screen.getByRole('button', { name: 'Send Reset Code' }))

      await waitFor(() => {
        expect(mockResetPassword).toHaveBeenCalledWith('testuser')
        expect(screen.getByText('Password reset code sent! Check your email.')).toBeInTheDocument()
      })
    })

    it('displays error on reset request failure', async () => {
      const user = userEvent.setup()
      mockResetPassword.mockResolvedValue({ success: false, error: 'User not found' })

      render(
        <ForgotPasswordForm
          onBackToSignIn={mockOnBackToSignIn}
          onResetSuccess={mockOnResetSuccess}
        />
      )

      await user.type(screen.getByLabelText('Email or Username'), 'nonexistent')
      await user.click(screen.getByRole('button', { name: 'Send Reset Code' }))

      await waitFor(() => {
        expect(screen.getByText('User not found')).toBeInTheDocument()
      })
    })

    it('calls onBackToSignIn when back link is clicked', async () => {
      const user = userEvent.setup()
      render(
        <ForgotPasswordForm
          onBackToSignIn={mockOnBackToSignIn}
          onResetSuccess={mockOnResetSuccess}
        />
      )

      await user.click(screen.getByText('Back to sign in'))
      expect(mockOnBackToSignIn).toHaveBeenCalled()
    })
  })

  describe('Confirm Reset Step', () => {
    beforeEach(async () => {
      const user = userEvent.setup()
      mockResetPassword.mockResolvedValue({ success: true })

      render(
        <ForgotPasswordForm
          onBackToSignIn={mockOnBackToSignIn}
          onResetSuccess={mockOnResetSuccess}
        />
      )

      // Navigate to confirm step
      await user.type(screen.getByLabelText('Email or Username'), 'testuser')
      await user.click(screen.getByRole('button', { name: 'Send Reset Code' }))

      await waitFor(() => {
        expect(screen.getByText('Reset your password')).toBeInTheDocument()
      })
    })

    it('renders password reset confirmation form', () => {
      expect(screen.getByText('Reset your password')).toBeInTheDocument()
      expect(screen.getByText(/Enter the code we sent to your email/)).toBeInTheDocument()
      expect(screen.getByLabelText('Confirmation Code')).toBeInTheDocument()
      expect(screen.getByLabelText('New Password')).toBeInTheDocument()
      expect(screen.getByLabelText('Confirm New Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Reset Password' })).toBeInTheDocument()
    })

    it('validates confirmation code format', async () => {
      const user = userEvent.setup()
      
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Confirmation code is required')).toBeInTheDocument()
      })

      const codeInput = screen.getByLabelText('Confirmation Code')
      await user.type(codeInput, '12345')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Confirmation code must be 6 digits')).toBeInTheDocument()
      })
    })

    it('validates new password requirements', async () => {
      const user = userEvent.setup()
      
      const passwordInput = screen.getByLabelText('New Password')
      
      // Test minimum length
      await user.type(passwordInput, 'short')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument()
      })

      await user.clear(passwordInput)
      
      // Test complexity requirements
      await user.type(passwordInput, 'password123')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Password must contain uppercase, lowercase, number, and special character')).toBeInTheDocument()
      })
    })

    it('validates password confirmation', async () => {
      const user = userEvent.setup()
      
      await user.type(screen.getByLabelText('New Password'), 'Password123!')
      await user.type(screen.getByLabelText('Confirm New Password'), 'DifferentPassword123!')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
      })
    })

    it('toggles password visibility', async () => {
      const user = userEvent.setup()
      
      const passwordInput = screen.getByLabelText('New Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm New Password')
      const toggleButtons = screen.getAllByRole('button', { name: '' }) // Eye icon buttons

      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(confirmPasswordInput).toHaveAttribute('type', 'password')

      // Toggle new password visibility
      await user.click(toggleButtons[0])
      expect(passwordInput).toHaveAttribute('type', 'text')

      // Toggle confirm password visibility
      await user.click(toggleButtons[1])
      expect(confirmPasswordInput).toHaveAttribute('type', 'text')
    })

    it('submits password reset with valid data', async () => {
      const user = userEvent.setup()
      mockConfirmResetPassword.mockResolvedValue({ success: true })

      await user.type(screen.getByLabelText('Confirmation Code'), '123456')
      await user.type(screen.getByLabelText('New Password'), 'NewPassword123!')
      await user.type(screen.getByLabelText('Confirm New Password'), 'NewPassword123!')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(mockConfirmResetPassword).toHaveBeenCalledWith('testuser', '123456', 'NewPassword123!')
      })
    })

    it('displays success message and calls onResetSuccess', async () => {
      const user = userEvent.setup()
      mockConfirmResetPassword.mockResolvedValue({ success: true })

      await user.type(screen.getByLabelText('Confirmation Code'), '123456')
      await user.type(screen.getByLabelText('New Password'), 'NewPassword123!')
      await user.type(screen.getByLabelText('Confirm New Password'), 'NewPassword123!')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Password reset successfully!')).toBeInTheDocument()
      })

      // Wait for the timeout to call onResetSuccess
      await waitFor(() => {
        expect(mockOnResetSuccess).toHaveBeenCalled()
      }, { timeout: 2000 })
    })

    it('displays error on password reset failure', async () => {
      const user = userEvent.setup()
      mockConfirmResetPassword.mockResolvedValue({ success: false, error: 'Invalid code' })

      await user.type(screen.getByLabelText('Confirmation Code'), '123456')
      await user.type(screen.getByLabelText('New Password'), 'NewPassword123!')
      await user.type(screen.getByLabelText('Confirm New Password'), 'NewPassword123!')
      await user.click(screen.getByRole('button', { name: 'Reset Password' }))

      await waitFor(() => {
        expect(screen.getByText('Invalid code')).toBeInTheDocument()
      })
    })
  })

  it('shows loading state during operations', async () => {
    mockUseAuth.mockReturnValue({
      resetPassword: mockResetPassword,
      confirmResetPassword: mockConfirmResetPassword,
      isLoading: true,
      user: null,
      isAuthenticated: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
    })

    render(
      <ForgotPasswordForm
        onBackToSignIn={mockOnBackToSignIn}
        onResetSuccess={mockOnResetSuccess}
      />
    )

    expect(screen.getByText('Sending code...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sending code/i })).toBeDisabled()
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    render(
      <ForgotPasswordForm
        onBackToSignIn={mockOnBackToSignIn}
        onResetSuccess={mockOnResetSuccess}
      />
    )

    const usernameInput = screen.getByLabelText('Email or Username')
    const submitButton = screen.getByRole('button', { name: 'Send Reset Code' })

    // Tab navigation
    await user.tab()
    expect(usernameInput).toHaveFocus()

    await user.tab()
    expect(submitButton).toHaveFocus()
  })
})