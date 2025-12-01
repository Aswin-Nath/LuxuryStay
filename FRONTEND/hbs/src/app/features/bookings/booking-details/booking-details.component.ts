import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { BookingsService, BookingResponse } from '../../../services/bookings.service';
import { CustomerNavbarComponent } from '../../../core/components/customer-navbar/customer-navbar.component';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-booking-details',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent],
  templateUrl: './booking-details.component.html',
  styleUrls: ['./booking-details.component.css']
})
export class BookingDetailsComponent implements OnInit, OnDestroy {
  booking: BookingResponse | null = null;
  isLoading = false;
  error: string = '';
  bookingId: number = 0;

  private destroy$ = new Subject<void>();

  constructor(
    private bookingsService: BookingsService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      // Handle both /bookings/details/:id and /booking/:booking_id routes
      this.bookingId = params['id'] || params['booking_id'];
      if (this.bookingId) {
        this.loadBookingDetails();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadBookingDetails(): void {
    this.isLoading = true;
    this.error = '';

    this.bookingsService
      .getBookingDetails(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: BookingResponse) => {
          this.booking = data;
          this.isLoading = false;
        },
        error: (err: any) => {
          console.error('Error loading booking details:', err);
          this.error = 'Failed to load booking details. Please try again.';
          this.isLoading = false;
        }
      });
  }

  goBack(): void {
    this.router.navigate(['/bookings']);
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

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  formatBookingDateTime(dateTimeString: string): string {
    if (!dateTimeString) return 'N/A';
    const date = new Date(dateTimeString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }) + ' at ' + date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatDateTime(dateString: string, timeString: string): string {
    const date = new Date(dateString);
    const formatted = date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
    return `${formatted} at ${timeString}`;
  }

  calculateNights(): number {
    if (!this.booking) return 0;
    const checkIn = new Date(this.booking.check_in).getTime();
    const checkOut = new Date(this.booking.check_out).getTime();
    return Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
  }

  getSubtotal(): number {
    if (!this.booking) return 0;
    const taxes = this.booking.taxes?.reduce((sum: number, tax) => sum + tax.tax_amount, 0) || 0;
    return this.booking.total_price - taxes;
  }

  downloadInvoice(): void {
    if (!this.booking) return;

    const invoiceHTML = this.generateInvoiceHTML();
    const blob = new Blob([invoiceHTML], { type: 'text/html' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Booking-${this.booking.booking_id}-Invoice.html`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  private generateInvoiceHTML(): string {
    if (!this.booking) return '';

    const nights = this.calculateNights();
    const baseAmount = this.booking.total_price - (this.booking.taxes?.reduce((sum: number, tax) => sum + tax.tax_amount, 0) || 0);

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Invoice - ${this.booking.booking_id}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
          .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #f59e0b; padding-bottom: 20px; }
          .hotel-name { font-size: 24px; font-weight: bold; color: #f59e0b; margin-bottom: 5px; }
          .invoice-title { font-size: 18px; color: #666; }
          .section { margin: 20px 0; }
          .section-title { font-size: 16px; font-weight: bold; color: #f59e0b; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
          .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
          .info-box { padding: 15px; background: #f9f9f9; border-left: 3px solid #f59e0b; }
          table { width: 100%; border-collapse: collapse; margin: 10px 0; }
          th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
          th { background: #f59e0b; color: white; font-weight: bold; }
          .total-row { background: #fff3cd; font-weight: bold; }
          .footer { margin-top: 30px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }
          @media print { body { margin: 0; } }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="hotel-name">🏨 LuxuryStay Hotel</div>
          <div class="invoice-title">BOOKING INVOICE</div>
        </div>

        <div class="info-grid">
          <div class="info-box">
            <div class="section-title">Booking Details</div>
            <p><strong>Booking ID:</strong> ${this.booking.booking_id}</p>
            <p><strong>Check-in:</strong> ${this.formatDate(this.booking.check_in)} at ${this.booking.check_in_time}</p>
            <p><strong>Check-out:</strong> ${this.formatDate(this.booking.check_out)} at ${this.booking.check_out_time}</p>
            <p><strong>Duration:</strong> ${nights} night(s)</p>
            <p><strong>Rooms:</strong> ${this.booking.room_count}</p>
          </div>
          
          <div class="info-box">
            <div class="section-title">Guest Information</div>
            <p><strong>Name:</strong> ${this.booking.primary_customer_name || 'N/A'}</p>
            <p><strong>Phone:</strong> ${this.booking.primary_customer_phone_number || 'N/A'}</p>
            <p><strong>DOB:</strong> ${this.booking.primary_customer_dob || 'N/A'}</p>
            <p><strong>Status:</strong> ${this.booking.status.toUpperCase()}</p>
          </div>
        </div>

        <div class="section">
          <div class="section-title">Room Charges</div>
          <table>
            <thead>
              <tr>
                <th>Room Type</th>
                <th>Rate/Night</th>
                <th>Nights</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Room(s)</td>
                <td>₹${(baseAmount / nights).toLocaleString()}</td>
                <td>${nights}</td>
                <td>₹${baseAmount.toLocaleString()}</td>
              </tr>
              ${this.booking.taxes ? this.booking.taxes.map((tax: any) => `
                <tr>
                  <td colspan="3">Tax #${tax.tax_id}</td>
                  <td>₹${tax.tax_amount.toLocaleString()}</td>
                </tr>
              `).join('') : ''}
              <tr class="total-row">
                <td colspan="3"><strong>Total Amount</strong></td>
                <td><strong>₹${this.booking.total_price.toLocaleString()}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="footer">
          <p>Thank you for choosing LuxuryStay Hotel!</p>
          <p>Generated on: ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}</p>
          <p>For any queries, contact us at: info@luxurystay.com | +91 99999 88888</p>
        </div>
      </body>
      </html>
    `;
  }
}
