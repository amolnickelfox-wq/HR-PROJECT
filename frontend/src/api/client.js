export const safeJson = async (res) => {
  try { return await res.json() } catch { return {} }
}

export const apiAnalyze = (resumeText, jdText, signal) =>
  fetch('/analyze', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ resume_text: resumeText, jd_text: jdText }),
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
