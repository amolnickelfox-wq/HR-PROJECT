export const safeJson = async (res) => {
  try { return await res.json() } catch { return {} }
}

export const apiAnalyze = (resumeText, jdText, signal, openingId, singleId) =>
  fetch('/analyze', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ resume_text: resumeText, jd_text: jdText, opening_id: openingId || null, single_id: singleId || null }),
    signal,
  })

export const apiStartInterview = (payload) =>
  fetch('/interview/start', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  })

export const apiInterviewStatus = (callId) =>
  fetch(`/interview/status/${callId}`)

export const apiRecallInterview = (interviewId) =>
  fetch(`/interview/recall/${interviewId}`, { method: 'POST' })

export const apiStartBatch = (formData) =>
  fetch('/batch/start', { method: 'POST', body: formData })

export const apiBatchStatus = (batchId) =>
  fetch(`/batch/status/${batchId}`)

export const apiBatchInterviewStart = (batchId, fileName) =>
  fetch(`/batch/${batchId}/interview/start`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ file_name: fileName }),
  })

export const apiCallbacksDue = () =>
  fetch('/callbacks/due')

export const apiGetOpenings = () =>
  fetch('/openings')

export const apiGetOpeningsFull = () =>
  fetch('/openings/full')

export const apiCreateOpening = (opening) =>
  fetch('/openings', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(opening),
  })

export const apiUpdateOpening = (id, data) =>
  fetch(`/openings/${id}`, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data),
  })

export const apiDeleteOpening = (id) =>
  fetch(`/openings/${id}`, { method: 'DELETE' })

export const apiGetOpeningCandidates = (id) =>
  fetch(`/openings/${id}/candidates`)

export const apiForceResolve = (interviewId) =>
  fetch(`/interview/force-resolve/${interviewId}`, { method: 'POST' })

export const apiActiveCalls = () =>
  fetch('/calls/active')

export const apiStartPipeline = (openingId) =>
  fetch(`/openings/${openingId}/pipeline/start`, { method: 'POST' })

export const apiPipelineStatus = (openingId) =>
  fetch(`/openings/${openingId}/pipeline/status`)

export const apiStopPipeline = (openingId) =>
  fetch(`/openings/${openingId}/pipeline/stop`, { method: 'POST' })
