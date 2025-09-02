import { useState } from 'react'
import { api } from './api'

type DocumentResponse = {
  id: string
  filename: string
  doc_type: string
  ingest_ts: string
  extracted_data: Record<string, any>
}

function formatDocType(type: string | undefined) {
  if (!type) return ''
  const map: Record<string, string> = {
    valuation_reports: 'Valuation Report',
    capital_call_letter: 'Capital Call Notice',
    distribution_notice: 'Distribution Notice',
    quarterly_update: 'Quarterly Update',
  }
  if (map[type]) return map[type]
  // Convert snake_case to Title Case
  return type
    .split('_')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(' ')
}

function prettyDate(iso?: string) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function SectionTitle({ children }: { children: string }) {
  return <h2 className="text-lg font-semibold text-gray-800 mt-6 mb-2">{children}</h2>
}

function KeyValue({ label, value }: { label: string, value: any }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-1 text-sm">
      <div className="text-gray-600">{label}</div>
      <div className="col-span-2 break-words">{String(value)}</div>
    </div>
  )
}

function RenderValue({ value }: { value: any }) {
  if (value === null || value === undefined) return <span className="text-gray-400">—</span>
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-400">[]</span>
    // Render array of objects or primitives
    const isObjArray = value.every(v => v && typeof v === 'object' && !Array.isArray(v))
    if (isObjArray) {
      const keys = Array.from(new Set(value.flatMap((v: any) => Object.keys(v))))
      return (
        <div className="overflow-x-auto">
          <table className="min-w-full border border-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {keys.map(k => <th key={k} className="text-left px-3 py-2 border-b">{k}</th>)}
              </tr>
            </thead>
            <tbody>
              {value.map((row: any, idx: number) => (
                <tr key={idx} className="odd:bg-white even:bg-gray-50">
                  {keys.map(k => <td key={k} className="px-3 py-2 border-b align-top">{String(row?.[k] ?? '')}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    return (
      <ul className="list-disc ml-6 space-y-1">
        {value.map((v, i) => <li key={i} className="break-words">{String(v)}</li>)}
      </ul>
    )
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value)
    if (entries.length === 0) return <span className="text-gray-400">{'{}'}</span>
    return (
      <div className="border border-gray-200 rounded-md divide-y">
        {entries.map(([k, v]) => (
          <div key={k} className="grid grid-cols-3 gap-2 px-3 py-2">
            <div className="text-gray-600">{k}</div>
            <div className="col-span-2"><RenderValue value={v} /></div>
          </div>
        ))}
      </div>
    )
  }
  return <span>{String(value)}</span>
}

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [doc, setDoc] = useState<DocumentResponse | null>(null)
  const [showRaw, setShowRaw] = useState(false)

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  const onUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setDoc(null)
    try {
      const { document_id } = await api.upload(file)
      const res = await api.getDocument(document_id)
      setDoc(res)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900">Alternative Investments Document Intelligence</h1>
        <p className="text-gray-600 mt-1">Upload a PDF to classify it and extract key fields.</p>

        <SectionTitle>Upload</SectionTitle>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
          className="border-2 border-dashed border-gray-300 rounded-lg p-6 bg-white flex flex-col items-center justify-center text-center"
        >
          <input
            id="fileInput"
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <p className="text-gray-700">Drag and drop a PDF here, or</p>
          <label htmlFor="fileInput" className="mt-2 inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer">
            Choose File
          </label>
          {file && (
            <div className="mt-3 text-sm text-gray-600">Selected: {file.name}</div>
          )}
          <button
            className="mt-4 inline-flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            onClick={onUpload}
            disabled={!file || loading}
          >
            {loading ? 'Processing…' : 'Upload & Process'}
          </button>
          {error && <div className="mt-2 text-sm text-red-600">{error}</div>}
        </div>

        {doc && (
          <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-xl font-semibold text-gray-900">Result</h3>
            <div className="mt-4 border-t pt-4">
              <KeyValue label="Filename" value={doc.filename} />
              <KeyValue label="Type" value={formatDocType(doc.doc_type)} />
              <KeyValue label="Ingested" value={prettyDate(doc.ingest_ts)} />
            </div>

            <SectionTitle>Extracted Data</SectionTitle>
            <div className="mt-2">
              <RenderValue value={{
                ...doc.extracted_data,
                // Hide _ai_raw from the pretty view; still available in Raw JSON
                _ai_raw: undefined,
              }} />
            </div>

            <div className="mt-6">
              <button
                className="text-sm text-blue-600 hover:text-blue-700"
                onClick={() => setShowRaw(s => !s)}
              >
                {showRaw ? 'Hide Raw JSON' : 'View Raw JSON'}
              </button>
              {showRaw && (
                <pre className="mt-3 text-xs bg-gray-900 text-gray-100 p-3 rounded overflow-auto max-h-96">
                  {JSON.stringify(doc, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


