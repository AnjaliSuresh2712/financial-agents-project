const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handleResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

export async function createAnalysisRun(ticker) {
  const response = await fetch(`${API_BASE_URL}/analyze/${ticker}`, {
    method: "POST"
  });
  return handleResponse(response);
}

export async function getAnalysisRun(runId) {
  const response = await fetch(`${API_BASE_URL}/analysis/${runId}`);
  return handleResponse(response);
}

export async function listAnalysisRuns(limit = 10) {
  const response = await fetch(`${API_BASE_URL}/analyses?limit=${limit}`);
  return handleResponse(response);
}

export { API_BASE_URL };
