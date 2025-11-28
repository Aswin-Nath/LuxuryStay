import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterModule } from '@angular/router';
import { Subject, Observable } from 'rxjs';
import { AuthenticationService } from '../../services/authentication/authentication.service';

interface Notification {
  type: 'booking' | 'issue' | 'refund' | 'offer';
  msg: string;
  time: string;
}

@Component({
  selector: 'app-customer-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule, RouterLink],
  templateUrl: './customer-navbar.component.html',
  styleUrls: ['./customer-navbar.component.css']
})
export class CustomerNavbarComponent implements OnInit, OnDestroy {
  public isLoggedIn$: Observable<boolean>;
  private readonly destroy$ = new Subject<void>();

  isMobileMenuOpen = false;
  isNotifDropdownOpen = false;
  isNotifDropdownMobileOpen = false;
  isNavbarVisible = true;
  private lastScrollY = 0;

  notifications: Notification[] = [
    { type: 'booking', msg: 'New booking: Room 201 confirmed', time: '2m ago' },
    { type: 'issue', msg: 'Issue reported in Room 105', time: '30m ago' },
    { type: 'refund', msg: 'Refund processed for BK#1234', time: '1h ago' }
  ];

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {
    this.isLoggedIn$ = this.authService.authState$;
  }

  ngOnInit(): void { }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  @HostListener('window:scroll', [])
  onWindowScroll(): void {
    if (window.innerWidth < 768) {
      if (window.scrollY > this.lastScrollY) {
        this.isNavbarVisible = false;
      } else {
        this.isNavbarVisible = true;
      }
    } else {
      this.isNavbarVisible = true;
    }
    this.lastScrollY = window.scrollY;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.notif-dropdown-container')) {
      this.isNotifDropdownOpen = false;
      this.isNotifDropdownMobileOpen = false;
    }
  }

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }

  toggleNotifDropdown(event: Event): void {
    event.stopPropagation();
    this.isNotifDropdownOpen = !this.isNotifDropdownOpen;
    this.isNotifDropdownMobileOpen = false;
  }

  toggleNotifDropdownMobile(event: Event): void {
    event.stopPropagation();
    this.isNotifDropdownMobileOpen = !this.isNotifDropdownMobileOpen;
    this.isNotifDropdownOpen = false;
  }

  getNotifIcon(type: string): string {
    switch (type) {
      case 'booking': return 'fa-calendar-check text-green-600';
      case 'issue': return 'fa-exclamation-triangle text-red-600';
      case 'refund': return 'fa-money-bill-wave text-yellow-500';
      case 'offer': return 'fa-tag text-blue-600';
      default: return 'fa-bell text-gray-500';
    }
  }

  openBookingModal(): void {
    // Emit event or navigate to booking
    console.log('Open booking modal');
  }

  logout(): void {
    this.destroy$.next();
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
