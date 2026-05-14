import { useState, useEffect, useRef } from 'react'

const SR        = window.SpeechRecognition || window.webkitSpeechRecognition
const SUPPORTED = !!SR && !!window.speechSynthesis

function pickVoice() {
  const vs = window.speechSynthesis.getVoices()
  return (
    vs.find(v => /zira|hazel|aria|susan|karen|samantha/i.test(v.name)) ||
    vs.find(v => v.lang === 'en-GB' && v.localService) ||
    vs.find(v => v.lang === 'en-US') ||
    vs.find(v => v.lang.startsWith('en')) ||
    vs[0]
  )
}

function speak(text, onDone, logFn) {
  logFn && logFn('TTS speak() — "' + text.slice(0, 60) + '"')
  window.speechSynthesis.cancel()

  let doneFired = false
  let ttsTimer  = null

  const done = (reason) => {
    if (doneFired) return
    doneFired = true
    clearTimeout(ttsTimer)
    logFn && logFn('TTS done (' + reason + ')')
    onDone && onDone()
  }

  const go = () => {
    const utt  = new SpeechSynthesisUtterance(text)
    utt.rate   = 0.92
    utt.pitch  = 1.0
    utt.volume = 1
    const v    = pickVoice()
    if (v) { utt.voice = v; logFn && logFn('TTS voice: ' + v.name) }

    utt.onstart = () => {
      logFn && logFn('TTS utt.onstart ✓')
      const ms = Math.min(Math.max(text.length * 100 + 6000, 8000), 45000)
      ttsTimer = setTimeout(() => {
        window.speechSynthesis.cancel()
        done('timeout')
      }, ms)
    }
    utt.onend   = () => done('onend')
    utt.onerror = (e) => { logFn && logFn('TTS onerror: ' + e.error); done('onerror:' + e.error) }

    window.speechSynthesis.speak(utt)

    setTimeout(() => {
      if (!doneFired && ttsTimer === null) {
        const ms = Math.min(Math.max(text.length * 100 + 8000, 10000), 45000)
        ttsTimer = setTimeout(() => {
          window.speechSynthesis.cancel()
          done('hard-timeout')
        }, ms)
      }
    }, 1500)
  }

  window.speechSynthesis.getVoices().length === 0
    ? (window.speechSynthesis.onvoiceschanged = go)
    : go()
}

export default function LocalInterview({
  resumeText, jdText, candidateName, onComplete, onCancel,
}) {
  const [phase,       setPhase]       = useState('loading')   // loading | speaking | listening | processing | done | goodbye
  const [questions,   setQuestions]   = useState([])
  const [answers,     setAnswers]     = useState([])          // answers[i] = text for questions[i]
  const [currentIdx,  setCurrentIdx]  = useState(0)
  const [finalText,   setFinalText]   = useState('')
  const [interimText, setInterimText] = useState('')
  const [elapsed,     setElapsed]     = useState(0)
  const [micReady,    setMicReady]    = useState(false)
  const [micError,    setMicError]    = useState('')
  const [countdown,   setCountdown]   = useState(null)
  const [debugLogs,   setDebugLogs]   = useState([])

  const S = useRef({
    phase: 'loading', acc: '', interimAcc: '',
    recog: null, silenceTimer: null, cntdwnTimer: null,
    currentIdx: 0,
  })
  const timerRef       = useRef(null)
  const transcriptRef  = useRef(null)
  const activeQRef     = useRef(null)

  const fmt = s => `${String(Math.floor(s / 60)).padStart(2,'0')}:${String(s % 60).padStart(2,'0')}`
  const now = () => new Date().toLocaleTimeString('en', { hour12: false })

  const scrollTranscript = () => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
  }

  function log(msg, data = '') {
    const line = `[${now()}] ${msg}${data ? '  ' + JSON.stringify(data) : ''}`
    console.log(line)
    setDebugLogs(prev => [...prev.slice(-29), line])
  }

  function killRecog() {
    const r = S.current.recog
    if (!r) return
    r.onresult = null; r.onerror = null; r.onend = null; r.onstart = null
    try { r.abort() } catch (_) {}
    S.current.recog = null
    log('recog killed')
  }

  function clearSilence() {
    clearTimeout(S.current.silenceTimer)
    clearInterval(S.current.cntdwnTimer)
    S.current.silenceTimer = null
    S.current.cntdwnTimer  = null
    setCountdown(null)
  }

  function armSilence(onFire) {
    clearSilence()
    let rem = 3
    setCountdown(rem)
    S.current.cntdwnTimer = setInterval(() => {
      rem -= 1
      setCountdown(rem > 0 ? rem : null)
    }, 1000)
    S.current.silenceTimer = setTimeout(() => {
      clearInterval(S.current.cntdwnTimer)
      setCountdown(null)
      onFire()
    }, 3000)
  }

  // ── Advance to next question or finish ────────────────────────────────────
  function advanceWith(answer, questions) {
    killRecog()
    clearSilence()
    setInterimText('')
    setFinalText('')

    const idx = S.current.currentIdx
    setAnswers(prev => {
      const next = [...prev]
      next[idx] = answer
      return next
    })

    const nextIdx = idx + 1

    if (nextIdx < questions.length) {
      S.current.currentIdx = nextIdx
      setCurrentIdx(nextIdx)
      S.current.phase = 'speaking'
      setPhase('speaking')
      S.current.acc        = ''
      S.current.interimAcc = ''
      setTimeout(() => {
        if (activeQRef.current) activeQRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 100)
      speak(questions[nextIdx], () => {
        log('TTS done — switching to listening')
        S.current.phase = 'listening'
        setPhase('listening')
        startListening()
      }, log)
    } else {
      // All questions answered — build conversation and score
      S.current.phase = 'processing'
      setPhase('processing')
      const allAnswers = [...Array(idx).fill('').map((_, i) => S.current.allAnswers?.[i] || ''), answer]
      const conversation = questions.flatMap((q, i) => [
        { role: 'interviewer', content: q },
        { role: 'candidate',   content: allAnswers[i] || '[no answer]' },
      ])
      log('all done — scoring conversation')
      speak(
        'Thank you for completing the interview. We will now process your responses.',
        () => onComplete(conversation),
        log
      )
    }
  }

  function submitAnswer(answer, questions) {
    log('submitAnswer: "' + answer.slice(0, 60) + '"')
    advanceWith(answer, questions)
  }

  function skipToListening() {
    log('User skipped TTS')
    window.speechSynthesis.cancel()
    S.current.phase      = 'listening'
    S.current.acc        = ''
    S.current.interimAcc = ''
    setPhase('listening')
    setFinalText('')
    setInterimText('')
    startListening()
  }

  // ── Start listening ───────────────────────────────────────────────────────
  function startListening(qs) {
    if (S.current.phase !== 'listening') {
      log('startListening skipped — phase=' + S.current.phase)
      return
    }
    killRecog()

    const recog           = new SR()
    recog.lang            = 'en-US'
    recog.continuous      = true
    recog.interimResults  = true
    recog.maxAlternatives = 1
    S.current.recog       = recog

    let startedAt   = null
    let speechStart = null

    recog.onstart = () => {
      startedAt = Date.now()
      log('recog.onstart ✓')
    }

    const getQs = () => qs || S.current.questions

    const fireSilence = () => {
      const answer = (S.current.acc + (S.current.interimAcc ? S.current.interimAcc + ' ' : '')).trim()
      log('silence fired — answer: "' + answer.slice(0, 60) + '"')
      if (answer && S.current.phase === 'listening') submitAnswer(answer, getQs())
      else if (!answer) { log('nothing captured, restarting'); startListening(qs) }
    }

    const wordCount = () => S.current.acc.trim().split(/\s+/).filter(Boolean).length

    recog.onspeechstart = () => {
      speechStart = Date.now()
      log('onspeechstart — cancelling silence timer')
      clearSilence()
    }

    recog.onspeechend = () => {
      const duration = speechStart ? Date.now() - speechStart : 0
      log('onspeechend — duration=' + duration + 'ms')
      if (duration < 400) { log('noise burst ignored'); return }
      const hasContent = (S.current.acc + S.current.interimAcc).trim()
      if (hasContent && !S.current.silenceTimer) armSilence(fireSilence)
    }

    recog.onresult = (e) => {
      let newFinal = '', newInterim = '', minConf = 1
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) {
          const conf = r[0].confidence || 1
          if (conf < 0.45) { log('low-conf (' + conf.toFixed(2) + ') skipped'); continue }
          minConf   = Math.min(minConf, conf)
          newFinal += r[0].transcript
        } else {
          newInterim = r[0].transcript
        }
      }
      log('onresult', { final: newFinal.slice(0,40), interim: newInterim.slice(0,40) })

      if (newFinal) {
        S.current.acc += (S.current.interimAcc ? S.current.interimAcc + ' ' : '') + newFinal + ' '
        S.current.interimAcc = ''
        setFinalText(S.current.acc.trim())
        setInterimText('')
        setTimeout(scrollTranscript, 0)
        if (wordCount() >= 3) armSilence(fireSilence)
      } else {
        S.current.interimAcc = newInterim
        setInterimText(newInterim)
        setTimeout(scrollTranscript, 0)
        clearSilence()
      }
    }

    recog.onerror = (e) => {
      log('recog.onerror: ' + e.error)
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        setMicError('Microphone blocked. Allow mic in browser settings and refresh.')
        return
      }
      if (e.error === 'aborted') return
      if (e.error === 'audio-capture') {
        setMicError('Mic capture failed — another app may be using the mic.')
        return
      }
    }

    recog.onend = () => {
      const alive = startedAt ? (Date.now() - startedAt) : 0
      log('recog.onend — alive=' + alive + 'ms, phase=' + S.current.phase)
      if (S.current.interimAcc) {
        S.current.acc += S.current.interimAcc + ' '
        S.current.interimAcc = ''
        setFinalText(S.current.acc.trim())
        setInterimText('')
        log('onend: salvaged interim')
      }
      if (S.current.phase !== 'listening') return
      setTimeout(() => {
        if (S.current.phase === 'listening') startListening(qs)
      }, 300)
    }

    try {
      recog.start()
      log('recog.start() ✓')
    } catch (err) {
      log('recog.start() threw: ' + err.message)
      setTimeout(() => { if (S.current.phase === 'listening') startListening(qs) }, 600)
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!SUPPORTED) return
    log('Requesting mic…')

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        stream.getTracks().forEach(t => { t.stop(); log('mic track released ✓') })
        log('Mic permission granted ✓')
        setMicReady(true)
        timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000)

        fetch('/interview/questions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resume_text: resumeText, jd_text: jdText }),
        })
          .then(r => r.json())
          .then(data => {
            const qs = data.questions || []
            log('questions loaded: ' + qs.length)
            setQuestions(qs)
            S.current.questions  = qs
            S.current.currentIdx = 0
            S.current.phase      = 'speaking'
            setPhase('speaking')
            speak(qs[0], () => {
              S.current.phase = 'listening'
              setPhase('listening')
              startListening(qs)
            }, log)
          })
          .catch(err => {
            log('Failed to load questions: ' + err.message)
          })
      })
      .catch(err => {
        log('getUserMedia failed: ' + err.message)
        setMicError('Microphone access denied. Allow mic permission in the browser address bar, then refresh.')
      })

    return () => {
      clearInterval(timerRef.current)
      clearSilence()
      window.speechSynthesis.cancel()
      killRecog()
    }
  }, []) // eslint-disable-line

  function handleDoneAnswering() {
    const answer = (S.current.acc + (S.current.interimAcc ? S.current.interimAcc + ' ' : '')).trim()
    if (answer) submitAnswer(answer, S.current.questions)
  }

  function handleCancel() {
    killRecog()
    clearSilence()
    clearInterval(timerRef.current)
    S.current.phase = 'goodbye'
    setPhase('goodbye')
    speak(
      'Thank you for joining. The interview has ended. We will be in touch soon. Goodbye!',
      () => onCancel(),
      log
    )
  }

  // ── Unsupported / no mic ──────────────────────────────────────────────────
  if (!SUPPORTED) return (
    <div className="local-iv-card">
      <div className="local-iv-unsupported">
        <div className="local-iv-unsupported-icon">⚠️</div>
        <div className="local-iv-unsupported-title">Browser Not Supported</div>
        <div className="local-iv-unsupported-text">Voice interview requires Chrome or Edge.</div>
        <button className="local-iv-cancel" onClick={onCancel}>Go Back</button>
      </div>
    </div>
  )

  if (!micReady) return (
    <div className="local-iv-card">
      <div className="local-iv-scoring">
        {micError
          ? <>
              <div style={{ fontSize: '2.2rem' }}>🎙️</div>
              <div className="local-iv-scoring-label" style={{ color: 'var(--red)', textAlign: 'center' }}>
                Microphone Access Required
              </div>
              <div className="local-iv-scoring-sub" style={{ textAlign: 'center', maxWidth: 380, lineHeight: 1.7 }}>
                {micError}
              </div>
              <button className="local-iv-cancel" style={{ marginTop: 20 }} onClick={onCancel}>Go Back</button>
            </>
          : <>
              <div className="local-iv-scoring-ring" />
              <div className="local-iv-scoring-label">Requesting microphone…</div>
              <div className="local-iv-scoring-sub">Allow mic permission in the browser popup</div>
            </>
        }
      </div>
    </div>
  )

  // ── Loading questions ─────────────────────────────────────────────────────
  if (phase === 'loading' || questions.length === 0) return (
    <div className="local-iv-card">
      <div className="local-iv-scoring">
        <div className="local-iv-scoring-ring" />
        <div className="local-iv-scoring-label">Preparing your interview…</div>
        <div className="local-iv-scoring-sub">Generating personalised questions</div>
      </div>
    </div>
  )

  // ── Main UI ───────────────────────────────────────────────────────────────
  return (
    <div className="local-iv-card">

      {/* Header */}
      <div className="local-iv-header">
        <div className="local-iv-live"><span className="local-iv-dot" />HR Voice Interview</div>
        <div className="local-iv-timer">{fmt(elapsed)}</div>
      </div>

      {/* Progress bar */}
      <div className="local-iv-dots">
        {questions.map((_, i) => (
          <div key={i} className={`local-iv-dot-step ${
            i < currentIdx ? 'done' : i === currentIdx ? 'active' : ''
          }`} />
        ))}
      </div>

      {/* Status bar */}
      <div className="local-iv-phase-strip">
        {phase === 'speaking'    && <><span className="local-iv-dot" style={{ background: 'var(--cyan)' }} /> Interviewer Speaking…</>}
        {phase === 'listening'   && <><span className="local-iv-mic-pulse" /> Your Turn — Speak Now</>}
        {phase === 'processing'  && <><span className="local-iv-dot" style={{ background: 'var(--purple)' }} /> Processing…</>}
        {phase === 'goodbye'     && <>👋 Ending Interview…</>}
      </div>

      {/* All questions list */}
      <div className="local-iv-qlist">
        {questions.map((q, i) => {
          const isDone    = i < currentIdx
          const isActive  = i === currentIdx
          const isPending = i > currentIdx

          return (
            <div
              key={i}
              ref={isActive ? activeQRef : null}
              className={`local-iv-qitem ${isDone ? 'done' : isActive ? 'active' : 'pending'}`}
            >
              {/* Question header */}
              <div className="local-iv-qitem-header">
                <span className="local-iv-qitem-num">
                  {isDone ? '✓' : `Q${i + 1}`}
                </span>
                <span className="local-iv-qitem-text">{q}</span>
              </div>

              {/* Completed answer */}
              {isDone && answers[i] && (
                <div className="local-iv-qitem-answer">
                  <span className="local-iv-qitem-answer-label">Your answer:</span>
                  <span className="local-iv-qitem-answer-text">{answers[i]}</span>
                </div>
              )}

              {/* Active — mic input */}
              {isActive && (
                <div className="local-iv-qitem-mic">
                  {/* Skip TTS */}
                  {phase === 'speaking' && (
                    <button
                      className="local-iv-cancel"
                      style={{ fontSize: '0.75rem', padding: '5px 14px', marginBottom: 10 }}
                      onClick={skipToListening}
                    >
                      Skip — Start Answering Now
                    </button>
                  )}

                  {/* Live transcript */}
                  {phase === 'listening' && (
                    <>
                      <div className="local-iv-live-label">
                        <span className="local-iv-mic-pulse" />
                        {countdown !== null
                          ? `Submitting in ${countdown}s — keep talking to reset`
                          : 'Listening — speak freely'}
                      </div>
                      <div className="local-iv-transcript-display" ref={transcriptRef}>
                        {finalText || interimText
                          ? <>
                              <span className="local-iv-final">{finalText}</span>
                              {interimText && <span className="local-iv-interim"> {interimText}</span>}
                            </>
                          : <span className="local-iv-live-placeholder">Start speaking — your words will appear here…</span>
                        }
                      </div>
                      <button
                        className="local-iv-done-btn"
                        onClick={handleDoneAnswering}
                        disabled={!finalText.trim() && !interimText.trim()}
                      >
                        Done Answering ✓
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* Pending */}
              {isPending && (
                <div className="local-iv-qitem-pending">Upcoming</div>
              )}
            </div>
          )
        })}
      </div>

      {micError && <div className="local-iv-error-bar">{micError}</div>}

      {/* Debug log */}
      <details className="local-iv-debug">
        <summary className="local-iv-debug-toggle">🔧 Debug Log ({debugLogs.length})</summary>
        <div className="local-iv-debug-body">
          {debugLogs.length === 0
            ? <span style={{ color: 'var(--text-3)' }}>No events yet…</span>
            : debugLogs.map((l, i) => <div key={i} className="local-iv-debug-line">{l}</div>)
          }
        </div>
      </details>

      {phase !== 'goodbye' && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="local-iv-cancel" onClick={handleCancel}>✕ End Interview</button>
        </div>
      )}
    </div>
  )
}
