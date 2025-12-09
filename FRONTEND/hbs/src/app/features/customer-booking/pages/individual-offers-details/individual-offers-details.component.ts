import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CustomerNavbarComponent } from '../../../../layout/Customer/customer-navbar/customer-navbar.component';
import { OfferService } from '../../../../services/offer.service';
import { ImageService } from '../../../../shared/services/image.service';
import { ReviewsService, Review } from '../../../../services/reviews.service';
import { WishlistService } from '../../../../services/wishlist.service';
import { BookingStateService } from '../../../../shared/services/booking-state.service';
import { OfferDatePickerModalComponent } from '../../../../shared/components/offer-date-picker-modal/offer-date-picker-modal.component';

interface OfferDetail {
  offer_id: number;
  offer_name: string;
  description: string;
  discount_percent: number;
  valid_from: string;
  valid_to: string;
  primary_image: string | null;
  images: string[];
  room_types: {
    room_type_id: number;
    type_name: string;
    price_per_night: number;
    original_price: number;
    available_count:number;
  }[];
}

@Component({
  selector: 'app-customer-offer-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent, OfferDatePickerModalComponent],
  templateUrl: './individual-offers-details.html',
  styleUrl: './individual-offers-details.css',
})
export class CustomerOfferDetailComponent implements OnInit, OnDestroy {
  offerId: number | null = null;
  offer: OfferDetail | null = null;
  reviews: Review[] = [];
  loading = true;
  error = '';
  previousPage = 'offers';
  
  selectedImageIndex = 0;
  
  // Offer Date Picker Modal Properties
  showOfferDatePickerModal = false;
  
  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    public router: Router,
    private offerService: OfferService,
    private imageService: ImageService,
    private reviewsService: ReviewsService,
    private wishlistService: WishlistService,
    private bookingStateService: BookingStateService
  ) {
    const navigation = this.router.getCurrentNavigation();
    this.previousPage = navigation?.extras?.state?.['from'] || 'offers';
  }

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.offerId = +params['id'];
      this.loadOfferDetails();
      this.loadReviews();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadOfferDetails(): void {
    if (!this.offerId) return;
    
    this.loading = true;
    const offerId = this.offerId;
    
    // Fetch offer details
    this.offerService.getOffer(offerId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (offerData: any) => {
        // Fetch offer images
        this.imageService.getOfferImages(offerId).pipe(takeUntil(this.destroy$)).subscribe({
          next: (images: any[]) => {
            this.offer = {
              offer_id: offerData.offer_id,
              offer_name: offerData.offer_name,
              description: offerData.description || '',
              discount_percent: offerData.discount_percent,
              valid_from: offerData.valid_from,
              valid_to: offerData.valid_to,
              primary_image: images.find((img: any) => img.is_primary)?.image_url || images[0]?.image_url || null,
              images: images.map((img: any) => img.image_url),
              room_types: offerData.room_types || []
            };
            this.loading = false;
          },
          error: () => {
            // Continue without images
            this.offer = {
              offer_id: offerData.offer_id,
              offer_name: offerData.offer_name,
              description: offerData.description || '',
              discount_percent: offerData.discount_percent,
              valid_from: offerData.valid_from,
              valid_to: offerData.valid_to,
              primary_image: null,
              images: [],
              room_types: offerData.room_types || []
            };
            this.loading = false;
          }
        });
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load offer details';
      }
    });
  }

  loadReviews(): void {
    if (!this.offerId) return;

    // For offers, we might want to show reviews for the included room types
    // Or we can create an endpoint that returns reviews for an offer
    // For now, we'll skip this - but the implementation would be similar to rooms
    this.reviews = [];
  }
  selectImage(index: number): void {
    this.selectedImageIndex = index;
  }

  /**
   * Open offer date picker modal to check availability and lock rooms
   */
  claimOffer(): void {
    if (!this.offerId) return;
    this.showOfferDatePickerModal = true;
  }

  /**
   * Handle modal closed event
   */
  onOfferDatePickerClosed(): void {
    this.showOfferDatePickerModal = false;
  }

  /**
   * Handle modal proceed event - navigate to booking page with locked rooms data
   */
  onOfferDatePickerProceed(event: any): void {
    this.showOfferDatePickerModal = false;
    
    if (this.offerId && event) {
      const offerId = this.offerId;
      
      // Navigate to booking page with locked rooms data
      setTimeout(() => {
        this.router.navigate(['/offers/book', offerId], {
          state: {
            lockedRoomsData: {
              offer_id: offerId,
              check_in: event.check_in,
              check_out: event.check_out,
              locked_rooms: event.locked_rooms,
              total_amount: event.total_amount_after_discount,
              expires_at: event.expires_at
            },
            from: 'offer-details'
          }
        });
      }, 50);
    }
  }

  onDatePickerClose(): void {
    this.onOfferDatePickerClosed();
  }
  onDatePickerProceed(data: { checkIn: string; checkOut: string; roomTypeId?: number; offerId?: number }): void {
    // Legacy method - replaced by onOfferDatePickerProceed
  }

  private formatDateForInput(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  goBack(): void {
    console.log(this.previousPage);
    this.router.navigate([this.previousPage]);
  }

  isOfferExpired(): boolean {
    return new Date(this.offer?.valid_to || '') < new Date();
  }

  getRatingStars(rating: number): number[] {
    return Array.from({ length: 5 }, (_, i) => i < rating ? 1 : 0);
  }

  getTimeAgo(date: string): string {
    const now = new Date();
    const reviewDate = new Date(date);
    const diffMs = now.getTime() - reviewDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 30) return `${diffDays} days ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  }

  getSavings(original: number): number {
    return original - Math.round(original * (1 - this.offer!.discount_percent / 100));
  }
}
