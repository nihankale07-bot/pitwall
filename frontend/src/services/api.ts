import { SessionResponse, DriversResponse, OptimizeRequest, OptimizationResponse } from '../types';

// Configurable backend URL with fallback
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      ...options,
    });

    if (!response.ok) {
      let errorMsg = `Server error: HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch {
        // use fallback text
      }
      throw new ApiError(errorMsg, response.status);
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new Error(err?.message || 'Failed to communicate with PITWALL backend.');
  }
}

export const api = {
  checkHealth: async (): Promise<{ status: string; service: string }> => {
    return request('/health');
  },

  getSessions: async (): Promise<SessionResponse> => {
    return request('/sessions');
  },

  getDrivers: async (sessionKey: number): Promise<DriversResponse> => {
    return request(`/sessions/${sessionKey}/drivers`);
  },

  optimizeStrategy: async (params: OptimizeRequest): Promise<OptimizationResponse> => {
    return request('/optimize', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};
