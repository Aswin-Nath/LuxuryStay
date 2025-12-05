import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';
import { OfferService } from '../../services/offer.service';
import { ImageService } from '../../services/image.service';
import { ReviewsService, Review } from '../../services/reviews.service';
import { WishlistService } from '../../services/wishlist.service';
import { BookingStateService } from '../../services/booking-state.service';
import { DatePickerModalComponent } from '../../shared/components/date-picker-modal/date-picker-modal.component';

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
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent, DatePickerModalComponent],
  templateUrl: './customer-offer-detail.component.html',
  styleUrl: './customer-offer-detail.component.css',
})
export class CustomerOfferDetailComponent implements OnInit, OnDestroy {
  offerId: number | null = null;
  offer: OfferDetail | null = null;
  reviews: Review[] = [];
  loading = true;
  error = '';
  previousPage = 'offers';
  
  selectedImageIndex = 0;
  
  // Date Picker Modal Properties
  showDatePickerModal = false;
  datePickerCheckIn: string = '';
  datePickerCheckOut: string = '';
  datePickerError: string = '';
  
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

  claimOffer(): void {
    if (!this.offerId) return;
    
    this.showDatePickerModal = true;
    
    // Set default dates
    const today = new Date();
    this.datePickerCheckIn = this.formatDateForInput(today);
    
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.datePickerCheckOut = this.formatDateForInput(tomorrow);
    
    this.datePickerError = '';
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
      offerId: this.offerId ?? undefined
    });
    
    // Navigate without query params
    this.router.navigate(['/booking']);
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
