import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, Observable } from 'rxjs';
import { AuthenticationService } from '../../../core/services/authentication/authentication.service';
import { BookingStateService } from '../../../services/booking-state.service';
import { DatePickerModalComponent } from '../../../shared/components/date-picker-modal/date-picker-modal.component';
interface Notification {
  type: 'booking' | 'issue' | 'refund' | 'offer';
  msg: string;
  time: string;
}

@Component({
  selector: 'app-customer-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule, RouterLink, FormsModule,DatePickerModalComponent],
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
  // Date Picker Modal Properties
  datePickerCheckIn: string = '';
  datePickerCheckOut: string = '';
  notifications: Notification[] = [
    { type: 'booking', msg: 'New booking: Room 201 confirmed', time: '2m ago' },
    { type: 'issue', msg: 'Issue reported in Room 105', time: '30m ago' },
    { type: 'refund', msg: 'Refund processed for BK#1234', time: '1h ago' }
  ];

  constructor(
    private authService: AuthenticationService,
    private router: Router,
        private bookingStateService: BookingStateService

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
    
    this.showDatePickerModal = true;
    
    // Set default dates
    const today = new Date();
    this.datePickerCheckIn = this.formatDateForInput(today);
    
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.datePickerCheckOut = this.formatDateForInput(tomorrow);
    
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



    onDatePickerClose(): void {
    this.showDatePickerModal = false;
    this.datePickerCheckIn = '';
    this.datePickerCheckOut = '';
    this.datePickerError = '';
  }

  onDatePickerProceed(data: { checkIn: string; checkOut: string; roomTypeId?: number; offerId?: number }): void {
    this.showDatePickerModal = false;
    
    // Store state in service
    this.bookingStateService.setBookingState({
      checkIn: data.checkIn,
      checkOut: data.checkOut
    });
    
    // Navigate without query params
    this.router.navigate(['/booking']);
  }

  logout(): void {
    this.destroy$.next();
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => this.router.navigate(['/login'])
    });
  }
}
