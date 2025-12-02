import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { BookingsService, BookingResponse, BookingRoomMapResponse } from '../../../services/bookings.service';
import { AdminNavbarComponent } from '../../../core/components/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../core/components/admin-sidebar/admin-sidebar.component';

@Component({
  selector: 'app-admin-booking-details',
  standalone: true,
  imports: [CommonModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './admin-booking-details.component.html',
  styleUrl: './admin-booking-details.component.css',
})
export class AdminBookingDetailsComponent implements OnInit, OnDestroy {
  bookingId: number=0;
  booking: BookingResponse | null = null;
  rooms: BookingRoomMapResponse[] = [];
  payments: any[] = [];
  issues: any[] = [];
  reviews: any[] = [];
  reviewsLoading = false;
  loading = true;
  error = '';
  roomTypes:Map<number,any> = new Map();
  private destroy$ = new Subject<void>();

  constructor(
    private bookingsService: BookingsService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      if (params['id']) {
        this.bookingId = parseInt(params['id'], 10);
        this.loadBookingDetails();
      } else {
        this.error = 'Invalid booking ID';
        this.loading = false;
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

getRoomTypePrice(roomTypeId: number): number | null {
    const roomType = this.roomTypes.get(roomTypeId);
    return roomType ? roomType.price_per_night : null;
  }

  
  loadBookingDetails(): void {
    this.loading = true;
    this.error = '';

    // Load room types first
    this.bookingsService
      .getRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (roomTypesData: any) => {
          if (roomTypesData.results && Array.isArray(roomTypesData.results)) {
            this.roomTypes = new Map(roomTypesData.results.map((rt: any) => [rt.room_type_id, rt]));
          }
          this.loadBookingWithDetails();
        },
        error: (err: any) => {
          console.error('Error loading room types:', err);
          this.loadBookingWithDetails();
        }
      });
  }

  private loadBookingWithDetails(): void {
    this.bookingsService
      .getAdminBookingDetails(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: BookingResponse) => {
          this.booking = data;
          console.log("BOOKING DATA1",this.booking);
          // Populate room prices from cached roomTypes Map
          if (this.booking.rooms) {
            this.rooms=this.booking.rooms;
            this.booking.rooms.forEach((room) => {
              const roomTypePrice = this.getRoomTypePrice(room.room_type_id);
              if (roomTypePrice !== null) {
                room.price_per_night = roomTypePrice;
              }
            });
          }
            console.log("BOOKING DATA2",this.booking);
          this.loadPayments();
          this.loadReviews();
          this.loadIssues();
          this.loading = false;
        },
        error: (err: any) => {
          console.error('Error loading booking details:', err);
          this.error = 'Failed to load booking details. Please try again.';
          this.loading = false;
        }
      });
  }

  private loadPayments(): void {
    if (!this.booking) return;

    // Call the payments endpoint to get booking payments
    this.bookingsService
      .getPaymentsByBooking(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (payments: any[]) => {
          if (this.booking) {
            this.booking.payments = payments;
          }
        },
        error: (err: any) => {
          console.error('Error loading payments:', err);
          if (this.booking) {
            this.booking.payments = [];
          }
        }
      });
  }

  private loadReviews(): void {
    if (!this.bookingId) return;
    
    this.reviewsLoading = true;
    this.bookingsService
      .getReviewsByBooking(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (reviews: any[]) => {
          this.reviews = reviews || [];
          this.reviewsLoading = false;
        },
        error: (err: any) => {
          console.error('Error loading reviews:', err);
          this.reviews = [];
          this.reviewsLoading = false;
        }
      });
  }

  private loadIssues(): void {
    if (!this.bookingId) return;
    
    this.bookingsService
      .getIssuesByBooking(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (issues: any[]) => {
          this.issues = issues || [];
        },
        error: (err: any) => {
          console.error('Error loading issues:', err);
          this.issues = [];
        }
      });
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

  formatDate(date: string | undefined): string {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }

  formatDateTime(date: string | undefined): string {
    if (!date) return '-';
    return new Date(date).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(price);
  }

  backToList(): void {
    this.router.navigate(['/admin/bookings']);
  }

  printBooking(): void {
    window.print();
  }

  getPaymentStatus(payment: any): string {
    return payment.status || 'Unknown';
  }

  getTotalTax(): number {
    if (!this.booking?.taxes) return 0;
    return this.booking.taxes.reduce((sum: number, tax: any) => sum + tax.tax_amount, 0);
  }

  getStayDuration(): number {
    if (!this.booking?.check_in || !this.booking?.check_out) return 0;
    const checkIn = new Date(this.booking.check_in);
    const checkOut = new Date(this.booking.check_out);
    return Math.ceil((checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60 * 24));
  }
}
