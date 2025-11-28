import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class PublicGuard implements CanActivate {

  constructor(private router: Router) {}

  canActivate(): boolean {
    const token = localStorage.getItem('access_token');
    const role_id=localStorage.getItem("auth_role_id");
    if (token) {
      if(role_id=="1"){
        this.router.navigate(['/dashboard']);
      }
      else{
        this.router.navigate(['admin/dashboard']);
      }
  }
    return true;
  }
}
