import { Injectable } from '@angular/core';
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
  HttpErrorResponse
} from '@angular/common/http';

import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { catchError, filter, switchMap, take, finalize } from 'rxjs/operators';
import { AuthenticationService } from '../services/authentication/authentication.service';
import { Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class TokenInterceptor implements HttpInterceptor {
  private refreshInProgress = false;
  private refreshSubject = new BehaviorSubject<string | null>(null);

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
          console.debug('TokenInterceptor: 401 received; attempting refresh', { url: req.url });
          return this.handle401(authReq, next);
        }
        return throwError(() => err);
      })
    );
  }

  private handle401(req: HttpRequest<any>, next: HttpHandler): Observable<any> {
    if (this.refreshInProgress) {
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

    return this.authService.refreshToken().pipe(
      switchMap((res: any) => {
        const newToken = res?.access_token;

        if (!newToken) {
          return throwError(() => new Error('No access token in refresh response'));
        }

        // Persist new token
        localStorage.setItem('access_token', newToken);
        if (res?.expires_in !== undefined) {
          const ttl = Math.max(0, Number(res.expires_in));
          localStorage.setItem('expires_in', String(ttl));
        }
        if (res?.role_id !== undefined) {
          localStorage.setItem('auth_role_id', String(res.role_id));
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
        console.error('TokenInterceptor: Token refresh failed', error);
        this.forceLogout();
        return throwError(() => error);
      }),

      finalize(() => {
        this.refreshInProgress = false;
      })
    );
  }

  private forceLogout() {
    // stop UI state immediately
    this.authService.setAuthenticated(false);

    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
