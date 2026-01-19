import { Injectable } from '@angular/core';
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
  HttpErrorResponse
} from '@angular/common/http';

import { Observable, BehaviorSubject, throwError, timer } from 'rxjs';
import { catchError, filter, switchMap, take, finalize, retry } from 'rxjs/operators';
import { AuthenticationService } from '../../services/authentication.service';
import { Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class TokenInterceptor implements HttpInterceptor {
  private refreshInProgress = false;
  private refreshSubject = new BehaviorSubject<string | null>(null);
  private readonly MAX_RETRY_ATTEMPTS = 2;
  private readonly RETRY_DELAY_MS = 1000;

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const isAuthRequest =
      req.url.includes('/auth/login') ||
      req.url.includes('/auth/signup') ||
      req.url.includes('/auth/otp') ||
      req.url.includes('/auth/refresh') ||
      req.url.includes('/auth/logout');
    const accessToken = localStorage.getItem('access_token');

    let authReq = req;
    if (!isAuthRequest && accessToken) {
      authReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${accessToken}`
        },
        withCredentials: true  // ✅ REQUIRED for HttpOnly refresh cookie
      });
    } else if (isAuthRequest) {
      // ✅ Also add withCredentials to auth requests to handle refresh cookie
      authReq = req.clone({
        withCredentials: true
      });
    }

    return next.handle(authReq).pipe(
      catchError(err => {
        if (err instanceof HttpErrorResponse && err.status === 401 && !isAuthRequest) {
          console.debug('🔄 TokenInterceptor: 401 received; attempting refresh', { url: req.url });
          return this.handle401(authReq, next);
        }
        return throwError(() => err);
      })
    );
  }

  private handle401(req: HttpRequest<any>, next: HttpHandler): Observable<any> {
    // ✅ CRITICAL: Check if refresh token itself has expired BEFORE attempting refresh
    const refreshTokenExpiry = localStorage.getItem('refresh_token_expires_at');
    if (refreshTokenExpiry && Date.now() > Number(refreshTokenExpiry)) {
      console.error('❌ TokenInterceptor: Refresh token has EXPIRED; forcing logout');
      this.forceLogout();
      return throwError(() => new Error('Refresh token expired'));
    }

    // ✅ Check if refresh is already in progress
    if (this.refreshInProgress) {
      console.debug('⏳ TokenInterceptor: Refresh already in progress; queuing request');
      return this.refreshSubject.pipe(
        filter(token => token !== null),
        take(1),
        switchMap(token => {
          const cloned = req.clone({
            setHeaders: { Authorization: `Bearer ${token}` },
            withCredentials: true
          });
          return next.handle(cloned);
        })
      );
    }

    this.refreshInProgress = true;
    this.refreshSubject.next(null);

    console.debug('🔄 TokenInterceptor: Starting token refresh...');

    // Attempt refresh with retry logic for network errors
    return this.authService.refreshToken().pipe(
      // Retry 2 times with 1 second delay for transient errors (not 401)
      retry({
        count: this.MAX_RETRY_ATTEMPTS,
        delay: (error, retryCount) => {
          // Only retry on transient errors (5xx, network timeout, etc)
          // DO NOT retry on 401/403 (permanent auth failures)
          if (error instanceof HttpErrorResponse && error.status >= 400 && error.status < 500) {
            console.error('❌ TokenInterceptor: Permanent client error (4xx), not retrying', {
              status: error.status,
              statusText: error.statusText
            });
            throw error;
          }
          console.warn('⚠️ TokenInterceptor: Transient error, retrying...', { retryCount, error: error?.message });
          return timer(this.RETRY_DELAY_MS * retryCount);
        }
      }),

      switchMap((res: any) => {
        const newToken = res?.access_token;

        if (!newToken) {
          console.error('❌ TokenInterceptor: No access token in refresh response');
          return throwError(() => new Error('No access token in refresh response'));
        }

        console.debug('✅ TokenInterceptor: Token refresh successful', {
          expiresIn: res.expires_in,
          refreshTokenExpiresAt: new Date(res.refresh_token_expires_at).toLocaleString()
        });

        // Persist new token
        localStorage.setItem('access_token', newToken);
        if (res?.expires_in !== undefined) {
          const ttl = Math.max(0, Number(res.expires_in));
          localStorage.setItem('expires_in', String(ttl));
        }
        if (res?.role_id !== undefined) {
          localStorage.setItem('auth_role_id', String(res.role_id));
        }
        // ✅ Also update refresh token expiration if provided
        if (res?.refresh_token_expires_at !== undefined) {
          localStorage.setItem('refresh_token_expires_at', String(res.refresh_token_expires_at));
          console.debug('🔐 TokenInterceptor: Refresh token expiration updated', new Date(res.refresh_token_expires_at).toLocaleString());
        }

        // notify queued requests
        this.refreshSubject.next(newToken);

        const cloned = req.clone({
          setHeaders: { Authorization: `Bearer ${newToken}` },
          withCredentials: true  // ✅ Maintain credentials for retried request
        });

        return next.handle(cloned);
      }),

      catchError(error => {
        console.error('❌ TokenInterceptor: Token refresh failed after retries', {
          status: error?.status,
          statusText: error?.statusText,
          message: error?.message
        });

        // Check the error type
        if (error instanceof HttpErrorResponse) {
          if (error.status === 401 || error.status === 403) {
            console.error('🔓 TokenInterceptor: Auth error (401/403) - refresh token may be invalid or expired');
          } else if (error.status >= 500) {
            console.error('🔥 TokenInterceptor: Server error (5xx)');
          } else if (error.status === 0) {
            console.error('🌐 TokenInterceptor: Network error');
          }
        }

        this.forceLogout();
        return throwError(() => error);
      }),

      finalize(() => {
        this.refreshInProgress = false;
      })
    );
  }

  private forceLogout() {
    console.log('🚪 TokenInterceptor: Force logging out user');
    // stop UI state immediately
    this.authService.setAuthenticated(false);

    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
