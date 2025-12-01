import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { BookingsService, BookingResponse } from '../../../services/bookings.service';
import { RoomsService, RoomType } from '../../../core/services/rooms/rooms.service';
import { CustomerNavbarComponent } from '../../../core/components/customer-navbar/customer-navbar.component';
import { Subject } from 'rxjs';
import { CustomerSidebarComponent } from '../../../core/components/customer-sidebar/customer-sidebar.component';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-my-bookings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, CustomerNavbarComponent, CustomerSidebarComponent],
  templateUrl: './my-bookings.component.html',
  styleUrls: ['./my-bookings.component.css']
})
export class MyBookingsComponent implements OnInit, OnDestroy {
  bookings: BookingResponse[] = [];
  filteredBookings: BookingResponse[] = [];
  isLoading = false;
  isLoadingRoomTypes = false;
  isLoadingStatuses = false;
  error: string = '';

  // Filters
  searchTerm: string = '';
  selectedStatus: string = '';
  minAmount: number | null = null;
  maxAmount: number | null = null;
  checkInDate: string = '';
  checkOutDate: string = '';
  selectedRoomType: string = '';

  // Pagination
  currentPage = 1;
  itemsPerPage = 5;
  totalItems = 0;

  // Dynamic options from API
  statusOptions: string[] = [];
  roomTypeOptions: RoomType[] = [];

  private destroy$ = new Subject<void>();

  constructor(
    private bookingsService: BookingsService,
    private roomsService: RoomsService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadStatuses();
    this.loadRoomTypes();
    this.loadBookings();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // Load booking statuses from backend
  loadStatuses(): void {
    this.isLoadingStatuses = true;
    this.bookingsService
      .getBookingStatuses()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: string[]) => {
          this.statusOptions = data;
          this.isLoadingStatuses = false;
        },
        error: (err: any) => {
          console.error('Error loading statuses:', err);
          this.statusOptions = [];
          this.isLoadingStatuses = false;
        }
      });
  }

  // Load room types from backend
  loadRoomTypes(): void {
    this.isLoadingRoomTypes = true;
    this.roomsService
      .getRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: RoomType[]) => {
          this.roomTypeOptions = data;
          this.isLoadingRoomTypes = false;
        },
        error: (err: any) => {
          console.error('Error loading room types:', err);
          this.roomTypeOptions = [];
          this.isLoadingRoomTypes = false;
        }
      });
  }

  loadBookings(): void {
    this.isLoading = true;
    this.error = '';

    const offset = (this.currentPage - 1) * this.itemsPerPage;

    this.bookingsService
      .getCustomerBookings(
        this.selectedStatus || undefined,
        this.itemsPerPage,
        offset,
        this.minAmount || undefined,
        this.maxAmount || undefined,
        this.selectedRoomType || undefined,
        this.checkInDate || undefined,
        this.checkOutDate || undefined
      )
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: BookingResponse[]) => {
          this.bookings = data;
          this.totalItems = data.length;
          this.applyFilters();
          this.isLoading = false;
        },
        error: (err: any) => {
          console.error('Error loading bookings:', err);
          this.error = 'Failed to load bookings. Please try again.';
          this.isLoading = false;
        }
      });
  }

  applyFilters(): void {
    this.filteredBookings = this.bookings.filter((booking) => {
      const matchesSearch =
        this.searchTerm === '' ||
        booking.booking_id.toString().includes(this.searchTerm) ||
        (booking.primary_customer_name || '')
          .toLowerCase()
          .includes(this.searchTerm.toLowerCase());

      const matchesStatus = this.selectedStatus === '' || booking.status === this.selectedStatus;

      const matchesAmount =
        (this.minAmount === null || booking.total_price >= this.minAmount) &&
        (this.maxAmount === null || booking.total_price <= this.maxAmount);

      return matchesSearch && matchesStatus && matchesAmount;
    });

    this.currentPage = 1;
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.selectedStatus = '';
    this.minAmount = null;
    this.maxAmount = null;
    this.checkInDate = '';
    this.checkOutDate = '';
    this.selectedRoomType = '';
    this.currentPage = 1;
    this.loadBookings();
  }

  onSearchChange(): void {
    this.applyFilters();
  }

  onStatusChange(): void {
    this.loadBookings();
  }

  onFilterChange(): void {
    this.applyFilters();
  }

  viewBookingDetails(bookingId: number): void {
    this.router.navigate(['/booking', bookingId]);
  }

  getStatusBadgeClass(status: string): string {
    const statusClasses: { [key: string]: string } = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
      'checked-in': 'bg-green-100 text-green-800',
      'checked-out': 'bg-purple-100 text-purple-800',
      cancelled: 'bg-red-100 text-red-800'
    };
    return statusClasses[status] || 'bg-gray-100 text-gray-800';
  }

  getStatusIcon(status: string): string {
    const icons: { [key: string]: string } = {
      pending: 'schedule',
      confirmed: 'check_circle',
      'checked-in': 'hotel',
      'checked-out': 'logout',
      cancelled: 'cancel'
    };
    return icons[status] || 'info';
  }

  // Pagination methods
  get totalPages(): number {
    return Math.ceil(this.filteredBookings.length / this.itemsPerPage);
  }

  get paginatedBookings(): BookingResponse[] {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    return this.filteredBookings.slice(startIndex, endIndex);
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  formatBookingDate(dateTimeString?: string): string {
    if (!dateTimeString) return 'N/A';
    const date = new Date(dateTimeString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }) + ' ' + date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // Calculate duration of booking in days
  calculateDuration(checkIn: string, checkOut: string): number {
    const start = new Date(checkIn);
    const end = new Date(checkOut);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  // Normalize min amount - handle negative numbers
  normalizeMinAmount(): void {
    if (this.minAmount !== null && this.minAmount < 0) {
      this.minAmount = null;
    }
  }

  // Normalize max amount - handle negative numbers
  normalizeMaxAmount(): void {
    if (this.maxAmount !== null && this.maxAmount < 0) {
      this.maxAmount = null;
    }
  }

  // Event handlers for filter changes
  onDateChange(): void {
    this.currentPage = 1;
    this.loadBookings();
  }

  onRoomTypeChange(): void {
    this.currentPage = 1;
    this.loadBookings();
  }
}
