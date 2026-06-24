import { useState, useRef, useEffect } from 'react'

const API = '';

const LANGUAGES = ['python','typescript','javascript','go','rust','java','ruby','csharp','cpp'];

const EXAMPLE_CODE = `import subprocess
import random
import pickle

DB_PASSWORD = "admin123"
API_KEY = "sk-prod-supersecret"

def get_users(db, search_term):
    query = "SELECT * FROM users WHERE name = '" + search_term + "'"
    results = db.execute(query)
    user_list = []
    for user in results:
        user_list = user_list + [user]
    return user_list

def run_command(cmd):
    output = subprocess.run(cmd, shell=True, capture_output=True)
    return output.stdout

def load_data(filepath):
    with open(filepath, "rb") as f:
        return pickle.load(f)

def generate_token():
    return random.randint(100000, 999999)`;

function Spinner() {
  return (
    <svg className="spinning" width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg>
  );
}

function VerdictBadge({ decision }) {
  if (!decision) return null;
  const styles = {
    block:           'badge badge-block',
    pass:            'badge badge-pass',
    request_changes: 'badge badge-request',
  };
  const labels = {
    block:           'BLOCK',
    pass:            'PASS',
    request_changes: 'REQUEST CHANGES',
  };
  return (
    <span className={styles[decision] || 'badge'}>
      {labels[decision] || decision.toUpperCase()}
    </span>
  );
}

function ScoreRing({ score }) {
  const color = score >= 8 ? '#ef4444' : score >= 5 ? '#f59e0b' : '#22c55e';
  const r = 36, cx = 44, cy = 44, stroke = 6;
  const circ = 2 * Math.PI * r;
  const dash = (score / 10) * circ;
  return (
    <div className="score-ring-wrap score-pop">
      <svg width="88" height="88">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e5e7eb" strokeWidth={stroke}/>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}/>
      </svg>
      <div className="score-ring-label">
        <span style={{ fontSize:24, fontWeight:600, lineHeight:1, color:'#111827' }}>{score}</span>
        <span style={{ fontSize:11, color:'#9ca3af' }}>/10</span>
      </div>
    </div>
  );
}

function IssueItem({ text, type }) {
  const cls = {
    critical:   'issue-item issue-critical',
    suggestion: 'issue-item issue-suggestion',
    nitpick:    'issue-item issue-nitpick',
  }[type] || 'issue-item issue-nitpick';
  return <div className={cls}>{text}</div>;
}

function TraceRow({ trace }) {
  const isOk = trace.status === 'ok';
  const barW = Math.min(100, (trace.duration_ms / 5000) * 100);
  return (
    <div style={{ display:'flex', alignItems:'center', gap:12, padding:'6px 0', borderBottom:'0.5px solid #f3f4f6' }}>
      <div style={{ width:6, height:6, borderRadius:'50%', flexShrink:0, backgroundColor: isOk ? '#4ade80' : '#f87171' }}/>
      <span style={{ fontSize:11, fontFamily:'monospace', color:'#6b7280', width:128, flexShrink:0 }}>{trace.agent}</span>
      <div className="trace-bar-bg">
        <div className="trace-bar-fill" style={{ width:`${barW}%` }}/>
      </div>
      <span style={{ fontSize:11, color:'#9ca3af', width:64, textAlign:'right', flexShrink:0 }}>
        {trace.duration_ms.toLocaleString()}ms
      </span>
      {trace.tokens && (
        <span style={{ fontSize:11, color:'#d1d5db', width:48, textAlign:'right', flexShrink:0 }}>
          {trace.tokens}t
        </span>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div style={{ width:56, height:56, borderRadius:16, backgroundColor:'#eef2ff', display:'flex', alignItems:'center', justifyContent:'center', marginBottom:16 }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
      </div>
      <p style={{ fontSize:14, fontWeight:500, color:'#374151', marginBottom:4 }}>No review yet</p>
      <p style={{ fontSize:12, color:'#9ca3af', lineHeight:1.6 }}>
        Paste or upload code on the left,<br/>then click Review code.
      </p>
    </div>
  );
}

function LoadingState() {
  const agents = ['security', 'performance', 'quality', 'tests', 'architecture'];
  const [active, setActive] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setActive(a => (a + 1) % agents.length), 600);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="loading-state">
      <div style={{ display:'flex', gap:6, marginBottom:24 }}>
        {agents.map((a, i) => (
          <div key={a} style={{
            height:4, borderRadius:9999,
            backgroundColor: i === active ? '#6366f1' : '#e5e7eb',
            width: i === active ? 24 : 6,
            transition: 'all 0.3s ease',
          }}/>
        ))}
      </div>
      <p style={{ fontSize:14, fontWeight:500, color:'#374151', marginBottom:4 }}>Running 5 specialist agents</p>
      <p style={{ fontSize:12, color:'#9ca3af', marginBottom:16 }}>in parallel</p>
      <span style={{ fontSize:11, fontFamily:'monospace', color:'#6366f1', backgroundColor:'#eef2ff', padding:'4px 12px', borderRadius:9999 }}>
        {agents[active]}
      </span>
    </div>
  );
}

function ResultPanel({ result, loading, error }) {
  const [showTrace, setShowTrace] = useState(false);
  const [showFull, setShowFull] = useState(false);

  if (loading) return <LoadingState />;

  if (error) return (
    <div style={{ padding:24 }}>
      <div style={{ backgroundColor:'#fef2f2', border:'1px solid #fecaca', borderRadius:12, padding:16, fontSize:13, color:'#b91c1c' }}>
        <p style={{ fontWeight:500, marginBottom:4 }}>Review failed</p>
        <p style={{ color:'#dc2626', marginBottom:8 }}>{error}</p>
        <p style={{ color:'#ef4444', fontSize:11 }}>
          Make sure the server is running:&nbsp;
          <code style={{ fontFamily:'monospace' }}>uvicorn api:app --reload --port 8000</code>
        </p>
      </div>
    </div>
  );

  if (!result) return <EmptyState />;

  const wallTime = result.traces?.length ? Math.max(...result.traces.map(t => t.duration_ms)) : 0;
  const totalTokens = result.traces?.reduce((s, t) => s + (t.tokens || 0), 0) || 0;

  return (
    <div className="animate-fade-in">
      <div style={{ padding:'20px 24px 16px', borderBottom:'0.5px solid #f3f4f6', display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:16 }}>
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8, flexWrap:'wrap' }}>
            <VerdictBadge decision={result.decision} />
            {result.memory_hit && <span className="badge-memory">↻ memory hit</span>}
            {result.revision_count > 1 && <span style={{ fontSize:11, color:'#9ca3af' }}>{result.revision_count} revisions</span>}
          </div>
          {result.filename && <code style={{ fontSize:11, color:'#9ca3af', fontFamily:'monospace' }}>{result.filename}</code>}
          {result.summary && <p style={{ fontSize:13, color:'#4b5563', lineHeight:1.65, maxWidth:380, marginTop:4 }}>{result.summary}</p>}
        </div>
        <ScoreRing score={result.severity_score || 0} />
      </div>

      {result.critical_issues?.length > 0 && (
        <div className="result-section">
          <p className="section-label">Critical — must fix before merge</p>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {result.critical_issues.map((issue, i) => <IssueItem key={i} text={issue} type="critical" />)}
          </div>
        </div>
      )}

      {result.suggestions?.length > 0 && (
        <div className="result-section">
          <p className="section-label">Suggestions</p>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {result.suggestions.map((s, i) => <IssueItem key={i} text={s} type="suggestion" />)}
          </div>
        </div>
      )}

      {result.nitpicks?.length > 0 && (
        <div className="result-section">
          <p className="section-label">Nitpicks</p>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {result.nitpicks.map((n, i) => <IssueItem key={i} text={n} type="nitpick" />)}
          </div>
        </div>
      )}

      <div className="result-section">
        <button className="toggle-btn" onClick={() => setShowTrace(s => !s)}
          style={{ display:'flex', alignItems:'center', gap:6 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ transform: showTrace ? 'rotate(90deg)' : 'none', transition:'transform .2s' }}>
            <polyline points="9 18 15 12 9 6"/>
          </svg>
          <span style={{ fontWeight:600, textTransform:'uppercase', letterSpacing:'0.05em', fontSize:11, color:'#9ca3af' }}>
            Agent trace
          </span>
          <span style={{ fontSize:11, color:'#d1d5db' }}>
            · wall {wallTime.toLocaleString()}ms · {totalTokens.toLocaleString()} tokens
          </span>
        </button>
        {showTrace && (
          <div className="animate-slide-up" style={{ marginTop:12 }}>
            {result.traces?.map((t, i) => <TraceRow key={i} trace={t} />)}
          </div>
        )}
      </div>

      <div className="result-section">
        <button className="toggle-btn" onClick={() => setShowFull(s => !s)}>
          {showFull ? '↑ Hide' : '↓ Show'} full review
        </button>
        {showFull && (
          <pre className="full-review-block animate-slide-up">{result.final_review}</pre>
        )}
      </div>
    </div>
  );
}

function HistoryPanel({ onClose }) {
  const [files, setFiles] = useState(null);

  useEffect(() => {
    fetch(`${API}/history`)
      .then(r => r.json())
      .then(d => setFiles(d.files))
      .catch(() => setFiles([]));
  }, []);

  async function deleteFile(filename) {
    await fetch(`${API}/history/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    setFiles(f => f.filter(x => x.filename !== filename));
  }

  const decisionColor = d => d === 'block' ? '#dc2626' : d === 'pass' ? '#16a34a' : '#d97706';

  return (
    <div style={{ height:'100%', display:'flex', flexDirection:'column' }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 24px', borderBottom:'0.5px solid #f3f4f6' }}>
        <p style={{ fontSize:14, fontWeight:500, color:'#111827' }}>Review history</p>
        <button onClick={onClose} style={{ fontSize:12, color:'#9ca3af', background:'none', border:'none', cursor:'pointer', fontFamily:'inherit' }}>
          Close
        </button>
      </div>
      <div style={{ flex:1, overflowY:'auto' }}>
        {!files && <p style={{ padding:'24px', fontSize:12, color:'#9ca3af' }}>Loading...</p>}
        {files?.length === 0 && <p style={{ padding:'24px', fontSize:13, color:'#9ca3af' }}>No files reviewed yet.</p>}
        {files?.map((f, i) => (
          <div key={i} className="history-row">
            <div>
              <code style={{ fontSize:12, fontFamily:'monospace', color:'#111827' }}>{f.filename}</code>
              <p style={{ fontSize:11, color:'#9ca3af', marginTop:2 }}>{f.reviewed_at?.replace('T', ' ')}</p>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:12 }}>
              <span style={{ fontSize:11, fontWeight:600, color: decisionColor(f.decision) }}>
                {f.decision?.toUpperCase().replace('_', ' ')}
              </span>
              <span style={{ fontSize:11, color:'#9ca3af' }}>{f.score}/10</span>
              <button onClick={() => deleteFile(f.filename)}
                style={{ fontSize:11, color:'#d1d5db', background:'none', border:'none', cursor:'pointer', padding:'2px 8px', borderRadius:6, fontFamily:'inherit' }}
                onMouseEnter={e => e.target.style.color = '#ef4444'}
                onMouseLeave={e => e.target.style.color = '#d1d5db'}
              >
                clear
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [tab,          setTab]          = useState('paste');
  const [code,         setCode]         = useState(EXAMPLE_CODE);
  const [context,      setContext]      = useState('');
  const [language,     setLanguage]     = useState('python');
  const [filename,     setFilename]     = useState('admin_utils.py');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [drag,         setDrag]         = useState(false);
  const [result,       setResult]       = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [showHistory,  setShowHistory]  = useState(false);
  const fileRef = useRef();

  async function runReview() {
    setLoading(true); setError(null); setResult(null);
    try {
      let res;
      if (tab === 'upload' && uploadedFile) {
        const fd = new FormData();
        fd.append('file', uploadedFile);
        if (context) fd.append('context', context);
        res = await fetch(`${API}/review/file`, { method:'POST', body:fd });
      } else {
        res = await fetch(`${API}/review`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language, context, filename }),
        });
      }
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Review failed'); }
      setResult(await res.json());
    } catch (e) {
      setError(e.message || 'Could not connect. Is the server running?');
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) { setUploadedFile(f); setTab('upload'); }
  }

  const canReview = !loading && (tab === 'paste' ? code.trim().length > 0 : !!uploadedFile);

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh' }}>
      <header className="app-header">
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          <span style={{ fontSize:14, fontWeight:600, color:'#ffffff', letterSpacing:'-0.01em' }}>
            Code<span style={{ color:'#818cf8' }}>Sentinel</span>
          </span>
        </div>
        <button onClick={() => setShowHistory(s => !s)}
          style={{ fontSize:12, color:'#94a3b8', background:'none', border:'none', cursor:'pointer', display:'flex', alignItems:'center', gap:6, fontFamily:'inherit' }}
          onMouseEnter={e => e.currentTarget.style.color = '#ffffff'}
          onMouseLeave={e => e.currentTarget.style.color = '#94a3b8'}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
          History
        </button>
      </header>

      <div className="app-layout">
        <div className="left-panel">
          <div style={{ display:'flex', gap:4, padding:'12px 16px 0', flexShrink:0 }}>
            {['paste','upload'].map(t => (
              <button key={t} onClick={() => setTab(t)} style={{
                fontSize:12, padding:'6px 14px', borderRadius:'6px 6px 0 0',
                border: tab === t ? '0.5px solid #2a2d3a' : 'none',
                background: tab === t ? '#1a1d27' : 'transparent',
                color: tab === t ? '#ffffff' : '#6b7280',
                cursor:'pointer', fontFamily:'inherit', textTransform:'capitalize',
              }}>
                {t}
              </button>
            ))}
          </div>

          <div style={{ flex:1, overflow:'hidden', display:'flex', flexDirection:'column', backgroundColor:'#1a1d27', borderTop:'0.5px solid #2a2d3a' }}>
            {tab === 'paste' && (
              <textarea className="code-textarea" value={code} onChange={e => setCode(e.target.value)}
                placeholder="Paste your code here..." spellCheck={false}/>
            )}
            {tab === 'upload' && (
              <div className={`upload-zone ${drag ? 'drag-over' : ''}`}
                onDragOver={e => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current.click()}
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                  stroke={drag ? '#818cf8' : '#4b5563'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                {uploadedFile
                  ? <><p style={{ fontSize:14, fontWeight:500, color:'#818cf8' }}>{uploadedFile.name}</p><p style={{ fontSize:12, color:'#6b7280' }}>Click to change</p></>
                  : <><p style={{ fontSize:14, color:'#94a3b8' }}>Drop a file here</p><p style={{ fontSize:12, color:'#6b7280' }}>.py · .ts · .js · .go · .rs · .java · .rb</p></>
                }
                <input ref={fileRef} type="file" style={{ display:'none' }}
                  onChange={e => { const f = e.target.files[0]; if (f) setUploadedFile(f); }}
                  accept=".py,.ts,.tsx,.js,.jsx,.go,.rs,.java,.rb,.cs,.cpp,.c,.php"/>
              </div>
            )}
          </div>

          <div className="left-bottom-bar">
            {tab === 'paste' && (
              <div style={{ display:'flex', gap:8 }}>
                <input className="input-dark" value={filename} onChange={e => setFilename(e.target.value)}
                  placeholder="filename.py" style={{ fontFamily:'monospace' }}/>
                <select className="input-dark" value={language} onChange={e => setLanguage(e.target.value)}
                  style={{ width:120, flexShrink:0 }}>
                  {LANGUAGES.map(l => <option key={l}>{l}</option>)}
                </select>
              </div>
            )}
            <input className="input-dark" value={context} onChange={e => setContext(e.target.value)}
              placeholder="Context — what does this code do? (optional)"/>
            <button className="btn-primary" onClick={runReview} disabled={!canReview}>
              {loading ? <><Spinner /> Reviewing…</> : 'Review code →'}
            </button>
          </div>
        </div>

        <div className="right-panel result-scroll">
          {showHistory
            ? <HistoryPanel onClose={() => setShowHistory(false)} />
            : <ResultPanel result={result} loading={loading} error={error} />
          }
        </div>
      </div>
    </div>
  );
}

export default App