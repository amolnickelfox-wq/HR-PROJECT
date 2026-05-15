import ScoreRing      from './ScoreRing'
import ScoreBreakdown from './ScoreBreakdown'
import SkillsPanel    from './SkillsPanel'
import CandidateCard  from './CandidateCard'
import ContactCard    from './ContactCard'
import ReasonBox      from './ReasonBox'
import JsonViewer     from './JsonViewer'
import InterviewPanel from './InterviewPanel'

export default function ResultsDashboard({
  data, interview, callLoading, callError, onStartInterview,
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

      <InterviewPanel interview={interview} />

      <JsonViewer data={data} />

    </section>
  )
}
