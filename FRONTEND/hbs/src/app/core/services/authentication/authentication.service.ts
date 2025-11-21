import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

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
  private readonly baseUrl = 'http://localhost:8000/auth';

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
    });
  }

  requestOtp(email: string, verificationType: string = 'PASSWORD_RESET') {
    const payload = { email, verification_type: verificationType };
    return this.http.post<any>(`${this.baseUrl}/otp/request`, payload, {});
  }

  verifyOtp(email: string, otp: string, verificationType: string = 'PASSWORD_RESET', newPassword?: string) {
    const payload: any = { email, otp, verification_type: verificationType };
    if (newPassword) payload.new_password = newPassword;
    return this.http.post<any>(`${this.baseUrl}/otp/verify`, payload);
  }

  refreshToken() {
    // NOTE: refresh token is stored in HttpOnly cookie by server, send credentials so cookie is included
    return this.http.post<TokenResponse>(`${this.baseUrl}/refresh`, {}, { withCredentials: true });
  }

  logout() {
    // Ask server to invalidate refresh cookie (return void), include credentials for cookie
    return this.http.post(`${this.baseUrl}/logout`, {}, { withCredentials: true }).pipe(
      tap(() => this.clearLocalAuthState())
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
}
