import ScoreRing      from './ScoreRing'
import ScoreBreakdown from './ScoreBreakdown'
import SkillsPanel    from './SkillsPanel'
import CandidateCard  from './CandidateCard'
import ContactCard    from './ContactCard'
import ReasonBox      from './ReasonBox'
import JsonViewer     from './JsonViewer'
import InterviewPanel from './InterviewPanel'
import LocalInterview from './LocalInterview'

export default function ResultsDashboard({
  data, interview, callLoading, callError, onStartInterview,
  resumeText, jdText, candidateName,
  localStep, localError, onStartLocal, onLocalComplete, onLocalCancel,
}) {
  return (
    <section className="results-section">

      <div className="section-label" style={{ marginBottom: 20 }}>Analysis Results</div>

      <div className="top-row">
        <ScoreRing score={data.match_score} />
        <CandidateCard data={data} />
        <ContactCard
          data={data}
          onStartInterview={onStartInterview}
          callLoading={callLoading}
          callError={callError}
          onStartLocal={onStartLocal}
          localLoading={localStep === 'loading'}
        />
      </div>

      {data.score_breakdown && (
        <ScoreBreakdown breakdown={data.score_breakdown} />
      )}

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

      {localError && (
        <div className="call-error" style={{ marginBottom: 12 }}>{localError}</div>
      )}

      {/* Live voice interview */}
      {localStep === 'in-progress' && (
        <LocalInterview
          resumeText={resumeText}
          jdText={jdText}
          candidateName={candidateName}
          onComplete={onLocalComplete}
          onCancel={onLocalCancel}
        />
      )}

      {/* Scoring spinner */}
      {localStep === 'scoring' && (
        <div className="local-iv-card">
          <div className="local-iv-scoring">
            <div className="local-iv-scoring-ring" />
            <div className="local-iv-scoring-label">Scoring your interview…</div>
            <div className="local-iv-scoring-sub">Claude is reviewing the full conversation</div>
          </div>
        </div>
      )}

      <InterviewPanel interview={interview} />

      <JsonViewer data={data} />

    </section>
  )
}
