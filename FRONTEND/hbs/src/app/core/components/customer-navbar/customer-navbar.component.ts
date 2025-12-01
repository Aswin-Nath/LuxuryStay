import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
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
  imports: [CommonModule, RouterModule, RouterLink, FormsModule],
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

  // Date Picker Modal Properties
  showDatePickerModal = false;
  checkIn: string = '';
  checkOut: string = '';
  datePickerError: string = '';

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
    // Show date picker modal directly
    this.showDatePickerModal = true;
    
    // Set today as check-in date
    const today = new Date();
    this.checkIn = this.formatDateForInput(today);
    
    // Set tomorrow as check-out date
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.checkOut = this.formatDateForInput(tomorrow);
    
    this.datePickerError = '';
  }

  private formatDateForInput(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  closeBookingModal(): void {
    this.showDatePickerModal = false;
    this.checkIn = '';
    this.checkOut = '';
    this.datePickerError = '';
  }

  calculateNumberOfNights(): number {
    if (!this.checkIn || !this.checkOut) return 0;
    const checkInDate = new Date(this.checkIn);
    const checkOutDate = new Date(this.checkOut);
    const diffTime = checkOutDate.getTime() - checkInDate.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  proceedWithBooking(): void {
    this.datePickerError = '';

    if (!this.checkIn) {
      this.datePickerError = 'Please select a check-in date';
      return;
    }

    if (!this.checkOut) {
      this.datePickerError = 'Please select a check-out date';
      return;
    }

    const checkInDate = new Date(this.checkIn);
    const checkOutDate = new Date(this.checkOut);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (checkInDate < today) {
      this.datePickerError = 'Check-in date cannot be in the past';
      return;
    }

    if (checkOutDate <= checkInDate) {
      this.datePickerError = 'Check-out date must be after check-in date';
      return;
    }

    // Close modal and navigate to booking with dates
    this.showDatePickerModal = false;
    this.router.navigate(['/booking'], {
      queryParams: {
        checkIn: this.checkIn,
        checkOut: this.checkOut
      }
    });
  }

  logout(): void {
    this.destroy$.next();
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
