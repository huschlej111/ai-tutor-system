import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'
import { AuthService } from '../services/auth'

// Mock the AuthService
vi.mock('../services/auth', () => ({
  AuthService: {
    getCurrentUser: vi.fn(),
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    confirmSignUp: vi.fn(),
    resendConfirmationCode: vi.fn(),
    resetPassword: vi.fn(),
    confirmResetPassword: vi.fn(),
  },
}))

// Mock AWS Amplify Hub
vi.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: vi.fn(() => vi.fn()), // Return unsubscribe function
  },
}))

const mockAuthService = vi.mocked(AuthService)

// Test component to access the context
const TestComponent = () => {
  const auth = useAuth()
  return (
    <div>
      <div data-testid="user">{auth.user ? auth.user.username : 'null'}</div>
      <div data-testid="loading">{auth.isLoading.toString()}</div>
      <div data-testid="authenticated">{auth.isAuthenticated.toString()}</div>
      <button onClick={() => auth.signIn('test', 'password')}>Sign In</button>
      <button onClick={() => auth.signOut()}>Sign Out</button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('throws error when useAuth is used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    expect(() => {
      render(<TestComponent />)
    }).toThrow('useAuth must be used within an AuthProvider')
    
    consoleSpy.mockRestore()
  })

  it('provides initial auth state', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Initially loading should be true
    expect(screen.getByTestId('loading')).toHaveTextContent('true')
    
    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('null')
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
  })

  it('sets user when getCurrentUser succeeds', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        userId: '123',
        username: 'testuser',
        signInDetails: { loginId: 'test@example.com' },
      },
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('testuser')
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })
  })

  it('handles signIn success', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.signIn.mockResolvedValue({ success: true })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Wait for initial loading
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    // Mock successful getCurrentUser after sign in
    mockAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        userId: '123',
        username: 'testuser',
        signInDetails: { loginId: 'test@example.com' },
      },
    })

    const signInButton = screen.getByText('Sign In')
    signInButton.click()

    await waitFor(() => {
      expect(mockAuthService.signIn).toHaveBeenCalledWith({
        username: 'test',
        password: 'password',
      })
    })
  })

  it('handles signIn failure', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.signIn.mockResolvedValue({ 
      success: false, 
      error: 'Invalid credentials' 
    })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signInButton = screen.getByText('Sign In')
    signInButton.click()

    await waitFor(() => {
      expect(mockAuthService.signIn).toHaveBeenCalled()
    })
  })

  it('handles signOut', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({
      success: true,
      user: {
        userId: '123',
        username: 'testuser',
        signInDetails: { loginId: 'test@example.com' },
      },
    })
    mockAuthService.signOut.mockResolvedValue({ success: true })

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    const signOutButton = screen.getByText('Sign Out')
    signOutButton.click()

    await waitFor(() => {
      expect(mockAuthService.signOut).toHaveBeenCalled()
      expect(screen.getByTestId('user')).toHaveTextContent('null')
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    })
  })

  it('handles signUp success', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.signUp.mockResolvedValue({ 
      success: true, 
      isSignUpComplete: false 
    })

    const TestSignUpComponent = () => {
      const auth = useAuth()
      return (
        <button 
          onClick={() => auth.signUp({
            username: 'newuser',
            password: 'password',
            email: 'new@example.com'
          })}
        >
          Sign Up
        </button>
      )
    }

    render(
      <AuthProvider>
        <TestSignUpComponent />
      </AuthProvider>
    )

    const signUpButton = screen.getByText('Sign Up')
    signUpButton.click()

    await waitFor(() => {
      expect(mockAuthService.signUp).toHaveBeenCalledWith({
        username: 'newuser',
        password: 'password',
        email: 'new@example.com'
      })
    })
  })

  it('handles confirmSignUp', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.confirmSignUp.mockResolvedValue({ success: true })

    const TestConfirmComponent = () => {
      const auth = useAuth()
      return (
        <button onClick={() => auth.confirmSignUp('testuser', '123456')}>
          Confirm
        </button>
      )
    }

    render(
      <AuthProvider>
        <TestConfirmComponent />
      </AuthProvider>
    )

    const confirmButton = screen.getByText('Confirm')
    confirmButton.click()

    await waitFor(() => {
      expect(mockAuthService.confirmSignUp).toHaveBeenCalledWith({
        username: 'testuser',
        confirmationCode: '123456'
      })
    })
  })

  it('handles resendConfirmationCode', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.resendConfirmationCode.mockResolvedValue({ success: true })

    const TestResendComponent = () => {
      const auth = useAuth()
      return (
        <button onClick={() => auth.resendConfirmationCode('testuser')}>
          Resend
        </button>
      )
    }

    render(
      <AuthProvider>
        <TestResendComponent />
      </AuthProvider>
    )

    const resendButton = screen.getByText('Resend')
    resendButton.click()

    await waitFor(() => {
      expect(mockAuthService.resendConfirmationCode).toHaveBeenCalledWith('testuser')
    })
  })

  it('handles resetPassword', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.resetPassword.mockResolvedValue({ success: true })

    const TestResetComponent = () => {
      const auth = useAuth()
      return (
        <button onClick={() => auth.resetPassword('testuser')}>
          Reset Password
        </button>
      )
    }

    render(
      <AuthProvider>
        <TestResetComponent />
      </AuthProvider>
    )

    const resetButton = screen.getByText('Reset Password')
    resetButton.click()

    await waitFor(() => {
      expect(mockAuthService.resetPassword).toHaveBeenCalledWith({
        username: 'testuser'
      })
    })
  })

  it('handles confirmResetPassword', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    mockAuthService.confirmResetPassword.mockResolvedValue({ success: true })

    const TestConfirmResetComponent = () => {
      const auth = useAuth()
      return (
        <button onClick={() => auth.confirmResetPassword('testuser', '123456', 'newpassword')}>
          Confirm Reset
        </button>
      )
    }

    render(
      <AuthProvider>
        <TestConfirmResetComponent />
      </AuthProvider>
    )

    const confirmResetButton = screen.getByText('Confirm Reset')
    confirmResetButton.click()

    await waitFor(() => {
      expect(mockAuthService.confirmResetPassword).toHaveBeenCalledWith({
        username: 'testuser',
        confirmationCode: '123456',
        newPassword: 'newpassword'
      })
    })
  })

  it('handles errors gracefully', async () => {
    mockAuthService.getCurrentUser.mockRejectedValue(new Error('Network error'))

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
      expect(screen.getByTestId('user')).toHaveTextContent('null')
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    })
  })

  it('sets loading state correctly during operations', async () => {
    mockAuthService.getCurrentUser.mockResolvedValue({ success: false })
    
    // Mock a delayed signIn to test loading state
    mockAuthService.signIn.mockImplementation(() => 
      new Promise(resolve => 
        setTimeout(() => resolve({ success: true }), 100)
      )
    )

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    // Wait for initial loading to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const signInButton = screen.getByText('Sign In')
    signInButton.click()

    // Should show loading during sign in
    expect(screen.getByTestId('loading')).toHaveTextContent('true')

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })
  })
})