import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import BatchUpload from './BatchUpload'

// Mock the API client
vi.mock('../../services/api', () => ({
  apiClient: {
    validateBatchUpload: vi.fn(),
    processBatchUpload: vi.fn(),
    getUploadHistory: vi.fn()
  }
}))

describe('BatchUpload', () => {
  it('renders file upload interface initially', () => {
    render(<BatchUpload />)
    
    expect(screen.getByText('Batch Upload')).toBeInTheDocument()
    expect(screen.getByText('Select JSON File')).toBeInTheDocument()
    expect(screen.getByText('Upload JSON file')).toBeInTheDocument()
  })

  it('shows file format requirements', () => {
    render(<BatchUpload />)
    
    expect(screen.getByText('File Format Requirements')).toBeInTheDocument()
    expect(screen.getByText('File must be in JSON format')).toBeInTheDocument()
    expect(screen.getByText(/Must include batch_metadata/)).toBeInTheDocument()
  })

  it('displays step indicator', () => {
    render(<BatchUpload />)
    
    expect(screen.getByText('Select File')).toBeInTheDocument()
    expect(screen.getByText('Validate')).toBeInTheDocument()
    expect(screen.getByText('Upload')).toBeInTheDocument()
  })
})