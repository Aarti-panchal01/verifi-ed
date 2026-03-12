/**
 * API Client — Production-Grade HTTP Client
 * ===========================================
 * 
 * Centralized API client with:
 * - Environment-based configuration
 * - Error handling
 * - Request/response interceptors
 * - Retry logic
 * - Type-safe endpoints
 */

let API_URL = import.meta.env.VITE_API_URL;

// Hybrid logic: if we are on a production-like host (not localhost) 
// but API_URL is pointing to localhost, we attempt to use the relative path 
// or a known production proxy. For Verifi-ed, we assume the backend might be 
// at the same host /api or similar, or just allow the user to override.
if (API_URL && API_URL.includes('localhost') && window.location.hostname.includes('vercel.app')) {
    console.warn('API_URL points to localhost but app is on Vercel. Switching to Railway production URL.');
    API_URL = 'https://verifi-ed-production.up.railway.app';
}

if (!API_URL) {
    API_URL = window.location.hostname.includes('vercel.app') 
        ? 'https://verifi-ed-production.up.railway.app' 
        : '/api';
}

const TIMEOUT = 30000;
const MAX_RETRIES = 3;

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new APIError('Request timeout', 408, {});
    }

    if (retries > 0 && (error.status === 429 || error.status >= 500)) {
      const delay = Math.pow(2, MAX_RETRIES - retries) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
      return fetchWithRetry(url, options, retries - 1);
    }

    throw error;
  }
}

export const api = {
  // Scoring endpoints
  async analyzeRepo(repoUrl, mode = 'DEVELOPER') {
    return fetchWithRetry(`${API_URL}/analyze/repo`, {
      method: 'POST',
      body: JSON.stringify({ repo_url: repoUrl, mode }),
    });
  },

  async analyzeCertificate(filePath, mode = 'LEARNER') {
    return fetchWithRetry(`${API_URL}/analyze/certificate`, {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath, mode }),
    });
  },

  async analyzeProject(projectPath, mode = 'DEVELOPER') {
    return fetchWithRetry(`${API_URL}/analyze/project`, {
      method: 'POST',
      body: JSON.stringify({ project_path: projectPath, mode }),
    });
  },

  // Verification endpoints
  async verifyRepo(repoUrl, wallet = null) {
    return fetchWithRetry(`${API_URL}/verify-evidence/repo`, {
      method: 'POST',
      body: JSON.stringify({ repo_url: repoUrl, wallet }),
    });
  },

  async verifyCertificate(filePath) {
    return fetchWithRetry(`${API_URL}/verify-evidence/certificate`, {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath }),
    });
  },

  async verifyProject(projectPath) {
    return fetchWithRetry(`${API_URL}/verify-evidence/project`, {
      method: 'POST',
      body: JSON.stringify({ project_path: projectPath }),
    });
  },

  // Submission endpoint
  async submitRecord(data) {
    return fetchWithRetry(`${API_URL}/submit`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Retrieval endpoints
  async getWalletRecords(wallet) {
    return fetchWithRetry(`${API_URL}/wallet/${wallet}`);
  },

  async getTimeline(wallet) {
    return fetchWithRetry(`${API_URL}/timeline/${wallet}`);
  },

  // Reputation endpoints
  async getReputation(wallet) {
    return fetchWithRetry(`${API_URL}/reputation/${wallet}`);
  },

  async verifyWallet(wallet) {
    return fetchWithRetry(`${API_URL}/verify/${wallet}`);
  },

  // Health check
  async health() {
    return fetchWithRetry(`${API_URL}/health`);
  },
};

export { APIError, API_URL };
