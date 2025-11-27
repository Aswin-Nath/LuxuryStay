import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, finalize,map } from 'rxjs/operators';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  role_id: number;
  message: string;
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
   * Set a timer to proactively refresh token before expiration.
   * Refreshes 30 seconds before token expires to prevent 401 errors.
   * 
   * @param expiresIn Token expiration time in seconds
   */
  private setTokenRefreshTimer(expiresIn: number): void {
    // Clear existing timer if any
    if (this.tokenRefreshTimer) {
      clearTimeout(this.tokenRefreshTimer);
    }

    // Refresh 30 seconds before expiration 
    const refreshTime = (expiresIn - 30) * 1000;

    if (refreshTime > 0) {
      console.debug('AuthenticationService: Token refresh scheduled in', {
        seconds: Math.round(refreshTime / 1000),
        totalExpiresIn: expiresIn
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
