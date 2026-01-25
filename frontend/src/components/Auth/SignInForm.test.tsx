import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SignInForm from './SignInForm'
import { useAuth } from '../../contexts/AuthContext'

// Mock the AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

describe('SignInForm', () => {
  const mockOnSwitchToSignUp = vi.fn()
  const mockOnSwitchToForgotPassword = vi.fn()
  const mockSignIn = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      signIn: mockSignIn,
      isLoading: false,
      user: null,
      isAuthenticated: false,
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })
  })

  it('renders sign in form with all elements', () => {
    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByText('Sign in to your account to continue learning')).toBeInTheDocument()
    expect(screen.getByLabelText('Email or Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument()
    expect(screen.getByText('Forgot your password?')).toBeInTheDocument()
    expect(screen.getByText('Sign up')).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Email or username is required')).toBeInTheDocument()
      expect(screen.getByText('Password is required')).toBeInTheDocument()
    })
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    const passwordInput = screen.getByLabelText('Password')
    const toggleButton = screen.getByRole('button', { name: '' }) // Eye icon button

    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'text')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('submits form with valid data', async () => {
    const user = userEvent.setup()
    mockSignIn.mockResolvedValue({ success: true })

    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    await user.type(screen.getByLabelText('Email or Username'), 'testuser')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith('testuser', 'password123')
    })
  })

  it('displays error message on sign in failure', async () => {
    const user = userEvent.setup()
    mockSignIn.mockResolvedValue({ success: false, error: 'Invalid credentials' })

    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    await user.type(screen.getByLabelText('Email or Username'), 'testuser')
    await user.type(screen.getByLabelText('Password'), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('shows loading state during sign in', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue({
      signIn: mockSignIn,
      isLoading: true,
      user: null,
      isAuthenticated: false,
      signUp: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    expect(screen.getByText('Signing in...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })

  it('calls onSwitchToSignUp when sign up link is clicked', async () => {
    const user = userEvent.setup()
    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    await user.click(screen.getByText('Sign up'))
    expect(mockOnSwitchToSignUp).toHaveBeenCalled()
  })

  it('calls onSwitchToForgotPassword when forgot password link is clicked', async () => {
    const user = userEvent.setup()
    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    await user.click(screen.getByText('Forgot your password?'))
    expect(mockOnSwitchToForgotPassword).toHaveBeenCalled()
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    const usernameInput = screen.getByLabelText('Email or Username')
    const passwordInput = screen.getByLabelText('Password')
    const submitButton = screen.getByRole('button', { name: 'Sign In' })

    // Tab navigation
    await user.tab()
    expect(usernameInput).toHaveFocus()

    await user.tab()
    expect(passwordInput).toHaveFocus()

    await user.tab()
    expect(submitButton).toHaveFocus()
  })

  it('handles form submission with Enter key', async () => {
    const user = userEvent.setup()
    mockSignIn.mockResolvedValue({ success: true })

    render(
      <SignInForm
        onSwitchToSignUp={mockOnSwitchToSignUp}
        onSwitchToForgotPassword={mockOnSwitchToForgotPassword}
      />
    )

    await user.type(screen.getByLabelText('Email or Username'), 'testuser')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith('testuser', 'password123')
    })
  })
})