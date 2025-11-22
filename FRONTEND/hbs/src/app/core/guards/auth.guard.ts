import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthenticationService } from '../services/authentication/authentication.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(
    private router: Router,
    private authService: AuthenticationService
  ) {}

  canActivate(): boolean {
    const token = localStorage.getItem('access_token');
    const expiresIn = localStorage.getItem('expires_in');

    if (!token) {
      this.router.navigate(['/login']);
      return false;
    }

    // Check if token is expired (expires_in is in seconds)
    if (expiresIn && Number(expiresIn) <= 0) {
      console.debug('AuthGuard: Token expired, attempting refresh');
      this.authService.refreshToken().subscribe({
        next: () => {
          console.debug('AuthGuard: Token refreshed successfully');
          return true;
        },
        error: (err) => {
          console.error('AuthGuard: Token refresh failed, redirecting to login', err);
          this.router.navigate(['/login']);
          return false;
        }
      });
      return false;
    }

    return true;
  }
}
