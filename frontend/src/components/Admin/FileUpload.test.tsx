import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import FileUpload from './FileUpload'

describe('FileUpload', () => {
  const mockOnFileSelect = vi.fn()
  const mockOnFileRemove = vi.fn()

  it('renders upload area when no file is selected', () => {
    render(
      <FileUpload
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
        onFileRemove={mockOnFileRemove}
      />
    )
    
    expect(screen.getByText('Upload JSON file')).toBeInTheDocument()
    expect(screen.getByText('Drag and drop your JSON file here, or click to browse')).toBeInTheDocument()
  })

  it('renders selected file when file is provided', () => {
    const mockFile = new File(['{}'], 'test.json', { type: 'application/json' })
    
    render(
      <FileUpload
        onFileSelect={mockOnFileSelect}
        selectedFile={mockFile}
        onFileRemove={mockOnFileRemove}
      />
    )
    
    expect(screen.getByText('test.json')).toBeInTheDocument()
    expect(screen.getByText(/JSON file/)).toBeInTheDocument()
  })

  it('shows disabled state when disabled prop is true', () => {
    render(
      <FileUpload
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
        onFileRemove={mockOnFileRemove}
        disabled={true}
      />
    )
    
    const uploadArea = screen.getByText('Upload JSON file').closest('[class*="border-2"]')
    expect(uploadArea).toHaveClass('opacity-50', 'cursor-not-allowed')
  })
})