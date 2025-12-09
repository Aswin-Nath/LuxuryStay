import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { CustomerNavbarComponent } from '../../../../layout/Customer/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../../../layout/Customer/customer-sidebar/customer-sidebar.component';
import { BookingsService } from '../../../../services/bookings.service';
import { OfferService } from '../../../../services/offer.service';
import { ProfileService } from '../../../../services/profile.service';
import { WishlistService } from '../../../../services/wishlist.service';
import { takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';
import { BookingStateService } from '../../../../shared/services/booking-state.service';
import { DatePickerModalComponent } from '../../../../shared/components/date-picker-modal/date-picker-modal.component';
interface Booking {
  booking_id: string;
  room_type_name?: string;
  room_numbers?: string;
  check_in: string;
  check_out: string;
  guest_count?: string;
  number_of_rooms?: number;
}

interface Offer {
  offer_id: number;
  offer_name: string;
  description: string;
  discount_percent: number;
  valid_to: string;
  imageUrl?: string;
  isSaved?: boolean;
  wishlist_id?: number;
  is_saved_to_wishlist?: boolean;
}

@Component({
  selector: 'app-customer-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, CustomerNavbarComponent, CustomerSidebarComponent,DatePickerModalComponent],
  templateUrl: './customer-dashboard.component.html',
  styleUrls: ['./customer-dashboard.component.css']
})
export class CustomerDashboardComponent implements OnInit {
  // Stats
  bookingsCount = 0;
  offersCount = 0;
  rewardPoints = 0;

  // Date picker modal properties
  showDatePickerModal: boolean = false;
  checkIn: string = '';
  checkOut: string = '';
  datePickerError: string = '';
  // Date Picker Modal Properties
  datePickerCheckIn: string = '';
  datePickerCheckOut: string = '';
  // Upcoming Bookings
  upcomingBookings: Booking[] = [];

  // Offers
  offers: Offer[] = [];
  
  // Offer images map
  offerImages = new Map<number, string>();

  // Toast
  showToast = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' = 'success';

  currentPage = 'dashboard';
  isLoading = true;
  private destroy$ = new Subject<void>();

  constructor(
    private router: Router,
    private bookingsService: BookingsService,
    private offerService: OfferService,
    private profileService: ProfileService,
    private wishlistService: WishlistService,
        private bookingStateService: BookingStateService

  ) { }

  ngOnInit(): void {
    this.loadDashboardData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
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
      checkOut: data.checkOut,
    });
    
    // Navigate without query params
    this.router.navigate(['/booking']);
  }

  loadDashboardData(): void {
    this.isLoading = true;
    
    // Load user profile for loyalty points
    this.profileService.getProfile()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (profile: any) => {
          this.rewardPoints = profile.loyalty_points || 0;
        },
        error: (err: any) => {
          console.error('Error loading profile:', err);
        }
      });

    // Load recent bookings
    this.bookingsService.getCustomerBookings()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (bookings: any[]) => {
          // Filter upcoming bookings (check_out date is in future)
          const now = new Date();
          this.upcomingBookings = bookings
            .filter(b => new Date(b.check_out) > now)
            .slice(0, 3);  // Show only 3 most recent
          
          this.bookingsCount = bookings.length;
        },
        error: (err: any) => {
          console.error('Error loading bookings:', err);
          this.upcomingBookings = [];
        }
      });

    // Load active offers with image medias
    this.offerService.listOffersCustomer(0, 6, { isActive: true })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (offers: any[]) => {
          // Filter offers that have not passed their valid_to date
          const now = new Date();
          this.offers = offers
            .filter(o => new Date(o.valid_to) >= now)
            .map(o => ({
              offer_id: o.offer_id,
              offer_name: o.offer_name,
              description: o.description || 'Special offer',
              discount_percent: o.discount_percent,
              valid_to: o.valid_to,
              isSaved: o.is_saved_to_wishlist || false,
              is_saved_to_wishlist: o.is_saved_to_wishlist || false,
              wishlist_id: o.wishlist_id
            }));
          this.offersCount = this.offers.length;
          
          // Load offer medias to get images
          this.offerService.getOfferMedias()
            .pipe(takeUntil(this.destroy$))
            .subscribe({
              next: (medias: any) => {
                // Process medias: extract primary image for each offer
                for (const offer of this.offers) {
                  const offerMedias = medias[offer.offer_id];
                  if (offerMedias && offerMedias.images && offerMedias.images.length > 0) {
                    // Find primary image or use first one
                    const primaryImage = offerMedias.images.find((img: any) => img.is_primary);
                    const imageUrl = (primaryImage || offerMedias.images[0]).image_url;
                    this.offerImages.set(offer.offer_id, imageUrl);
                    offer.imageUrl = imageUrl;
                  } else {
                    // Fallback to placeholder
                    this.offerImages.set(offer.offer_id, 'assets/images/placeholder-offer.jpg');
                    offer.imageUrl = 'assets/images/placeholder-offer.jpg';
                  }
                }
              },
              error: (err: any) => {
                console.warn('Failed to load offer medias:', err);
                // Fallback: set placeholders for all offers
                this.offers.forEach(offer => {
                  this.offerImages.set(offer.offer_id, 'assets/images/placeholder-offer.jpg');
                  offer.imageUrl = 'assets/images/placeholder-offer.jpg';
                });
              }
            });
        },
        error: (err: any) => {
          console.error('Error loading offers:', err);
          this.offers = [];
        }
      });

    this.isLoading = false;
  }

  toggleSaveOffer(offer: Offer): void {
    // OPTIMISTIC UPDATE - save previous state
    const previousState = offer.is_saved_to_wishlist;
    const previousWishlistId = offer.wishlist_id;
    
    // Update UI immediately (optimistic)
    offer.is_saved_to_wishlist = !offer.is_saved_to_wishlist;
    offer.isSaved = offer.is_saved_to_wishlist;

    // Call unified toggle endpoint
    this.wishlistService.toggleWishlist('offer', offer.offer_id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res: any) => {
          if (res.action === 'added') {
            offer.wishlist_id = res.wishlist_id;
            this.displayToast('Offer saved to your wishlist!', 'success');
          } else if (res.action === 'removed') {
            offer.wishlist_id = undefined;
            this.displayToast('Offer removed from wishlist', 'info');
          }
        },
        error: (err: any) => {
          // Revert on error
          offer.is_saved_to_wishlist = previousState;
          offer.isSaved = previousState;
          offer.wishlist_id = previousWishlistId;
          this.displayToast('Error updating wishlist', 'error');
          console.error('Error toggling wishlist:', err);
        }
      });
  }

  displayToast(message: string, type: 'success' | 'error' | 'info'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.showToast = true;

    setTimeout(() => {
      this.showToast = false;
    }, 3000);
  }

  getToastIcon(): string {
    switch (this.toastType) {
      case 'success': return 'check_circle';
      case 'error': return 'error';
      case 'info': return 'info';
      default: return 'check_circle';
    }
  }

  getToastClass(): string {
    switch (this.toastType) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'info': return 'bg-blue-500';
      default: return 'bg-green-500';
    }
  }

  getDiscountBadgeClass(type: string): string {
    return type === 'percent' ? 'bg-green-100 text-green-800' : 'bg-pink-100 text-pink-800';
  }

  /**
   * Navigate to booking detail page
   */
  viewBookingDetails(booking: Booking): void {
    console.log(booking);
    this.router.navigate(['/booking', booking.booking_id],{state:{from:"dashboard"}});
  }

  /**
   * Navigate to offer detail page
   */
  viewOfferDetails(offer: Offer): void {
    this.router.navigate(['/offer-details', offer.offer_id], { state: { from: 'dashboard' } });
  }
  
  /**
   * Book now - show date picker modal
   */
  bookNow(): void {
    this.showDatePickerModal = true;
    // Set today as check-in date
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


  /**
   * Close date picker modal
   */
  closeBookingModal(): void {
    this.showDatePickerModal = false;
    this.checkIn = '';
    this.checkOut = '';
    this.datePickerError = '';
  }

  /**
   * Calculate number of nights
   */
  calculateNumberOfNights(): number {
    if (!this.checkIn || !this.checkOut) return 0;
    const checkInDate = new Date(this.checkIn);
    const checkOutDate = new Date(this.checkOut);
    const diffTime = checkOutDate.getTime() - checkInDate.getTime();
    const diffDays = diffTime / (1000 * 60 * 60 * 24);
    return Math.max(0, Math.ceil(diffDays));
  }

  /**
   * Proceed with booking
   */
  proceedWithBooking(): void {
    // Validate dates
    if (!this.checkIn || !this.checkOut) {
      this.datePickerError = 'Please select both check-in and check-out dates';
      return;
    }

    const checkInDate = new Date(this.checkIn);
    const checkOutDate = new Date(this.checkOut);

    if (checkOutDate <= checkInDate) {
      this.datePickerError = 'Check-out date must be after check-in date';
      return;
    }
    console.log(this.checkIn,this.checkOut);
    // Navigate to rooms page with dates as query params
    this.showDatePickerModal=false;
    this.router.navigate(['/booking'], {
      queryParams: {
        checkIn: this.checkIn,
        checkOut: this.checkOut
      },state: { from: this.router.url }
    });
    this.closeBookingModal();

  }
  
}
