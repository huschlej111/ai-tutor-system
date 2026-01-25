import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SignUpForm from './SignUpForm'
import { useAuth } from '../../contexts/AuthContext'

// Mock the AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

describe('SignUpForm', () => {
  const mockOnSwitchToSignIn = vi.fn()
  const mockOnSignUpSuccess = vi.fn()
  const mockSignUp = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      signUp: mockSignUp,
      isLoading: false,
      user: null,
      isAuthenticated: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })
  })

  it('renders sign up form with all elements', () => {
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    expect(screen.getByText('Create your account')).toBeInTheDocument()
    expect(screen.getByText('Join Know-It-All Tutor and start learning today')).toBeInTheDocument()
    expect(screen.getByLabelText('First Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Last Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create Account' })).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    const submitButton = screen.getByRole('button', { name: 'Create Account' })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument()
      expect(screen.getByText('Email is required')).toBeInTheDocument()
      expect(screen.getByText('Password is required')).toBeInTheDocument()
      expect(screen.getByText('Please confirm your password')).toBeInTheDocument()
    })
  })

  it('validates username format', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    const usernameInput = screen.getByLabelText('Username')
    
    // Test minimum length
    await user.type(usernameInput, 'ab')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Username must be at least 3 characters')).toBeInTheDocument()
    })

    await user.clear(usernameInput)
    
    // Test invalid characters
    await user.type(usernameInput, 'user@name')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Username can only contain letters, numbers, and underscores')).toBeInTheDocument()
    })
  })

  it('validates email format', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    const emailInput = screen.getByLabelText('Email Address')
    await user.type(emailInput, 'invalid-email')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Invalid email address')).toBeInTheDocument()
    })
  })

  it('validates password requirements', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    const passwordInput = screen.getByLabelText('Password')
    
    // Test minimum length
    await user.type(passwordInput, 'short')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument()
    })

    await user.clear(passwordInput)
    
    // Test complexity requirements
    await user.type(passwordInput, 'password123')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Password must contain uppercase, lowercase, number, and special character')).toBeInTheDocument()
    })
  })

  it('validates password confirmation', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    await user.type(screen.getByLabelText('Password'), 'Password123!')
    await user.type(screen.getByLabelText('Confirm Password'), 'DifferentPassword123!')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
    })
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    const passwordInput = screen.getByLabelText('Password')
    const confirmPasswordInput = screen.getByLabelText('Confirm Password')
    const toggleButtons = screen.getAllByRole('button', { name: '' }) // Eye icon buttons

    expect(passwordInput).toHaveAttribute('type', 'password')
    expect(confirmPasswordInput).toHaveAttribute('type', 'password')

    // Toggle password visibility
    await user.click(toggleButtons[0])
    expect(passwordInput).toHaveAttribute('type', 'text')

    // Toggle confirm password visibility
    await user.click(toggleButtons[1])
    expect(confirmPasswordInput).toHaveAttribute('type', 'text')
  })

  it('submits form with valid data', async () => {
    const user = userEvent.setup()
    mockSignUp.mockResolvedValue({ success: true, requiresConfirmation: true })

    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    await user.type(screen.getByLabelText('First Name'), 'John')
    await user.type(screen.getByLabelText('Last Name'), 'Doe')
    await user.type(screen.getByLabelText('Username'), 'johndoe')
    await user.type(screen.getByLabelText('Email Address'), 'john@example.com')
    await user.type(screen.getByLabelText('Password'), 'Password123!')
    await user.type(screen.getByLabelText('Confirm Password'), 'Password123!')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith({
        username: 'johndoe',
        email: 'john@example.com',
        password: 'Password123!',
        given_name: 'John',
        family_name: 'Doe',
      })
      expect(mockOnSignUpSuccess).toHaveBeenCalledWith('johndoe')
    })
  })

  it('displays error message on sign up failure', async () => {
    const user = userEvent.setup()
    mockSignUp.mockResolvedValue({ success: false, error: 'Username already exists' })

    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    await user.type(screen.getByLabelText('Username'), 'existinguser')
    await user.type(screen.getByLabelText('Email Address'), 'user@example.com')
    await user.type(screen.getByLabelText('Password'), 'Password123!')
    await user.type(screen.getByLabelText('Confirm Password'), 'Password123!')
    await user.click(screen.getByRole('button', { name: 'Create Account' }))

    await waitFor(() => {
      expect(screen.getByText('Username already exists')).toBeInTheDocument()
    })
  })

  it('shows loading state during sign up', async () => {
    mockUseAuth.mockReturnValue({
      signUp: mockSignUp,
      isLoading: true,
      user: null,
      isAuthenticated: false,
      signIn: vi.fn(),
      signOut: vi.fn(),
      confirmSignUp: vi.fn(),
      resendConfirmationCode: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    expect(screen.getByText('Creating account...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled()
  })

  it('calls onSwitchToSignIn when sign in link is clicked', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    await user.click(screen.getByText('Sign in'))
    expect(mockOnSwitchToSignIn).toHaveBeenCalled()
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    render(
      <SignUpForm
        onSwitchToSignIn={mockOnSwitchToSignIn}
        onSignUpSuccess={mockOnSignUpSuccess}
      />
    )

    const firstNameInput = screen.getByLabelText('First Name')
    const lastNameInput = screen.getByLabelText('Last Name')
    const usernameInput = screen.getByLabelText('Username')

    // Tab navigation through form fields
    await user.tab()
    expect(firstNameInput).toHaveFocus()

    await user.tab()
    expect(lastNameInput).toHaveFocus()

    await user.tab()
    expect(usernameInput).toHaveFocus()
  })
})