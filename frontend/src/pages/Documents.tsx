import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentsApi } from '../api/documents'
import { useUIStore } from '../stores/uiStore'
import Card from '../components/common/Card'
import LoadingSpinner from '../components/common/LoadingSpinner'
import {
  DocumentTextIcon,
  LockClosedIcon,
  TrashIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline'

export default function Documents() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const queryClient = useQueryClient()
  const addNotification = useUIStore((state) => state.addNotification)

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentsApi.getDocuments({ ordering: '-uploaded_at' }),
  })

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => documentsApi.uploadDocument(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setSelectedFile(null)
      addNotification({
        type: 'success',
        title: 'Document Uploaded',
        message: 'Your document has been uploaded successfully',
      })
    },
    onError: () => {
      addNotification({
        type: 'error',
        title: 'Upload Failed',
        message: 'Failed to upload document. Please try again.',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      addNotification({
        type: 'success',
        title: 'Document Deleted',
        message: 'The document has been deleted successfully',
      })
    },
  })

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('name', selectedFile.name)

    uploadMutation.mutate(formData)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Document Manager</h1>
        <p className="text-gray-600 mt-1">Upload and manage your secure documents</p>
      </div>

      {/* Upload Section */}
      <Card title="Upload Document">
        <div className="space-y-4">
          <div>
            <label className="label">Select File</label>
            <input
              type="file"
              onChange={handleFileSelect}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {selectedFile && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-700">
                <span className="font-medium">Selected file:</span> {selectedFile.name}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Size: {formatBytes(selectedFile.size)}
              </p>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploadMutation.isPending}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </Card>

      {/* Documents List */}
      <Card
        title="Your Documents"
        subtitle={`${documents?.count || 0} documents`}
      >
        {documents?.results && documents.results.length > 0 ? (
          <div className="space-y-3">
            {documents.results.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-4 flex-1">
                  <div className="flex-shrink-0">
                    <DocumentTextIcon className="w-10 h-10 text-gray-400" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h4 className="font-medium text-gray-900 truncate">{doc.name}</h4>
                      {doc.is_encrypted && (
                        <LockClosedIcon className="w-4 h-4 text-green-600" title="Encrypted" />
                      )}
                      {doc.is_quarantined && (
                        <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded">
                          Quarantined
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 mt-1 text-sm text-gray-600">
                      <span>{formatBytes(doc.file_size)}</span>
                      <span>•</span>
                      <span>{doc.file_type}</span>
                      <span>•</span>
                      <span>Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                    </div>

                    {doc.encryption_type && (
                      <p className="text-xs text-green-600 mt-1">
                        Encryption: {doc.encryption_type}
                      </p>
                    )}

                    {doc.retention_date && (
                      <p className="text-xs text-orange-600 mt-1">
                        Scheduled deletion: {new Date(doc.retention_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <a
                    href={doc.file}
                    download
                    className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                    title="Download"
                  >
                    <ArrowDownTrayIcon className="w-5 h-5" />
                  </a>

                  <button
                    onClick={() => deleteMutation.mutate(doc.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <TrashIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <DocumentTextIcon className="w-12 h-12 mx-auto mb-2 text-gray-400" />
            <p>No documents uploaded</p>
            <p className="text-sm">Upload your first document to get started</p>
          </div>
        )}
      </Card>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}
