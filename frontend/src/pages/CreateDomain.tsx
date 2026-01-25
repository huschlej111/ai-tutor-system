import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiClient, Domain, Term, CreateDomainRequest, AddTermsRequest } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const CreateDomain = () => {
  const navigate = useNavigate()
  const { domainId } = useParams()
  const { user } = useAuth()
  const isEditing = Boolean(domainId)

  // Domain form state
  const [domainForm, setDomainForm] = useState<CreateDomainRequest>({
    name: '',
    description: ''
  })

  // Terms state
  const [terms, setTerms] = useState<{ term: string; definition: string }[]>([
    { term: '', definition: '' }
  ])

  // UI state
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [existingTerms, setExistingTerms] = useState<Term[]>([])

  // Load existing domain data if editing
  useEffect(() => {
    const loadDomain = async () => {
      if (!isEditing || !domainId) return

      try {
        setLoading(true)
        const [domain, domainTerms] = await Promise.all([
          apiClient.getDomain(domainId),
          apiClient.getTerms(domainId)
        ])

        setDomainForm({
          name: domain.name,
          description: domain.description
        })
        setExistingTerms(domainTerms)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load domain')
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      loadDomain()
    }
  }, [isEditing, domainId, user])

  const handleDomainChange = (field: keyof CreateDomainRequest, value: string) => {
    setDomainForm(prev => ({ ...prev, [field]: value }))
  }

  const handleTermChange = (index: number, field: 'term' | 'definition', value: string) => {
    setTerms(prev => prev.map((term, i) => 
      i === index ? { ...term, [field]: value } : term
    ))
  }

  const addTerm = () => {
    setTerms(prev => [...prev, { term: '', definition: '' }])
  }

  const removeTerm = (index: number) => {
    if (terms.length > 1) {
      setTerms(prev => prev.filter((_, i) => i !== index))
    }
  }

  const validateForm = () => {
    const errors: string[] = []

    // Validate domain
    if (!domainForm.name.trim()) {
      errors.push('Domain name is required')
    } else if (domainForm.name.length < 2 || domainForm.name.length > 100) {
      errors.push('Domain name must be between 2 and 100 characters')
    }

    if (!domainForm.description.trim()) {
      errors.push('Domain description is required')
    } else if (domainForm.description.length < 10 || domainForm.description.length > 500) {
      errors.push('Domain description must be between 10 and 500 characters')
    }

    // Validate terms (only if adding new terms)
    const validTerms = terms.filter(t => t.term.trim() || t.definition.trim())
    if (!isEditing && validTerms.length === 0) {
      errors.push('At least one term is required')
    }

    for (let i = 0; i < validTerms.length; i++) {
      const term = validTerms[i]
      if (!term.term.trim()) {
        errors.push(`Term ${i + 1}: Term name is required`)
      } else if (term.term.length < 2 || term.term.length > 200) {
        errors.push(`Term ${i + 1}: Term name must be between 2 and 200 characters`)
      }

      if (!term.definition.trim()) {
        errors.push(`Term ${i + 1}: Definition is required`)
      } else if (term.definition.length < 10 || term.definition.length > 1000) {
        errors.push(`Term ${i + 1}: Definition must be between 10 and 1000 characters`)
      }
    }

    return errors
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validationErrors = validateForm()
    if (validationErrors.length > 0) {
      setError(validationErrors.join('. '))
      return
    }

    try {
      setSaving(true)
      setError(null)

      let domain: Domain

      if (isEditing && domainId) {
        // Update existing domain
        await apiClient.updateDomain(domainId, domainForm)
        domain = { ...domainForm, id: domainId } as Domain
      } else {
        // Create new domain
        domain = await apiClient.createDomain(domainForm)
      }

      // Add terms if any are provided
      const validTerms = terms.filter(t => t.term.trim() && t.definition.trim())
      if (validTerms.length > 0) {
        const termsRequest: AddTermsRequest = { terms: validTerms }
        await apiClient.addTerms(domain.id, termsRequest)
      }

      navigate('/app/domains')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save domain')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteExistingTerm = async (termId: string) => {
    if (!domainId || !confirm('Are you sure you want to delete this term?')) return

    try {
      await apiClient.deleteTerm(domainId, termId)
      setExistingTerms(prev => prev.filter(t => t.id !== termId))
    } catch (err) {
      alert('Failed to delete term: ' + (err instanceof Error ? err.message : 'Unknown error'))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          {isEditing ? 'Edit Domain' : 'Create Domain'}
        </h1>
        <p className="page-subtitle">
          {isEditing 
            ? 'Update your knowledge domain and manage terms.'
            : 'Create a new knowledge domain with terms and definitions.'
          }
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Domain Information */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold mb-4">Domain Information</h2>
          
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Domain Name *
              </label>
              <input
                type="text"
                id="name"
                value={domainForm.name}
                onChange={(e) => handleDomainChange('name', e.target.value)}
                placeholder="e.g., AWS Certification, Python Basics"
                className="input w-full"
                maxLength={100}
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                {domainForm.name.length}/100 characters
              </p>
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                Description *
              </label>
              <textarea
                id="description"
                value={domainForm.description}
                onChange={(e) => handleDomainChange('description', e.target.value)}
                placeholder="Describe what this domain covers and what learners will gain..."
                className="input w-full h-24 resize-none"
                maxLength={500}
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                {domainForm.description.length}/500 characters
              </p>
            </div>
          </div>
        </div>

        {/* Existing Terms (for editing) */}
        {isEditing && existingTerms.length > 0 && (
          <div className="card p-6">
            <h2 className="text-xl font-semibold mb-4">Existing Terms ({existingTerms.length})</h2>
            <div className="space-y-4">
              {existingTerms.map((term) => (
                <div key={term.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">{term.term}</h4>
                      <p className="text-sm text-gray-600 mt-1">{term.definition}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteExistingTerm(term.id)}
                      className="ml-4 text-red-600 hover:text-red-700 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* New Terms */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              {isEditing ? 'Add New Terms' : 'Terms'}
            </h2>
            <button
              type="button"
              onClick={addTerm}
              className="btn btn-secondary btn-sm"
            >
              Add Term
            </button>
          </div>

          <div className="space-y-6">
            {terms.map((term, index) => (
              <div key={index} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-gray-900">Term {index + 1}</h3>
                  {terms.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeTerm(index)}
                      className="text-red-600 hover:text-red-700 text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Term Name
                    </label>
                    <input
                      type="text"
                      value={term.term}
                      onChange={(e) => handleTermChange(index, 'term', e.target.value)}
                      placeholder="e.g., Lambda Function, List Comprehension"
                      className="input w-full"
                      maxLength={200}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Definition
                    </label>
                    <textarea
                      value={term.definition}
                      onChange={(e) => handleTermChange(index, 'definition', e.target.value)}
                      placeholder="Provide a clear, comprehensive definition..."
                      className="input w-full h-20 resize-none"
                      maxLength={1000}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {!isEditing && (
            <p className="text-sm text-gray-500 mt-4">
              You can add more terms later after creating the domain.
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/app/domains')}
            className="btn btn-secondary"
            disabled={saving}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {isEditing ? 'Updating...' : 'Creating...'}
              </>
            ) : (
              isEditing ? 'Update Domain' : 'Create Domain'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default CreateDomain