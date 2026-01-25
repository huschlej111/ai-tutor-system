import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import AdminPanel from './AdminPanel'

// Mock the API client
vi.mock('../services/api', () => ({
  apiClient: {
    validateBatchUpload: vi.fn(),
    processBatchUpload: vi.fn(),
    getUploadHistory: vi.fn().mockResolvedValue([])
  }
}))

describe('AdminPanel', () => {
  it('renders admin panel with tabs', () => {
    render(<AdminPanel />)
    
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByText('Manage batch uploads and system administration.')).toBeInTheDocument()
    expect(screen.getAllByText('Batch Upload')).toHaveLength(2) // Tab and content header
    expect(screen.getByText('Upload History')).toBeInTheDocument()
  })

  it('shows batch upload interface by default', () => {
    render(<AdminPanel />)
    
    expect(screen.getByText('Select JSON File')).toBeInTheDocument()
    expect(screen.getByText('Upload JSON file')).toBeInTheDocument()
  })
})