import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, finalize } from 'rxjs/operators';

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

  constructor(private http: HttpClient) {}

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
      tap(() => this.authStateSubject.next(true))
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
}
