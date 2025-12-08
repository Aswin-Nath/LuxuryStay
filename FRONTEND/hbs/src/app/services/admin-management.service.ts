import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AdminUser {
  user_id: number;
  full_name: string;
  email: string;
  phone_number?: string;
  role_id: number;
  role_name?: string;
  status?: string;
  status_id?: number;
  suspend_reason?: string;
  created_at?: string;
  dob?: string;
  gender?: string;
  profile_image_url?: string;
}

export interface CreateAdminPayload {
  full_name: string;
  email: string;
  password?: string;
  phone_number: string;
  dob: string;
  gender: string;
  role_id: number;
}

export interface UpdateAdminPayload {
  full_name?: string;
  phone_number?: string;
  role_id?: number;
  status?: string;
}

export interface Role {
  role_id: number;
  role_name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AdminListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  limit: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminManagementService {
  private apiUrl = `${environment.apiUrl}`;

  constructor(private http: HttpClient) {}

  /**
   * Fetch list of admin users with filtering and pagination
   */
  listAdmins(params: {
    page?: number;
    limit?: number;
    search?: string;
    role_id?: number;
    status?: string;
    date_from?: string;
    date_to?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  } = {}): Observable<AdminListResponse> {
    let httpParams = new HttpParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        httpParams = httpParams.set(key, value.toString());
      }
    });

    // Note: Backend might need a dedicated endpoint for listing users
    // For now, using a placeholder - adjust based on actual backend endpoint
    return this.http.get<AdminListResponse>(`${this.apiUrl}/users/list`, { params: httpParams });
  }

  /**
   * Create new admin user
   */
  createAdmin(payload: CreateAdminPayload): Observable<AdminUser> {
    return this.http.post<AdminUser>(`${this.apiUrl}/auth/register`, payload);
  }

  /**
   * Update existing admin user
   */
  updateAdmin(userId: number, payload: UpdateAdminPayload): Observable<AdminUser> {
    return this.http.put<AdminUser>(`${this.apiUrl}/users/${userId}`, payload);
  }

  /**
   * Suspend or activate admin user
   */
  suspendAdmin(userId: number, suspend: boolean, reason?: string): Observable<any> {
    if (suspend) {
      // Suspend user
      if (!reason) {
        throw new Error('Suspension reason is required');
      }
      const payload = { suspend_reason: reason };
      return this.http.post(`${this.apiUrl}/users/${userId}/suspend`, payload);
    } else {
      // Unsuspend user
      return this.http.post(`${this.apiUrl}/users/${userId}/unsuspend`, {});
    }
  }

  /**
   * Get single admin user details
   */
  getAdmin(userId: number): Observable<AdminUser> {
    return this.http.get<AdminUser>(`${this.apiUrl}/users/${userId}`);
  }

  /**
   * Fetch all available roles
   */
  getRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(`${this.apiUrl}/roles`);
  }

  /**
   * Check if email is unique (for validation)
   */
  checkEmailUnique(email: string): Observable<{ available: boolean }> {
    return this.http.get<{ available: boolean }>(`${this.apiUrl}/users/check-email`, {
      params: { email }
    });
  }
}
