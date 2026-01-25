import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConfirmSignUpForm from './ConfirmSignUpForm'
import { useAuth } from '../../contexts/AuthContext'

// Mock the AuthContext
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

describe('ConfirmSignUpForm', () => {
  const mockOnConfirmationSuccess = vi.fn()
  const mockOnBackToSignUp = vi.fn()
  const mockConfirmSignUp = vi.fn()
  const mockResendConfirmationCode = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({
      confirmSignUp: mockConfirmSignUp,
      resendConfirmationCode: mockResendConfirmationCode,
      isLoading: false,
      user: null,
      isAuthenticated: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })
  })

  it('renders confirmation form with all elements', () => {
    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    expect(screen.getByText('Check your email')).toBeInTheDocument()
    expect(screen.getByText(/We've sent a confirmation code to your email address/)).toBeInTheDocument()
    expect(screen.getByLabelText('Confirmation Code')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm Account' })).toBeInTheDocument()
    expect(screen.getByText('Resend code')).toBeInTheDocument()
    expect(screen.getByText('Back to sign up')).toBeInTheDocument()
  })

  it('validates confirmation code format', async () => {
    const user = userEvent.setup()
    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    const codeInput = screen.getByLabelText('Confirmation Code')
    
    // Test empty code
    await user.click(screen.getByRole('button', { name: 'Confirm Account' }))

    await waitFor(() => {
      expect(screen.getByText('Confirmation code is required')).toBeInTheDocument()
    })

    // Test invalid format
    await user.type(codeInput, '12345')
    await user.click(screen.getByRole('button', { name: 'Confirm Account' }))

    await waitFor(() => {
      expect(screen.getByText('Confirmation code must be 6 digits')).toBeInTheDocument()
    })
  })

  it('submits form with valid confirmation code', async () => {
    const user = userEvent.setup()
    mockConfirmSignUp.mockResolvedValue({ success: true })

    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    await user.type(screen.getByLabelText('Confirmation Code'), '123456')
    await user.click(screen.getByRole('button', { name: 'Confirm Account' }))

    await waitFor(() => {
      expect(mockConfirmSignUp).toHaveBeenCalledWith('testuser', '123456')
    })
  })

  it('displays success message and calls onConfirmationSuccess', async () => {
    const user = userEvent.setup()
    mockConfirmSignUp.mockResolvedValue({ success: true })

    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    await user.type(screen.getByLabelText('Confirmation Code'), '123456')
    await user.click(screen.getByRole('button', { name: 'Confirm Account' }))

    await waitFor(() => {
      expect(screen.getByText('Account confirmed successfully!')).toBeInTheDocument()
    })

    // Wait for the timeout to call onConfirmationSuccess
    await waitFor(() => {
      expect(mockOnConfirmationSuccess).toHaveBeenCalled()
    }, { timeout: 2000 })
  })

  it('displays error message on confirmation failure', async () => {
    const user = userEvent.setup()
    mockConfirmSignUp.mockResolvedValue({ success: false, error: 'Invalid confirmation code' })

    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    await user.type(screen.getByLabelText('Confirmation Code'), '123456')
    await user.click(screen.getByRole('button', { name: 'Confirm Account' }))

    await waitFor(() => {
      expect(screen.getByText('Invalid confirmation code')).toBeInTheDocument()
    })
  })

  it('resends confirmation code', async () => {
    const user = userEvent.setup()
    mockResendConfirmationCode.mockResolvedValue({ success: true })

    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    await user.click(screen.getByText('Resend code'))

    await waitFor(() => {
      expect(mockResendConfirmationCode).toHaveBeenCalledWith('testuser')
      expect(screen.getByText('Confirmation code sent! Check your email.')).toBeInTheDocument()
    })
  })

  it('displays error when resend fails', async () => {
    const user = userEvent.setup()
    mockResendConfirmationCode.mockResolvedValue({ success: false, error: 'Resend failed' })

    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    await user.click(screen.getByText('Resend code'))

    await waitFor(() => {
      expect(screen.getByText('Resend failed')).toBeInTheDocument()
    })
  })

  it('shows loading state during confirmation', async () => {
    mockUseAuth.mockReturnValue({
      confirmSignUp: mockConfirmSignUp,
      resendConfirmationCode: mockResendConfirmationCode,
      isLoading: true,
      user: null,
      isAuthenticated: false,
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      resetPassword: vi.fn(),
      confirmResetPassword: vi.fn(),
    })

    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    expect(screen.getByText('Confirming...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirming/i })).toBeDisabled()
  })

  it('calls onBackToSignUp when back link is clicked', async () => {
    const user = userEvent.setup()
    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    await user.click(screen.getByText('Back to sign up'))
    expect(mockOnBackToSignUp).toHaveBeenCalled()
  })

  it('limits confirmation code input to 6 characters', async () => {
    const user = userEvent.setup()
    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    const codeInput = screen.getByLabelText('Confirmation Code')
    await user.type(codeInput, '1234567890')

    expect(codeInput).toHaveValue('123456')
  })

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup()
    render(
      <ConfirmSignUpForm
        username="testuser"
        onConfirmationSuccess={mockOnConfirmationSuccess}
        onBackToSignUp={mockOnBackToSignUp}
      />
    )

    const codeInput = screen.getByLabelText('Confirmation Code')
    const confirmButton = screen.getByRole('button', { name: 'Confirm Account' })

    // Tab navigation
    await user.tab()
    expect(codeInput).toHaveFocus()

    await user.tab()
    expect(confirmButton).toHaveFocus()
  })
})