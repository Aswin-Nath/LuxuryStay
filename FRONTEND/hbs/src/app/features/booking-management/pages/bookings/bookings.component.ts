import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { BookingsService, BookingResponse } from '../../../../shared/services/bookings.service';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';

@Component({
  selector: 'app-admin-bookings',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './bookings.html',
  styleUrl: './bookings.css',
})
export class AdminBookingsComponent implements OnInit, OnDestroy {
  bookings: BookingResponse[] = [];
  filteredBookings: BookingResponse[] = [];
  loading = false;
  error = '';
  Math = Math;  // Expose Math to template
  
  // Filter properties
  searchQuery = '';
  filterStatus = 'all';
  minAmount: number | null = null;
  maxAmount: number | null = null;
  filterRoomType = 'all';
  dateFrom = '';
  dateTo = '';

  // Pagination
  currentPage = 1;
  bookingsPerPage = 10;
  totalBookings = 0;

  // Status options
  statusOptions = ['Active', 'Completed', 'Cancelled', 'Pending', 'No Show'];
  roomTypeOptions: any[] = [];

  private destroy$ = new Subject<void>();

  constructor(
    private bookingsService: BookingsService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadBookings();
    this.loadRoomTypes();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadBookings(): void {
    this.loading = true;
    this.error = '';

    // Call API to get all bookings (admin view)
    // For now, we'll use the customer endpoint with admin context
    this.bookingsService
      .getAdminBookings(
        this.filterStatus !== 'all' ? this.filterStatus : undefined,
        this.bookingsPerPage,
        (this.currentPage - 1) * this.bookingsPerPage,
        this.minAmount || undefined,
        this.maxAmount || undefined,
        this.filterRoomType !== 'all' ? this.filterRoomType : undefined,
        this.dateFrom || undefined,
        this.dateTo || undefined,
      )
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: any) => {
            console.log("data",data);
          this.bookings = data
          this.totalBookings =  data.length;
          this.applyFilters();
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Failed to load bookings';
          this.loading = false;
          console.error('Error loading bookings:', err);
        },
      });
  }

  loadRoomTypes(): void {
    this.bookingsService
      .getRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.roomTypeOptions = data.results || [];
        },
        error: (err) => {
          console.error('Error loading room types:', err);
        },
      });
  }

  applyFilters(): void {
    this.filteredBookings = this.bookings.filter((booking) => {
      const matchesSearch =
        !this.searchQuery ||
        booking.booking_id.toString().includes(this.searchQuery) ||
        booking.primary_customer_name?.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        booking.primary_customer_phone_number?.includes(this.searchQuery);

      const matchesStatus = this.filterStatus === 'all' || booking.status === this.filterStatus;

      return matchesSearch && matchesStatus;
    });
  }

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadBookings();
  }

  resetFilters(): void {
    this.searchQuery = '';
    this.filterStatus = 'all';
    this.minAmount = null;
    this.maxAmount = null;
    this.filterRoomType = 'all';
    this.dateFrom = '';
    this.dateTo = '';
    this.currentPage = 1;
    this.loadBookings();
  }

  viewBooking(bookingId: number): void {
    this.router.navigate(['/admin/bookings/booking', bookingId]);
  }

  getStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'active':
      case 'confirmed':
        return 'bg-blue-100 text-blue-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'no show':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  getStatusIcon(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'check_circle';
      case 'active':
      case 'confirmed':
        return 'access_time';
      case 'cancelled':
        return 'cancel';
      case 'pending':
        return 'schedule';
      case 'no show':
        return 'warning';
      default:
        return 'info';
    }
  }

  formatDate(date: string): string {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(price);
  }

  get paginatedBookings(): BookingResponse[] {
    const start = (this.currentPage - 1) * this.bookingsPerPage;
    return this.filteredBookings.slice(start, start + this.bookingsPerPage);
  }

  get totalPages(): number {
    return Math.ceil(this.filteredBookings.length / this.bookingsPerPage);
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }
}