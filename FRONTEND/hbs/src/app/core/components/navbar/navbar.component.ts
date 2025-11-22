import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { Subject, Observable } from 'rxjs';
// no rxjs/operators imports needed for navbar after removing polling
import { AuthenticationService } from '../../services/authentication/authentication.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.css']
})
export class NavbarComponent implements OnInit, OnDestroy {
  public isLoggedIn$: Observable<boolean>;
  private readonly destroy$ = new Subject<void>();

  constructor(private authService: AuthenticationService, private router: Router) {
    this.isLoggedIn$ = this.authService.authState$;
  }

  ngOnInit(): void {
    // No polling here — the token refresh is handled by the interceptor on 401s.
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  logout() {
    this.destroy$.next();
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
