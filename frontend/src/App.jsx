import { useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function readResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
  return data
}

export default function App() {
  const [document, setDocument] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [status, setStatus] = useState('Upload a lecture PDF to get started.')
  const [busy, setBusy] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')

  async function upload(event) {
    event.preventDefault()
    if (!selectedFile) return setError('Please choose a PDF file.')
    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) return setError('Please upload a PDF file.')
    setBusy(true)
    setError('')
    setStatus('Uploading PDF and processing document...')
    const form = new FormData()
    form.append('file', selectedFile)
    try {
      const result = await readResponse(await fetch(`${API}/upload`, { method: 'POST', body: form }))
      setDocument(result)
      setMessages([])
      setStatus('Document processed and ready for questions.')
    } catch (err) {
      setStatus(document ? 'Previous document is still ready.' : 'Upload failed.')
      setError(err.message)
    } finally { setBusy(false) }
  }

  async function ask(event) {
    event.preventDefault()
    const text = question.trim()
    if (!text) return
    if (!document) return setError('Please upload a document first.')
    if (busy) return
    setQuestion('')
    setError('')
    setMessages(previous => [...previous, { role: 'user', text }])
    setBusy(true)
    try {
      const result = await readResponse(await fetch(`${API}/ask`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: text })
      }))
      setMessages(previous => [...previous, { role: 'assistant', text: result.answer, sources: result.sources }])
    } catch (err) {
      setMessages(previous => [...previous, { role: 'error', text: err.message }])
    } finally { setBusy(false) }
  }

  return <div className="layout">
    <aside className="sidebar">
      <div className="logo"><span className="logo-icon">✦</span> Study Assistant</div>
      <div className="side-label">YOUR DOCUMENT</div>
      <form onSubmit={upload} className="upload-card">
        <label className="file-picker">
          <span className="file-icon">↥</span>
          <strong>{selectedFile ? selectedFile.name : 'Choose a PDF'}</strong>
          <small>Lecture notes · PDF · Up to 15 MB</small>
          <input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={event => setSelectedFile(event.target.files[0] || null)} />
        </label>
        <button className="upload-button" disabled={busy || !selectedFile}>{busy && !document ? 'Processing...' : 'Upload document'}</button>
      </form>
      {document && <div className="document-card"><span className="doc-icon">▤</span><span><strong title={document.document}>{document.document}</strong><small>{document.pages} text pages · Ready ✓</small></span></div>}
      <div className="status" aria-live="polite">{status}</div>
      <div className="sidebar-bottom">Answers grounded in your notes.<br/>Always check the cited pages.</div>
    </aside>
    <main className="main">
      <header><div><strong>Ask your notes</strong><span>Find answers with source pages</span></div><div className="badge">RAG powered</div></header>
      <section className="conversation" aria-live="polite">
        {messages.length === 0 && <div className="welcome"><div className="welcome-icon">✦</div><h1>Make sense of your notes.</h1><p>Upload a PDF, ask a question, and get an answer with the pages used to find it.</p><div className="hint">Try: “What are the main concepts in this lecture?”</div></div>}
        {messages.map((message, index) => <article key={index} className={`message ${message.role}`}><div className="avatar">{message.role === 'user' ? 'You' : '✦'}</div><div className="message-body"><div className="speaker">{message.role === 'user' ? 'You' : message.role === 'error' ? 'Error' : 'Study Assistant'}</div><p>{message.text}</p>{message.sources?.length > 0 && <div className="sources"><strong>Retrieved sources</strong><div>{message.sources.map((source, i) => <span className="source" key={i}>{source.document} · Page {source.page}</span>)}</div></div>}</div></article>)}
        {busy && document && <div className="thinking">✦ {status.startsWith('Uploading') ? 'Processing document...' : 'Thinking...'}</div>}
      </section>
      <div className="composer-wrap">{error && <div className="error-banner" role="alert">{error}</div>}<form onSubmit={ask} className="composer"><input aria-label="Ask a question" placeholder={document ? 'Ask something about your notes...' : 'Upload a PDF to begin...'} value={question} disabled={!document || busy} maxLength={2000} onChange={event => setQuestion(event.target.value)} /><button disabled={!document || busy || !question.trim()} aria-label="Send question">↑</button></form><small className="fine-print">Answers are generated from retrieved text. Verify important details in the PDF.</small></div>
    </main>
  </div>
}
