function Chip({ text, type }) {
  const cls = type === 'match' ? 'chip chip-match'
            : type === 'missing' ? 'chip chip-missing'
            : 'chip chip-skill'
  const icon = type === 'match' ? '✓' : type === 'missing' ? '✗' : '◆'
  return <span className={cls}>{icon} {text}</span>
}

function SkillGroup({ title, skills, type, countCls }) {
  return (
    <div className="card">
      <div className="section-label">
        {title}
        <span className={`section-count ${countCls}`}>{skills.length}</span>
      </div>
      <div className="chips-container">
        {skills.length > 0
          ? skills.map((s, i) => <Chip key={i} text={s} type={type} />)
          : <span className="no-data">None found</span>
        }
      </div>
    </div>
  )
}

export default function SkillsPanel({ matchingSkills, missingSkills, allSkills }) {
  return (
    <>
      <div className="skills-grid">
        <SkillGroup
          title="Matching Skills"
          skills={matchingSkills || []}
          type="match"
          countCls="count-green"
        />
        <SkillGroup
          title="Missing Skills"
          skills={missingSkills || []}
          type="missing"
          countCls="count-red"
        />
      </div>

      <div className="card all-skills-card">
        <div className="section-label">
          All Resume Skills
          <span className="section-count">{(allSkills || []).length}</span>
        </div>
        <div className="chips-container">
          {(allSkills || []).length > 0
            ? allSkills.map((s, i) => <Chip key={i} text={s} type="all" />)
            : <span className="no-data">No skills extracted</span>
          }
        </div>
      </div>
    </>
  )
}
