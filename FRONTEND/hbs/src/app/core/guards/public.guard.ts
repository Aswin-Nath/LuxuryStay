import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class PublicGuard implements CanActivate {

  constructor(private router: Router) {}

  canActivate(): boolean {
    const token = localStorage.getItem('access_token');

    if (token) {
      this.router.navigate(['/home_page']);
      return false;
    }

    return true;
  }
}
