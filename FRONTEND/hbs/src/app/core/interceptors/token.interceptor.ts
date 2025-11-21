import { Injectable } from '@angular/core';
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest, HttpErrorResponse, HttpResponse } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError, of } from 'rxjs';
import { catchError, filter, switchMap, take, finalize } from 'rxjs/operators';
import { AuthenticationService } from '../services/authentication/authentication.service';
import { Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class TokenInterceptor implements HttpInterceptor {
  private refreshInProgress = false;
  private refreshSubject: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  constructor(private authService: AuthenticationService, private router: Router) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Do not attach auth header for auth endpoints or if there is no access token
    const isAuthRequest = req.url.includes('/auth/login') || req.url.includes('/auth/signup') || req.url.includes('/auth/refresh') || req.url.includes('/auth/otp');

    let authReq = req;
    const accessToken = localStorage.getItem('access_token');
    if (!isAuthRequest && accessToken) {
      authReq = req.clone({ setHeaders: { Authorization: `Bearer ${accessToken}` } });
    }

    return next.handle(authReq).pipe(
      catchError((error: any) => {
        if (error instanceof HttpErrorResponse && error.status === 401 && !isAuthRequest) {
          // Access token might be expired. Attempt refresh and retry.
          return this.handle401Error(authReq, next);
        }
        return throwError(() => error);
      })
    );
  }

  private handle401Error(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (this.refreshInProgress) {
      // If refresh is already in progress, queue request until it's refreshed
      return this.refreshSubject.pipe(
        filter(token => token !== null),
        take(1),
        switchMap(token => {
          const cloned = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
          return next.handle(cloned);
        })
      );
    }

    this.refreshInProgress = true;
    this.refreshSubject.next(null);

    // Call the refresh endpoint (server expects refresh cookie in HttpOnly cookie)
    return this.authService.refreshToken().pipe(
      switchMap((res: any) => {
        // The backend returns new access token as response.access_token
        const newToken = res?.access_token;
        if (newToken) {
          localStorage.setItem('access_token', newToken);
          if (res?.role_id !== undefined) {
            localStorage.setItem('auth_role_id', String(res.role_id));
          }
          this.refreshSubject.next(newToken);
          const cloned = req.clone({ setHeaders: { Authorization: `Bearer ${newToken}` } });
          return next.handle(cloned);
        }
        // If no token in response, treat as failure
        return throwError(() => new Error('No access token in refresh response'));
      }),
      catchError(err => {
        // Refresh failed, route to login and clear storage
        this.logoutAndRedirect();
        return throwError(() => err);
      }),
      finalize(() => {
        this.refreshInProgress = false;
      })
    );
  }

  private logoutAndRedirect() {
    // attempt a server-side logout to remove refresh cookie, then navigate to login
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
