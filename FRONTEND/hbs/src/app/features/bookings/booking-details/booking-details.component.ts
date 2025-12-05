import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { BookingsService, BookingResponse } from '../../../services/bookings.service';
import { ReviewsService, Review } from '../../../services/reviews.service';
import { CustomerNavbarComponent } from '../../../core/components/customer-navbar/customer-navbar.component';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-booking-details',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, CustomerNavbarComponent],
  templateUrl: './booking-details.component.html',
  styleUrls: ['./booking-details.component.css']
})
export class BookingDetailsComponent implements OnInit, OnDestroy {
  booking: BookingResponse | null = null;
  roomTypes: Map<number, any> = new Map();
  isLoading = false;
  error: string = '';
  bookingId: number = 0;

  // Review properties
  selectedRating: number = 0;
  reviewText: string = '';
  ratingTexts: { [key: number]: string } = {
    1: 'Poor - Not satisfied',
    2: 'Fair - Below expectations',
    3: 'Good - Satisfactory',
    4: 'Very Good - Exceeded expectations',
    5: 'Excellent - Outstanding experience'
  };
  reviews: Review[] = [];
  existingReview: Review | null = null;
  isSubmittingReview: boolean = false;
  reviewsLoading: boolean = false;
  selectedReviewImages: File[] = [];
  reviewImagePreviews: string[] = [];

  // Issue properties
  issueTitle: string = '';
  issueDescription: string = '';
  selectedImages: any[] = [];
  previousPage="bookings";
  // Cancel properties
  cancellationReason: string = '';

  private destroy$ = new Subject<void>();

  constructor(
    private bookingsService: BookingsService,
    private reviewsService: ReviewsService,
    private route: ActivatedRoute,
    private router: Router
  ) {
    const navigation = this.router.getCurrentNavigation();
    this.previousPage = navigation?.extras?.state?.['from'] || 'offers';

  }

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
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
      .getBookingDetails(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: BookingResponse) => {
          this.booking = data;
          // Populate room prices from cached roomTypes Map
          if (this.booking.rooms) {
            this.booking.rooms.forEach((room) => {
              const roomTypePrice = this.getRoomTypePrice(room.room_type_id);
              if (roomTypePrice !== null) {
                room.price_per_night = roomTypePrice;
              }
            });
          }
          this.loadPayments();
          this.loadReviews();
          this.isLoading = false;
        },
        error: (err: any) => {
          console.error('Error loading booking details:', err);
          this.error = 'Failed to load booking details. Please try again.';
          this.isLoading = false;
        }
      });
  }

  private loadReviews(): void {
    if (!this.booking) return;

    this.reviewsLoading = true;
    this.reviewsService
      .getReviewsByBooking(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (reviews: Review[]) => {
          this.reviews = reviews;
          if (reviews.length > 0) {
            this.existingReview = reviews[0]; // Show the first review (only one per booking)
          }
          this.reviewsLoading = false;
          console.log("Reviews",this.reviews);
        },
        error: (err: any) => {
          console.error('Error loading reviews:', err);
          this.reviews = [];
          this.reviewsLoading = false;
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

  private loadIssues(): void {
    if (!this.booking) return;

    this.bookingsService
      .getIssuesByBooking(this.bookingId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (issues: any[]) => {
          if (this.booking) {
            this.booking.issues = issues;
          }
        },
        error: (err: any) => {
          console.error('Error loading issues:', err);
          if (this.booking) {
            this.booking.issues = [];
          }
        }
      });
  }

  getRoomTypeName(roomTypeId: number): string | null {
    const roomType = this.roomTypes.get(roomTypeId);
    return roomType ? roomType.type_name : null;
  }

  getRoomTypePrice(roomTypeId: number): number | null {
    const roomType = this.roomTypes.get(roomTypeId);
    return roomType ? roomType.price_per_night : null;
  }

  goBack(): void {
    if(this.previousPage=="dashboard"){
      this.router.navigate(["/dashboard"]);
    }
    else{
    this.router.navigate(['/bookings']);
  }}

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

  calculateNights(): number {
    if (!this.booking) return 0;
    const checkIn = new Date(this.booking.check_in).getTime();
    const checkOut = new Date(this.booking.check_out).getTime();
    return Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
  }

  getTotalRoomPrice(): number {
    if (!this.booking || !this.booking.rooms) return 0;
    const nights = this.calculateNights();
    return this.booking.rooms.reduce((sum, room) => sum + ((this.getRoomTypePrice(room.room_type_id) || 0) * nights), 0);
  }

  calculateGST(): number {
    const subtotal = this.getTotalRoomPrice();
    return Math.round(subtotal * 0.18 * 100) / 100;
  }

  getTotalAmount(): number {
    const subtotal = this.getTotalRoomPrice();
    const gst = this.calculateGST();
    return Math.round((subtotal + gst) * 100) / 100;
  }

  isBookingStaying(): boolean {
    return this.booking?.status.toLowerCase() === 'checked-in';
  }

  isBookingCheckedOut(): boolean {
    return this.booking?.status.toLowerCase() === 'checked-out';
  }

  canShowReview(): boolean {
    return this.isBookingStaying() || this.isBookingCheckedOut();
  }

  canShowIssueForm(): boolean {
    return this.isBookingStaying();
  }

  canShowCancelButton(): boolean {
    if (!this.booking) return false;
    const status = this.booking.status.toLowerCase();
    return status !== 'cancelled' && status !== 'checked-out';
  }

  getRoomNumbers(): string {
    if (!this.booking || !this.booking.rooms || this.booking.rooms.length === 0) {
      return 'N/A';
    }
    return this.booking.rooms.map(r => r.room_id).join(', ');
  }

  getPaymentMethodName(methodId: number): string {
    const paymentMethods: { [key: number]: string } = {
      1: 'Credit Card',
      2: 'Debit Card',
      3: 'Net Banking',
      4: 'UPI',
      5: 'Wallet',
      6: 'Cash',
      7: 'Check'
    };
    return paymentMethods[methodId] || `Method ID: ${methodId}`;
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
    const baseAmount = this.getTotalRoomPrice();

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

  // ✅ Review Methods
  setRating(rating: number): void {
    this.selectedRating = rating;
  }

  onReviewImageSelect(event: any): void {
    const files = Array.from(event.target.files) as File[];
    files.forEach((file: File) => {
      // Check file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        this.showToast(`File ${file.name} is too large. Max 5MB allowed.`, 'error');
        return;
      }

      this.selectedReviewImages.push(file);

      // Generate preview
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.reviewImagePreviews.push(e.target.result);
      };
      reader.readAsDataURL(file);
    });
  }

  removeReviewImage(index: number): void {
    this.selectedReviewImages.splice(index, 1);
    this.reviewImagePreviews.splice(index, 1);
  }

  submitReview(): void {
    if (this.selectedRating === 0 || !this.reviewText || this.reviewText.trim().length === 0) {
      this.showToast('Please provide a rating and review text', 'error');
      return;
    }

    if (this.existingReview) {
      this.showToast('You can only submit one review per booking', 'error');
      return;
    }

    this.isSubmittingReview = true;

    // Get the first room type from the booking to associate with the review
    const roomTypeId = this.booking?.rooms?.[0]?.room_type_id || 0;

    const reviewPayload = {
      booking_id: this.bookingId,
      rating: this.selectedRating,
      comment: this.reviewText,
      room_type_id: roomTypeId
    };

    this.reviewsService
      .createReview(reviewPayload)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (review: Review) => {
          // Upload images if any
          if (this.selectedReviewImages.length > 0) {
            this.reviewsService
              .uploadReviewImages(review.review_id, this.selectedReviewImages)
              .pipe(takeUntil(this.destroy$))
              .subscribe({
                next: () => {
                  this.showToast('Review submitted successfully with images!', 'success');
                  this.resetReview();
                  this.loadReviews();
                  this.isSubmittingReview = false;
                },
                error: (err) => {
                  console.error('Error uploading images:', err);
                  this.showToast('Review submitted but image upload failed', 'error');
                  this.isSubmittingReview = false;
                  this.loadReviews();
                }
              });
          } else {
            this.showToast('Review submitted successfully!', 'success');
            this.resetReview();
            this.loadReviews();
            this.isSubmittingReview = false;
          }
        },
        error: (err) => {
          console.error('Error submitting review:', err);
          this.showToast('Failed to submit review. Please try again.', 'error');
          this.isSubmittingReview = false;
        }
      });
  }

  resetReview(): void {
    this.selectedRating = 0;
    this.reviewText = '';
    this.selectedReviewImages = [];
    this.reviewImagePreviews = [];
  }

  // ✅ Issue Modal Methods
  openRaiseIssueModal(): void {
    const modal = document.getElementById('raiseIssueModal');
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
      document.body.style.overflow = 'hidden';
    }
  }

  closeRaiseIssueModal(): void {
    const modal = document.getElementById('raiseIssueModal');
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      document.body.style.overflow = '';
    }
    this.resetIssueForm();
  }

  resetIssueForm(): void {
    this.issueTitle = '';
    this.issueDescription = '';
    this.selectedImages = [];
  }

  onImageSelect(event: any): void {
    const files = Array.from(event.target.files) as File[];
    files.forEach((file: File) => {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.selectedImages.push({
          name: file.name,
          preview: e.target.result
        });
      };
      reader.readAsDataURL(file);
    });
  }

  removeImage(index: number): void {
    this.selectedImages.splice(index, 1);
  }

  submitIssue(): void {
    if (!this.issueTitle || !this.issueDescription) {
      this.showToast('Please fill in all required fields', 'error');
      return;
    }

    console.log('Issue submitted:', {
      title: this.issueTitle,
      description: this.issueDescription,
      images: this.selectedImages,
      bookingId: this.booking?.booking_id
    });

    this.closeRaiseIssueModal();
    this.showToast('Issue reported successfully! We will contact you soon.', 'success');
  }

  // ✅ Cancel Booking Methods
  openCancelBookingModal(): void {
    const policyModal = document.getElementById('cancelPolicyModal');
    if (policyModal) {
      policyModal.classList.remove('hidden');
      policyModal.classList.add('flex');
      document.body.style.overflow = 'hidden';
    }
  }

  closeCancelPolicyModal(): void {
    const policyModal = document.getElementById('cancelPolicyModal');
    if (policyModal) {
      policyModal.classList.add('hidden');
      policyModal.classList.remove('flex');
      document.body.style.overflow = '';
    }
  }

  proceedToCancel(): void {
    this.closeCancelPolicyModal();
    setTimeout(() => {
      const cancelModal = document.getElementById('unifiedCancelModal');
      if (cancelModal) {
        cancelModal.classList.remove('hidden');
        cancelModal.classList.add('flex');
        document.body.style.overflow = 'hidden';
        this.cancellationReason = '';
      }
    }, 100);
  }

  closeUnifiedCancelModal(): void {
    const cancelModal = document.getElementById('unifiedCancelModal');
    if (cancelModal) {
      cancelModal.classList.add('hidden');
      cancelModal.classList.remove('flex');
      document.body.style.overflow = '';
    }
    this.cancellationReason = '';
  }

  confirmCancel(): void {
    if (!this.booking) {
      this.showToast('Error: Booking not found', 'error');
      return;
    }

    // Check if booking is checked-in and show no-refund warning
    if (this.isBookingStaying()) {
      const confirmed = confirm(
        'IMPORTANT: Cancelling after check-in means NO REFUND will be issued. You will be charged for the entire stay.\n\nDo you want to proceed with the cancellation?'
      );
      if (!confirmed) {
        return;
      }
    }

    this.closeUnifiedCancelModal();
    
    // Call the cancel booking API
    this.bookingsService
      .cancelBooking(this.booking.booking_id, this.cancellationReason || '')
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: any) => {
          this.showToast('Booking cancelled successfully. Rooms have been unlocked.', 'success');
          // Update booking status locally
          if (this.booking) {
            this.booking.status = 'cancelled';
          }
          // Optionally redirect after 2 seconds
          setTimeout(() => {
            this.goBack();
          }, 2000);
        },
        error: (err: any) => {
          console.error('Error cancelling booking:', err);
          this.showToast('Failed to cancel booking. Please try again.', 'error');
        }
      });
  }

  // ✅ Toast Notification
  showToast(message: string, type: 'success' | 'error' = 'success'): void {
    const toastContainer = document.getElementById('unifiedToast');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    const bgColor = type === 'error' ? 'bg-red-600' : 'bg-green-600';
    toast.className = `${bgColor} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3`;
    toast.style.minWidth = '250px';
    toast.innerHTML = `
      <div class="flex-1 text-sm">${message}</div>
      <button class="opacity-80 hover:opacity-100">✕</button>
    `;

    toast.querySelector('button')?.addEventListener('click', () => toast.remove());
    toastContainer.appendChild(toast);

    setTimeout(() => {
      try {
        toast.remove();
      } catch (e) {
        // Element already removed
      }
    }, 4000);
  }
}
