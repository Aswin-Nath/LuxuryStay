import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, finalize,map } from 'rxjs/operators';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  role_id: number;
  message: string;
  refresh_token_expires_at?: number;  // Unix timestamp (milliseconds) when refresh token expires
}

@Injectable({
  providedIn: 'root',
})
export class AuthenticationService {
  private readonly baseUrl = `${environment.apiUrl}/auth`;
  private authStateSubject = new BehaviorSubject<boolean>(!!localStorage.getItem('access_token'));
  public authState$ = this.authStateSubject.asObservable();
  private tokenRefreshTimer: any;

  constructor(private http: HttpClient) {
    this.initializeTokenRefresh();
  }

  ngOnDestroy() {
    if (this.tokenRefreshTimer) clearTimeout(this.tokenRefreshTimer);
  }
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
        if (res?.expires_in !== undefined) {
          this.setTokenRefreshTimer(res.expires_in);
        }
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
        // Reset timer with new expiration time
        if (res?.expires_in !== undefined) {
          this.setTokenRefreshTimer(res.expires_in);
        }
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

  /**
   * Initialize token refresh timer on app startup.
   * Checks localStorage for existing expiration time and sets timer.
   */
  private initializeTokenRefresh(): void {
    const expiresIn = localStorage.getItem('expires_in');
    if (expiresIn && Number(expiresIn) > 0) {
      console.debug('AuthenticationService: Initializing token refresh timer', { expiresIn });
      this.setTokenRefreshTimer(Number(expiresIn));
    }
  }

  /**
   * Check if refresh token has expired.
   * @returns true if refresh token is expired; false if valid or unknown
   */
  private isRefreshTokenExpired(): boolean {
    const refreshTokenExpiry = localStorage.getItem('refresh_token_expires_at');
    if (!refreshTokenExpiry) {
      return false;  // If not set, assume valid
    }
    const expiryTime = Number(refreshTokenExpiry);
    const isExpired = Date.now() > expiryTime;
    if (isExpired) {
      console.warn('AuthenticationService: Refresh token has expired');
    }
    return isExpired;
  }

  /**
   * Set a timer to proactively refresh token before expiration.
   * Refreshes 30 seconds before token expires to prevent 401 errors.
   * Also checks if refresh token itself has expired.
   * 
   * @param expiresIn Token expiration time in seconds
   */
  private setTokenRefreshTimer(expiresIn: number): void {
    // Clear existing timer if any
    if (this.tokenRefreshTimer) {
      clearTimeout(this.tokenRefreshTimer);
    }

    // Check if refresh token itself has expired BEFORE scheduling refresh
    if (this.isRefreshTokenExpired()) {
      console.error('AuthenticationService: Refresh token has expired; logging out');
      this.logout().subscribe();
      return;
    }

    // Refresh 30 seconds before expiration 
    const refreshTime = (expiresIn - 30) * 1000;

    if (refreshTime > 0) {
      console.debug('AuthenticationService: Token refresh scheduled in', {
        seconds: Math.round(refreshTime / 1000),
        totalExpiresIn: expiresIn,
        refreshTokenExpiresAt: new Date(Number(localStorage.getItem('refresh_token_expires_at'))).toLocaleString()
      });
      this.tokenRefreshTimer = setTimeout(() => {
        console.debug('AuthenticationService: Proactively refreshing token');
        this.refreshToken().subscribe({
          next: () => {
            console.debug('AuthenticationService: Token proactively refreshed successfully');
          },
          error: (error) => {
            console.error('AuthenticationService: Proactive token refresh failed', error);
            this.logout().subscribe();
          }
        });
      }, refreshTime);
    }
  }
}
