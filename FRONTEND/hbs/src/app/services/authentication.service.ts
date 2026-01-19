import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, finalize, map } from 'rxjs/operators';

// ===== Authentication Interfaces =====
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  role_id: number;
  message: string;
  refresh_token_expires_at?: number;  // Unix timestamp (milliseconds) when refresh token expires
}

// ===== Admin Management Interfaces =====
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
  password: string;
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

export interface AdminListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  limit: number;
}

// ===== Role Management Interfaces =====
export interface Role {
  role_id: number;
  role_name: string;
  role_description?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Permission {
  permission_id: number;
  permission_name: string;
}

export interface PermissionGroup {
  resource: string; // ADMIN_CREATION, ROOM_MANAGEMENT, etc.
  permissions: PermissionAction[];
}

export interface PermissionAction {
  action: string; // READ, WRITE, DELETE, UPDATE
  permission_id: number;
  permission_name: string;
}

export interface RolePermissions {
  role_id: number;
  role_name: string;
  permissions: Permission[];
  permission_ids: number[];
}

export interface AssignPermissionsRequest {
  permission_ids: number[];
}

@Injectable({
  providedIn: 'root',
})
export class AuthenticationService {
  private readonly baseUrl = `${environment.apiUrl}/auth`;
  private readonly apiUrl = `${environment.apiUrl}`;
  
  // Initialize authStateSubject with localStorage value - if token exists, user is logged in
  private authStateSubject = new BehaviorSubject<boolean>(!!localStorage.getItem('access_token'));
  public authState$ = this.authStateSubject.asObservable();
  
  // ===== Permission Service Properties =====
  private userScopes = new BehaviorSubject<Set<string>>(new Set());
  public permissions$ = this.userScopes.asObservable();

  constructor(private http: HttpClient) {
    // Subscribe to ensure we stay in sync with localStorage
    this.authState$.subscribe(state => {
      console.debug('🔐 AuthenticationService: Auth state changed to', state);
    });
  }

  // ===== Authentication Methods =====
  fetchUserPermissions(): Observable<string[]> {
    return this.http.get<any>(`${environment.apiUrl}/roles/me`, {
      withCredentials: true
    }).pipe(
      tap(res => {
        console.debug("Fetched user permissions:", res.permissions);
      }),
      map(res => res.permissions)
    );
  }

  login(identifier: string, password: string): Observable<TokenResponse> {
    const body = new URLSearchParams();
    body.set('username', identifier);
    body.set('password', password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded',
    });

    return this.http.post<TokenResponse>(`${this.baseUrl}/login`, body.toString(), {
      headers,
      withCredentials: true,
    }).pipe(
      tap((res) => {
        // Store access token and expiration
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('expires_in', String(res.expires_in));
        localStorage.setItem('auth_role_id', String(res.role_id));
        
        // ✅ Store refresh token expiration (Unix timestamp in milliseconds)
        if (res.refresh_token_expires_at) {
          localStorage.setItem('refresh_token_expires_at', String(res.refresh_token_expires_at));
          console.debug('AuthenticationService: Refresh token expires at', new Date(res.refresh_token_expires_at));
        }
        
        this.authStateSubject.next(true);
      })
    );
  }

  requestOtp(email: string, verificationType: string = 'PASSWORD_RESET') {
    const payload = { email, verification_type: verificationType };
    // Include credentials so HttpOnly refresh cookie is sent when necessary
    return this.http.post<any>(`${this.baseUrl}/otp/request`, payload, { withCredentials: true });
  }

  verifyOtp(email: string, otp: string, verificationType: string = 'PASSWORD_RESET', newPassword?: string) {
    const payload: any = { email, otp, verification_type: verificationType };
    if (newPassword) payload.new_password = newPassword;
    // Include credentials so backend OTP verification/ password reset uses refresh cookie if required
    return this.http.post<any>(`${this.baseUrl}/otp/verify`, payload, { withCredentials: true });
  }

  refreshToken() {
    // NOTE: refresh token is stored in HttpOnly cookie by server, send credentials so cookie is included
    return this.http.post<TokenResponse>(`${this.baseUrl}/refresh`, {}, { withCredentials: true }).pipe(
      tap((res) => {
        console.debug('AuthenticationService: refreshToken response', res);
        
        // Update token and expiration in localStorage
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('expires_in', String(res.expires_in));
        
        // ✅ Also update refresh token expiration if provided
        if (res.refresh_token_expires_at) {
          localStorage.setItem('refresh_token_expires_at', String(res.refresh_token_expires_at));
          console.debug('AuthenticationService: Refresh token expiration updated', new Date(res.refresh_token_expires_at));
        }
        
        this.authStateSubject.next(true);
      })
    );
  }

    logout() {
      // Ask server to invalidate refresh cookie (return void), include credentials for cookie
      // Use finalize to ensure local state is cleared even if the request errors
      return this.http.post(`${this.baseUrl}/logout`, {}, { withCredentials: true }).pipe(
        finalize(() => {
          this.clearLocalAuthState();
          this.authStateSubject.next(false);
        })
      );
    }

  clearLocalAuthState() {
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('expires_in');
      localStorage.removeItem('auth_role_id');
      localStorage.removeItem('permissions');
      localStorage.removeItem('refresh_token_expires_at');  // ✅ Also clear refresh token expiration
    } catch (err) {
      // ignore errors for read-only/private environments
    }
  }

  // Helper to set auth state programmatically if needed
  setAuthenticated(value: boolean) {
    this.authStateSubject.next(value);
  }

  // ===== Admin Management Methods =====
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
   * Check if email is unique (for validation)
   */
  checkEmailUnique(email: string): Observable<{ available: boolean }> {
    return this.http.get<{ available: boolean }>(`${this.apiUrl}/users/check-email`, {
      params: { email }
    });
  }

  // ===== Signup Method =====
  /**
   * User signup
   */
  signup(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/signup`, payload, { withCredentials: true });
  }

  // ===== Permission Service Methods =====
  /**
   * Load user permissions/scopes
   */
  loadPermissions(scopes: string[]): void {
    console.log("🔐 Loaded Scopes in AuthenticationService:", scopes);
    console.log("🔐 Total permissions:", scopes.length);
    scopes.forEach(s => console.log("  ✓", s));
    this.userScopes.next(new Set(scopes));
  }

  /**
   * Check if user has a specific permission
   */
  hasPermission(scope: string): boolean {
    return this.userScopes.value.has(scope);
  }

  /**
   * Check if user has all specified permissions
   */
  hasAll(scopes: string[]): boolean {
    const current = this.userScopes.value;
    return scopes.every(s => current.has(s));
  }

  // ===== Role Management Methods =====
  /**
   * Get all roles
   */
  getRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(`${this.apiUrl}/roles`);
  }

  /**
   * Create a new role
   */
  createRole(roleData: { role_name: string; role_description: string }): Observable<Role> {
    return this.http.post<Role>(`${this.apiUrl}/roles`, roleData);
  }

  /**
   * Get all permissions grouped by resource
   */
  getPermissionsGrouped(): Observable<PermissionGroup[]> {
    return this.http.get<Permission[]>(`${this.apiUrl}/roles/all-permissions`).pipe(
      // Transform flat permission list to grouped structure
      (source: any) => new Observable(observer => {
        source.subscribe({
          next: (permissions: Permission[]) => {
            const grouped = this.groupPermissions(permissions);
            observer.next(grouped);
            observer.complete();
          },
          error: (err: any) => observer.error(err)
        });
      })
    );
  }

  /**
   * Get all permissions
   */
  getPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(`${this.apiUrl}/roles/all-permissions`);
  }

  /**
   * Get permissions for a specific role
   */
  getRolePermissions(roleId: number): Observable<Permission[]> {
    const params = new HttpParams().set('role_id', roleId.toString());
    return this.http.get<Permission[]>(`${this.apiUrl}/roles/permissions`, { params, withCredentials: true });
  }

  /**
   * Assign permissions to a role
   */
  assignPermissionsToRole(
    roleId: number,
    permissionIds: number[]
  ): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/roles/assign`,
      {
        role_id: roleId,
        permission_ids: permissionIds
      }
    );
  }

  /**
   * Group permissions by resource and action
   */
  private groupPermissions(permissions: Permission[]): PermissionGroup[] {
    const groupMap: { [key: string]: PermissionAction[] } = {};

    permissions.forEach((perm: Permission) => {
      const [resource, action] = perm.permission_name.split(':');

      if (!groupMap[resource]) {
        groupMap[resource] = [];
      }

      groupMap[resource].push({
        action: action || 'OTHER',
        permission_id: perm.permission_id,
        permission_name: perm.permission_name
      });
    });

    // Convert map to array and sort by resource name
    return Object.entries(groupMap)
      .map(([resource, permissions]) => ({
        resource,
        permissions: permissions.sort((a, b) =>
          this.getActionOrder(a.action) - this.getActionOrder(b.action)
        )
      }))
      .sort((a, b) => a.resource.localeCompare(b.resource));
  }

  /**
   * Get sort order for permission actions
   */
  private getActionOrder(action: string): number {
    const order: { [key: string]: number } = {
      'READ': 1,
      'WRITE': 2,
      'UPDATE': 3,
      'DELETE': 4
    };
    return order[action] || 99;
  }

  /**
   * Transform grouped permissions to flat permission IDs
   */
  getSelectedPermissionIds(selectedGroups: {
    [resource: string]: string[]
  }): number[] {
    // This will be implemented based on how we track selected permissions
    return [];
  }
}
