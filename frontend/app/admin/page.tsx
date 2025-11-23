'use client'

import { useEffect, useState } from 'react'
import Navbar from '@/components/Navbar'

interface ScraperLog {
  id: number
  status: string
  records_extracted: number
  error_message: string | null
  run_date: string
  created_at: string
}

interface ScraperStatus {
  status: string
  last_run: string | null
  last_status: string | null
  total_records: number
  last_extraction_count: number
}

export default function AdminPage() {
  const [logs, setLogs] = useState<ScraperLog[]>([])
  const [status, setStatus] = useState<ScraperStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [targetDate, setTargetDate] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [liveLogs, setLiveLogs] = useState<string[]>([])

  const stopScraper = async () => {
    try {
      const token = localStorage.getItem('token')
      await fetch(`/api/proxy/api/scraper/stop`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setMessage('Stop requested...')
    } catch (err) {
      console.error('Failed to stop scraper', err)
    }
  }

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    if (triggering) {
      setLiveLogs([])
      intervalId = setInterval(async () => {
        try {
          const token = localStorage.getItem('token')
          const res = await fetch(`/api/proxy/api/scraper/progress`, {
             headers: { 'Authorization': `Bearer ${token}` }
          })
          if (res.ok) {
            const data = await res.json()
            if (data.logs) {
                setLiveLogs(data.logs)
            }
          }
        } catch (e) {
          console.error("Polling error", e)
        }
      }, 2000)
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [triggering])

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        setError('Please login first')
        setLoading(false)
        return
      }

      const headers = { 'Authorization': `Bearer ${token}` }
      
      const [statusRes, logsRes] = await Promise.all([
        fetch(`/api/proxy/api/scraper/status`, { headers }),
        fetch(`/api/proxy/api/scraper/logs`, { headers })
      ])
      
      if (statusRes.ok) {
        const statusData = await statusRes.json()
        setStatus(statusData)
      }
      
      if (logsRes.ok) {
        const logsData = await logsRes.json()
        setLogs(logsData)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const triggerScraper = async () => {
    setTriggering(true)
    setMessage('')
    setError('')
    
    try {
      const token = localStorage.getItem('token')
      let url = `/api/proxy/api/scraper/trigger`
      if (targetDate) {
        url += `?target_date=${targetDate}`
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      const data = await response.json()
      
      if (response.ok) {
        setMessage(`Scraper completed! Extracted ${data.records_extracted} records.`)
        fetchData()
      } else {
        setError(data.message || 'Failed to trigger scraper')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to trigger scraper')
    } finally {
      setTriggering(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <div>
      <Navbar />
      <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '2rem' }}>Admin Dashboard</h1>
        
        {error && (
          <div style={{ 
            background: '#ffebee', 
            color: '#c62828', 
            padding: '1rem',
            borderRadius: '4px',
            marginBottom: '1rem'
          }}>
            {error}
          </div>
        )}
        
        {message && (
          <div style={{ 
            background: '#e8f5e9', 
            color: '#2e7d32', 
            padding: '1rem',
            borderRadius: '4px',
            marginBottom: '1rem'
          }}>
            {message}
          </div>
        )}
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>Loading...</div>
        ) : (
          <>
            <div style={{ 
              background: 'white', 
              padding: '2rem', 
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              marginBottom: '2rem'
            }}>
              <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Scraper Status</h2>
              
              <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                    Select Date to Scrape (Optional)
                  </label>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}
                  />
                </div>
                <button
                  onClick={triggerScraper}
                  disabled={triggering}
                  style={{
                    background: triggering ? '#ccc' : '#2196f3',
                    color: 'white',
                    border: 'none',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '4px',
                    cursor: triggering ? 'not-allowed' : 'pointer',
                    fontWeight: 'bold',
                    height: '46px'
                  }}
                >
                  {triggering ? 'Running Scraper...' : 'Run Scraper Now'}
                </button>
                {triggering && (
                  <button
                    onClick={stopScraper}
                    style={{
                      background: '#d32f2f',
                      color: 'white',
                      border: 'none',
                      padding: '0.75rem 1.5rem',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      height: '46px'
                    }}
                  >
                    Stop
                  </button>
                )}
              </div>
              
              {status && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div>
                    <div style={{ color: '#666', fontSize: '0.875rem' }}>Status</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: status.status === 'success' ? '#2e7d32' : '#666' }}>
                      {status.status || 'Never Run'}
                    </div>
                  </div>
                  
                  <div>
                    <div style={{ color: '#666', fontSize: '0.875rem' }}>Last Run</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
                      {status.last_run ? new Date(status.last_run).toLocaleString() : 'N/A'}
                    </div>
                  </div>
                  
                  <div>
                    <div style={{ color: '#666', fontSize: '0.875rem' }}>Total Records</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#1976d2' }}>
                      {status.total_records}
                    </div>
                  </div>
                  
                  <div>
                    <div style={{ color: '#666', fontSize: '0.875rem' }}>Last Extraction Count</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
                      {status.last_extraction_count}
                    </div>
                  </div>
                </div>
              )}

              {triggering && (
                <div style={{ marginBottom: '1.5rem', background: '#f5f5f5', padding: '1rem', borderRadius: '4px', maxHeight: '300px', overflowY: 'auto' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Live Logs</h3>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.9rem', whiteSpace: 'pre-wrap' }}>
                    {liveLogs.length > 0 ? liveLogs.join('\n') : 'Waiting for logs...'}
                  </div>
                </div>
              )}
              
              <button
                onClick={triggerScraper}
                disabled={triggering}
                style={{
                  background: '#2e7d32',
                  color: 'white',
                  padding: '0.75rem 2rem',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '1rem',
                  cursor: triggering ? 'not-allowed' : 'pointer',
                  opacity: triggering ? 0.6 : 1
                }}
              >
                {triggering ? 'Running Scraper...' : 'Trigger Scraper Manually'}
              </button>
            </div>
            
            <div style={{ 
              background: 'white', 
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              overflow: 'hidden'
            }}>
              <h2 style={{ fontSize: '1.5rem', padding: '1.5rem', borderBottom: '1px solid #eee' }}>Scraper Logs</h2>
              
              {logs.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
                  No logs available
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Status</th>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Run Date</th>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Records Extracted</th>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Error Message</th>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Created At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
                        <td style={{ padding: '1rem' }}>
                          <span style={{
                            background: log.status === 'success' ? '#e8f5e9' : '#ffebee',
                            color: log.status === 'success' ? '#2e7d32' : '#c62828',
                            padding: '0.25rem 0.75rem',
                            borderRadius: '12px',
                            fontSize: '0.875rem',
                            fontWeight: '500'
                          }}>
                            {log.status}
                          </span>
                        </td>
                        <td style={{ padding: '1rem' }}>
                          {new Date(log.run_date).toLocaleDateString()}
                        </td>
                        <td style={{ padding: '1rem' }}>{log.records_extracted}</td>
                        <td style={{ padding: '1rem', color: log.error_message ? '#c62828' : '#666' }}>
                          {log.error_message || '-'}
                        </td>
                        <td style={{ padding: '1rem' }}>
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
