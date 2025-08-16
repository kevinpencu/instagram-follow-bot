const API_BASE_URL = 'http://localhost:5001';

export interface Profile {
  ads_power_id: string;
  username: string;
  profile_name: string;
}

export interface ProfileStatus {
  ads_power_id: string;
  username: string;
  bot_status: 'scheduled' | 'running' | 'done' | 'failed' | 'seleniumFailed' | 'adsPowerFailed' | 'followblocked' | 'accountLoggedOut' | 'notargets';
  total_accounts: number;
  total_followed: number;
  total_follow_failed: number;
  total_already_followed: number;
}

export interface StatusResponse {
  activeProfiles: Record<string, ProfileStatus>;
  scheduled: string[];
}

export interface ApiError {
  error: string;
  message: string;
}

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        error: 'network_error',
        message: 'Network request failed',
      }));
      throw new Error(errorData.message);
    }

    return response.json();
  }

  async getProfiles(): Promise<Profile[]> {
    return this.request<Profile[]>('/profiles');
  }

  async getStatus(): Promise<StatusResponse> {
    return this.request<StatusResponse>('/status');
  }

  async startAll(maxWorkers?: number, acceptFollowRequests?: boolean): Promise<{}> {
    const body: any = {};
    if (maxWorkers) body.maxWorkers = maxWorkers;
    if (acceptFollowRequests !== undefined) body.acceptFollowRequests = acceptFollowRequests;
    
    return this.request<{}>('/start-all', {
      method: 'POST',
      body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
    });
  }

  async stopAll(): Promise<{}> {
    return this.request<{}>('/stop-all', {
      method: 'POST',
    });
  }


  async startSelected(adsPowerIds: string[], maxWorkers?: number, acceptFollowRequests?: boolean): Promise<{}> {
    const body: any = { adsPowerIds };
    if (maxWorkers) body.maxWorkers = maxWorkers;
    if (acceptFollowRequests !== undefined) body.acceptFollowRequests = acceptFollowRequests;
    
    return this.request<{}>('/start-selected', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }
}

export const apiService = new ApiService();
