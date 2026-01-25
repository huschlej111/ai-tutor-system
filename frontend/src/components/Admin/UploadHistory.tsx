import React, { useEffect, useState } from 'react'
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline'
import { apiClient, UploadHistoryItem } from '../../services/api'

const UploadHistory: React.FC = () => {
  const [uploads, setUploads] = useState<UploadHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadUploadHistory()
  }, [])

  const loadUploadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const history = await apiClient.getUploadHistory()
      setUploads(history)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load upload history')
    } finally {
      setLoading(false)
    }
  }

  const toggleExpanded = (uploadId: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(uploadId)) {
      newExpanded.delete(uploadId)
    } else {
      newExpanded.add(uploadId)
    }
    setExpandedItems(newExpanded)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case 'processing':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Completed'
      case 'failed':
        return 'Failed'
      case 'processing':
        return 'Processing'
      default:
        return 'Unknown'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading upload history...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <XCircleIcon className="h-5 w-5 text-red-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error Loading History</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
            <button
              onClick={loadUploadHistory}
              className="mt-2 text-sm text-red-600 hover:text-red-500 underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (uploads.length === 0) {
    return (
      <div className="text-center py-8">
        <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No upload history</h3>
        <p className="mt-1 text-sm text-gray-500">
          Upload your first batch file to see history here.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Upload History</h3>
        <button
          onClick={loadUploadHistory}
          className="text-sm text-blue-600 hover:text-blue-500"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-3">
        {uploads.map((upload) => (
          <div key={upload.id} className="border border-gray-200 rounded-lg">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => toggleExpanded(upload.id)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    {expandedItems.has(upload.id) ? (
                      <ChevronDownIcon className="h-4 w-4 text-gray-500" />
                    ) : (
                      <ChevronRightIcon className="h-4 w-4 text-gray-500" />
                    )}
                  </button>
                  <DocumentTextIcon className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="font-medium text-gray-900">{upload.filename}</p>
                    <p className="text-sm text-gray-500">
                      {formatDate(upload.uploaded_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      {upload.metadata.domains_created} domains, {upload.metadata.terms_created} terms
                    </p>
                    <p className="text-xs text-gray-500">
                      {upload.metadata.total_items} total items
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(upload.status)}
                    <span className={`text-sm font-medium ${
                      upload.status === 'completed' ? 'text-green-700' :
                      upload.status === 'failed' ? 'text-red-700' :
                      'text-yellow-700'
                    }`}>
                      {getStatusText(upload.status)}
                    </span>
                  </div>
                </div>
              </div>

              {expandedItems.has(upload.id) && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="font-medium text-gray-700">Upload Details</p>
                      <div className="mt-1 space-y-1 text-gray-600">
                        <p>Upload ID: {upload.id}</p>
                        <p>Processed: {upload.processed_at ? formatDate(upload.processed_at) : 'Not processed'}</p>
                        <p>Subject Count: {upload.subject_count}</p>
                      </div>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Results</p>
                      <div className="mt-1 space-y-1 text-gray-600">
                        <p>Domains Created: {upload.metadata.domains_created}</p>
                        <p>Terms Created: {upload.metadata.terms_created}</p>
                        <p>Total Items: {upload.metadata.total_items}</p>
                      </div>
                    </div>
                  </div>
                  
                  {upload.error_message && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                      <p className="text-sm font-medium text-red-800">Error Details</p>
                      <p className="mt-1 text-sm text-red-700">{upload.error_message}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default UploadHistory