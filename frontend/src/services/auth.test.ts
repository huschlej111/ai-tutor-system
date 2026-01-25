import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthService } from './auth'
import * as amplifyAuth from 'aws-amplify/auth'

// Mock AWS Amplify auth functions
vi.mock('aws-amplify/auth', () => ({
  signUp: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
  confirmSignUp: vi.fn(),
  resendSignUpCode: vi.fn(),
  resetPassword: vi.fn(),
  confirmResetPassword: vi.fn(),
  getCurrentUser: vi.fn(),
  fetchAuthSession: vi.fn(),
}))

const mockAmplifyAuth = vi.mocked(amplifyAuth)

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Suppress console.error for tests
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  describe('signUp', () => {
    it('successfully signs up a user', async () => {
      const mockResponse = {
        isSignUpComplete: false,
        userId: '123',
        nextStep: { signUpStep: 'CONFIRM_SIGN_UP' },
      }
      mockAmplifyAuth.signUp.mockResolvedValue(mockResponse)

      const result = await AuthService.signUp({
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com',
        given_name: 'Test',
        family_name: 'User',
      })

      expect(mockAmplifyAuth.signUp).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        options: {
          userAttributes: {
            email: 'test@example.com',
            given_name: 'Test',
            family_name: 'User',
          },
        },
      })

      expect(result).toEqual({
        success: true,
        isSignUpComplete: false,
        userId: '123',
        nextStep: { signUpStep: 'CONFIRM_SIGN_UP' },
      })
    })

    it('handles sign up without optional attributes', async () => {
      const mockResponse = {
        isSignUpComplete: false,
        userId: '123',
        nextStep: { signUpStep: 'CONFIRM_SIGN_UP' },
      }
      mockAmplifyAuth.signUp.mockResolvedValue(mockResponse)

      const result = await AuthService.signUp({
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com',
      })

      expect(mockAmplifyAuth.signUp).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        options: {
          userAttributes: {
            email: 'test@example.com',
          },
        },
      })

      expect(result.success).toBe(true)
    })

    it('handles sign up error', async () => {
      const error = new Error('Username already exists')
      mockAmplifyAuth.signUp.mockRejectedValue(error)

      const result = await AuthService.signUp({
        username: 'existinguser',
        password: 'password123',
        email: 'test@example.com',
      })

      expect(result).toEqual({
        success: false,
        error: 'Username already exists',
      })
    })

    it('handles non-Error exceptions', async () => {
      mockAmplifyAuth.signUp.mockRejectedValue('String error')

      const result = await AuthService.signUp({
        username: 'testuser',
        password: 'password123',
        email: 'test@example.com',
      })

      expect(result).toEqual({
        success: false,
        error: 'Sign up failed',
      })
    })
  })

  describe('signIn', () => {
    it('successfully signs in a user', async () => {
      const mockResponse = {
        isSignedIn: true,
        nextStep: { signInStep: 'DONE' },
      }
      mockAmplifyAuth.signIn.mockResolvedValue(mockResponse)

      const result = await AuthService.signIn({
        username: 'testuser',
        password: 'password123',
      })

      expect(mockAmplifyAuth.signIn).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
      })

      expect(result).toEqual({
        success: true,
        isSignedIn: true,
        nextStep: { signInStep: 'DONE' },
      })
    })

    it('handles sign in error', async () => {
      const error = new Error('Incorrect username or password')
      mockAmplifyAuth.signIn.mockRejectedValue(error)

      const result = await AuthService.signIn({
        username: 'testuser',
        password: 'wrongpassword',
      })

      expect(result).toEqual({
        success: false,
        error: 'Incorrect username or password',
      })
    })
  })

  describe('signOut', () => {
    it('successfully signs out', async () => {
      mockAmplifyAuth.signOut.mockResolvedValue(undefined)

      const result = await AuthService.signOut()

      expect(mockAmplifyAuth.signOut).toHaveBeenCalled()
      expect(result).toEqual({ success: true })
    })

    it('handles sign out error', async () => {
      const error = new Error('Sign out failed')
      mockAmplifyAuth.signOut.mockRejectedValue(error)

      const result = await AuthService.signOut()

      expect(result).toEqual({
        success: false,
        error: 'Sign out failed',
      })
    })
  })

  describe('confirmSignUp', () => {
    it('successfully confirms sign up', async () => {
      const mockResponse = {
        isSignUpComplete: true,
        nextStep: { signUpStep: 'DONE' },
      }
      mockAmplifyAuth.confirmSignUp.mockResolvedValue(mockResponse)

      const result = await AuthService.confirmSignUp({
        username: 'testuser',
        confirmationCode: '123456',
      })

      expect(mockAmplifyAuth.confirmSignUp).toHaveBeenCalledWith({
        username: 'testuser',
        confirmationCode: '123456',
      })

      expect(result).toEqual({
        success: true,
        isSignUpComplete: true,
        nextStep: { signUpStep: 'DONE' },
      })
    })

    it('handles confirmation error', async () => {
      const error = new Error('Invalid verification code')
      mockAmplifyAuth.confirmSignUp.mockRejectedValue(error)

      const result = await AuthService.confirmSignUp({
        username: 'testuser',
        confirmationCode: '123456',
      })

      expect(result).toEqual({
        success: false,
        error: 'Invalid verification code',
      })
    })
  })

  describe('resendConfirmationCode', () => {
    it('successfully resends confirmation code', async () => {
      mockAmplifyAuth.resendSignUpCode.mockResolvedValue(undefined)

      const result = await AuthService.resendConfirmationCode('testuser')

      expect(mockAmplifyAuth.resendSignUpCode).toHaveBeenCalledWith({
        username: 'testuser',
      })

      expect(result).toEqual({ success: true })
    })

    it('handles resend error', async () => {
      const error = new Error('User not found')
      mockAmplifyAuth.resendSignUpCode.mockRejectedValue(error)

      const result = await AuthService.resendConfirmationCode('testuser')

      expect(result).toEqual({
        success: false,
        error: 'User not found',
      })
    })
  })

  describe('resetPassword', () => {
    it('successfully initiates password reset', async () => {
      const mockResponse = {
        nextStep: { resetPasswordStep: 'CONFIRM_RESET_PASSWORD_WITH_CODE' },
      }
      mockAmplifyAuth.resetPassword.mockResolvedValue(mockResponse)

      const result = await AuthService.resetPassword({
        username: 'testuser',
      })

      expect(mockAmplifyAuth.resetPassword).toHaveBeenCalledWith({
        username: 'testuser',
      })

      expect(result).toEqual({
        success: true,
        nextStep: { resetPasswordStep: 'CONFIRM_RESET_PASSWORD_WITH_CODE' },
      })
    })

    it('handles reset password error', async () => {
      const error = new Error('User not found')
      mockAmplifyAuth.resetPassword.mockRejectedValue(error)

      const result = await AuthService.resetPassword({
        username: 'nonexistent',
      })

      expect(result).toEqual({
        success: false,
        error: 'User not found',
      })
    })
  })

  describe('confirmResetPassword', () => {
    it('successfully confirms password reset', async () => {
      mockAmplifyAuth.confirmResetPassword.mockResolvedValue(undefined)

      const result = await AuthService.confirmResetPassword({
        username: 'testuser',
        confirmationCode: '123456',
        newPassword: 'newpassword123',
      })

      expect(mockAmplifyAuth.confirmResetPassword).toHaveBeenCalledWith({
        username: 'testuser',
        confirmationCode: '123456',
        newPassword: 'newpassword123',
      })

      expect(result).toEqual({ success: true })
    })

    it('handles confirm reset password error', async () => {
      const error = new Error('Invalid verification code')
      mockAmplifyAuth.confirmResetPassword.mockRejectedValue(error)

      const result = await AuthService.confirmResetPassword({
        username: 'testuser',
        confirmationCode: '123456',
        newPassword: 'newpassword123',
      })

      expect(result).toEqual({
        success: false,
        error: 'Invalid verification code',
      })
    })
  })

  describe('getCurrentUser', () => {
    it('successfully gets current user', async () => {
      const mockUser = {
        userId: '123',
        username: 'testuser',
        signInDetails: { loginId: 'test@example.com' },
      }
      mockAmplifyAuth.getCurrentUser.mockResolvedValue(mockUser)

      const result = await AuthService.getCurrentUser()

      expect(mockAmplifyAuth.getCurrentUser).toHaveBeenCalled()
      expect(result).toEqual({
        success: true,
        user: mockUser,
      })
    })

    it('handles get current user error', async () => {
      const error = new Error('No current user')
      mockAmplifyAuth.getCurrentUser.mockRejectedValue(error)

      const result = await AuthService.getCurrentUser()

      expect(result).toEqual({
        success: false,
        error: 'No current user',
      })
    })
  })

  describe('getAuthSession', () => {
    it('successfully gets auth session', async () => {
      const mockSession = {
        tokens: {
          accessToken: { toString: () => 'access-token' },
          idToken: { toString: () => 'id-token' },
        },
      }
      mockAmplifyAuth.fetchAuthSession.mockResolvedValue(mockSession)

      const result = await AuthService.getAuthSession()

      expect(mockAmplifyAuth.fetchAuthSession).toHaveBeenCalled()
      expect(result).toEqual({
        success: true,
        session: mockSession,
        tokens: mockSession.tokens,
      })
    })

    it('handles get auth session error', async () => {
      const error = new Error('No valid session')
      mockAmplifyAuth.fetchAuthSession.mockRejectedValue(error)

      const result = await AuthService.getAuthSession()

      expect(result).toEqual({
        success: false,
        error: 'No valid session',
      })
    })
  })

  describe('error handling', () => {
    it('handles string errors correctly', async () => {
      mockAmplifyAuth.signIn.mockRejectedValue('String error message')

      const result = await AuthService.signIn({
        username: 'test',
        password: 'test',
      })

      expect(result).toEqual({
        success: false,
        error: 'Sign in failed',
      })
    })

    it('handles null/undefined errors', async () => {
      mockAmplifyAuth.signIn.mockRejectedValue(null)

      const result = await AuthService.signIn({
        username: 'test',
        password: 'test',
      })

      expect(result).toEqual({
        success: false,
        error: 'Sign in failed',
      })
    })

    it('logs errors to console', async () => {
      const consoleSpy = vi.spyOn(console, 'error')
      const error = new Error('Test error')
      mockAmplifyAuth.signIn.mockRejectedValue(error)

      await AuthService.signIn({
        username: 'test',
        password: 'test',
      })

      expect(consoleSpy).toHaveBeenCalledWith('Sign in error:', error)
    })
  })
})