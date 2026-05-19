import { useEffect } from 'react'
import ScoreRing      from './ScoreRing'
import ScoreBreakdown from './ScoreBreakdown'
import SkillsPanel    from './SkillsPanel'
import CandidateCard  from './CandidateCard'
import ReasonBox      from './ReasonBox'
import InterviewPanel from './InterviewPanel'

export default function BatchCandidateModal({ candidate, onClose, onCallCandidate }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  const data = candidate.analyze_result
  const interview = {
    status:       candidate.interview_status,
    questions:    candidate.questions || [],
    score_result: candidate.score_result,
    transcript:   candidate.transcript,
    fail_reason:  candidate.fail_reason,
    call_log:     candidate.call_log,
  }

  return (
    <div className="batch-modal-overlay" onClick={onClose}>
      <div className="batch-modal-panel" onClick={e => e.stopPropagation()}>

        <div className="batch-modal-header">
          <button className="batch-modal-back" onClick={onClose}>← Back to Results</button>
          <div className="batch-modal-title">
            <div className="candidate-avatar candidate-avatar--sm">
              {(candidate.name || candidate.file_name || '?')[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-1)' }}>
                {candidate.name || candidate.file_name || 'Candidate'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
                {candidate.email || candidate.file_name}
              </div>
            </div>
          </div>
        </div>

        <div className="batch-modal-body">
          {data ? (
            <section className="results-section">
              <div className="section-label" style={{ marginBottom: 20 }}>Analysis Results</div>

              <div className="top-row">
                <ScoreRing score={data.match_score} />
                <CandidateCard data={data} />
                <div className="card">
                  <div className="section-label">Contact</div>
                  <div className="info-item" style={{ marginBottom: 10 }}>
                    <div className="info-icon-wrap">✉</div>
                    <div className="info-body">
                      <div className="info-lbl">Email</div>
                      <div className="info-val small">{data.email || 'Not found'}</div>
                    </div>
                  </div>
                  <div className="info-item">
                    <div className="info-icon-wrap">📞</div>
                    <div className="info-body">
                      <div className="info-lbl">Phone</div>
                      <div className="info-val">{data.phone || 'Not found'}</div>
                    </div>
                  </div>
                </div>
              </div>

              {data.score_breakdown && <ScoreBreakdown breakdown={data.score_breakdown} />}

              <div className="section-label">Skills Analysis</div>
              <SkillsPanel
                matchingSkills={data.matching_skills}
                missingSkills={data.missing_skills}
                allSkills={data.skills}
              />

              <ReasonBox reason={data.reason} />

              {data.projects?.length > 0 && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <div className="section-label">Extracted Projects</div>
                  <div className="project-list">
                    {data.projects.map((p, i) => (
                      <div key={i} className="project-item">
                        <div className="project-dot" />{p}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {candidate.interview_status === 'retry_queued' && (
                <div style={{ background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: '0.82rem', color: '#92400e' }}>
                  🔄 Call not answered — will retry after the queue completes
                </div>
              )}

              {onCallCandidate && candidate.phone &&
               candidate.filter_status !== 'no_phone' && (
                <div style={{ marginBottom: 16 }}>
                  <button
                    className="btn-analyze"
                    style={{ fontSize: '0.85rem', padding: '9px 20px' }}
                    onClick={() => { onCallCandidate(candidate); onClose() }}
                  >
                    📞 Call Candidate
                  </button>
                </div>
              )}

              <InterviewPanel interview={interview} />
            </section>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-3)' }}>
              <div style={{ fontSize: '2rem', marginBottom: 12 }}>📄</div>
              <div>No detailed analysis available for this candidate.</div>
              <div style={{ fontSize: '0.8rem', marginTop: 6 }}>
                {candidate.filter_status === 'filtered_out' ? 'Resume score was below the threshold.' : ''}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
