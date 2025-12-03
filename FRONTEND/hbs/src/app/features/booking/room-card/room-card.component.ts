import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, ChangeDetectorRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BookingService, RoomLock } from '../../../services/booking.service';
import { takeUntil } from 'rxjs/operators';
import { Subject } from 'rxjs';

export interface RoomImage {
  image_id: number;
  image_url: string;
  caption?: string;
  is_primary?: boolean;
  uploaded_by?: number;
}

export interface RoomType {
  room_type_id: number;
  type_name: string;
  description: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  square_ft: number;
  amenities?: string[];
  image_url?: string;
  images?: RoomImage[];
}

@Component({
  selector: 'app-room-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './room-card.component.html',
  styleUrls: ['./room-card.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomCardComponent implements OnInit {
  @Input() roomType: RoomType | null = null;
  @Input() isBookingDisabled: boolean = false;
  @Input() checkIn: string = '';
  @Input() checkOut: string = '';
  @Input() expiryTime: string = '';
  @Input() totalSelectedRooms: number = 0;  // Total rooms already selected

  // Max rooms allowed in one booking
  readonly MAX_ROOMS = 5;

  @Output() roomLocked = new EventEmitter<RoomLock>();
  @Output() bookingError = new EventEmitter<string>();
  @Output() bookingSuccess = new EventEmitter<void>();

  // State
  isBooking = false;
  error: string = '';
  success: string = '';
  showDetailsModal = false;
  showReviewsModal = false;
  
  // Image carousel state
  roomImages: RoomImage[] = [];
  currentImageIndex: number = 0;
  isLoadingImages: boolean = false;
  imagesError: string = '';
  
  // Amenities state
  amenities: { amenity_id: number; amenity_name: string }[] = [];
  isLoadingAmenities: boolean = false;
  amenitiesError: string = '';

  private destroy$ = new Subject<void>();

  constructor(
    private bookingService: BookingService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  ngOnInit() {
    this.cdr.markForCheck();
    // Load room images and amenities when component initializes
    if (this.roomType?.room_type_id) {
      this.loadRoomImages();
      this.loadRoomAmenities();
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // Open Room Details Modal
  openDetailsModal() {
    this.showDetailsModal = true;
    this.cdr.markForCheck();
  }

  closeDetailsModal() {
    this.showDetailsModal = false;
    this.cdr.markForCheck();
  }



  // Open Reviews Modal
  openReviewsModal() {
    this.showReviewsModal = true;
    this.cdr.markForCheck();
  }

  closeReviewsModal() {
    this.showReviewsModal = false;
    this.cdr.markForCheck();
  }

  // Check if max rooms limit reached
  isMaxRoomsReached(): boolean {
    return this.totalSelectedRooms >= this.MAX_ROOMS;
  }

  // Book Now - Lock the room
  bookNow() {
    if (!this.roomType || this.isBooking || this.isMaxRoomsReached()) return;

    this.isBooking = true;
    this.error = '';
    this.success = '';
    this.cdr.markForCheck();

    this.bookingService.lockRoom(
      this.roomType.room_type_id,
      this.checkIn,
      this.checkOut,
      this.expiryTime
    ).pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (lock: RoomLock) => {
          this.success = `✅ Room locked successfully!`;
          this.roomLocked.emit(lock);
          this.bookingSuccess.emit();
          
          setTimeout(() => {
            this.isBooking = false;
            this.cdr.markForCheck();
          }, 1000);
        },
        error: (err: any) => {
          let errorMsg = 'Failed to lock room. Please try again.';
          const status = err?.status;
          const detail = err?.error?.detail || '';
          
          // 404: Room type or rooms don't exist
          if (status === 404) {
            if (detail.includes('room type')) {
              errorMsg = `❌ This room type is no longer available.`;
            } else {
              errorMsg = `❌ ${this.roomType?.type_name} rooms not found.`;
            }
          }
          // 409: Conflict - No availability for selected dates
          else if (status === 409) {
            errorMsg = `❌ No ${this.roomType?.type_name} rooms available for your selected dates. Please try different dates.`;
          }
          // 423: Locked - Room lock conflict
          else if (status === 423) {
            errorMsg = `❌ Room is temporarily locked by another user. Please try again in a moment.`;
          }
          // 400: Bad request
          else if (status === 400) {
            errorMsg = `❌ ${detail || 'Invalid request. Please check your dates.'}`;
          }
          // Fallback to detail message
          else if (detail) {
            errorMsg = `❌ ${detail}`;
          }
          // Network or unknown error
          else if (err?.message) {
            errorMsg = `❌ Error: ${err.message}`;
          }
          
          this.error = errorMsg;
          this.bookingError.emit(errorMsg);
          this.isBooking = false;
          this.cdr.markForCheck();
        }
      });
  }

  /**
   * Load amenities for this room type from backend
   */
  loadRoomAmenities(): void {
    if (!this.roomType?.room_type_id) return;
    
    this.isLoadingAmenities = true;
    this.amenitiesError = '';
    this.cdr.markForCheck();
    
    const apiUrl = `${this.bookingService.getImageApiUrl().replace('/types', '')}/types/${this.roomType.room_type_id}/amenities`;
    
    this.http.get<{ room_type_id: number; amenities: { amenity_id: number; amenity_name: string }[] }>(apiUrl)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: any) => {
          this.amenities = response.amenities && response.amenities.length > 0 ? response.amenities : [];
          this.isLoadingAmenities = false;
          this.cdr.markForCheck();
          console.log(`✅ Loaded ${this.amenities.length} amenities for ${this.roomType?.type_name}`);
        },
        error: (err: any) => {
          console.error(`❌ Failed to load amenities:`, err);
          this.amenitiesError = 'Failed to load amenities';
          this.isLoadingAmenities = false;
          this.amenities = [];
          this.cdr.markForCheck();
        }
      });
  }
  
  /**
   * Get display amenities (from API or empty array)
   */
  getDisplayAmenities(): { amenity_id: number; amenity_name: string }[] {
    return this.amenities.length > 0 ? this.amenities : [];
  }
  
  /**
   * Get amenities preview string for card header
   */
  getAmenitiesPreview(): string {
    if (this.amenities.length === 0) {
      return 'amenities';
    }
    const names = this.amenities.slice(0, 2).map(a => a.amenity_name);
    return names.join(' & ');
  }
  
  /**
   * Get full amenities list as tooltip
   */
  getAmenitiesToolTip(): string {
    return this.amenities.map(a => a.amenity_name).join(', ');
  }

  // Get sample reviews
  getSampleReviews() {
    return [
      { name: 'John D.', rating: 4, comment: 'Great room with excellent comfort. Wi-Fi speed could be better.' },
      { name: 'Priya S.', rating: 5, comment: 'Loved the hospitality! Room service was quick and professional.' },
      { name: 'Michael B.', rating: 4, comment: 'Spacious and clean. Breakfast was tasty but could add more variety.' },
      { name: 'Anita R.', rating: 5, comment: 'Amazing stay! Definitely coming back again.' }
    ];
  }

  getAverageRating(): number {
    const reviews = this.getSampleReviews();
    const sum = reviews.reduce((acc, r) => acc + r.rating, 0);
    return Math.round((sum / reviews.length) * 10) / 10;
  }

  getRatingPercentage(stars: number): number {
    const reviews = this.getSampleReviews();
    const count = reviews.filter(r => r.rating === stars).length;
    return Math.round((count / reviews.length) * 100);
  }

  // Get rounded rating for display
  getRoundedRating(): number {
    return Math.round(this.getAverageRating());
  }

  // ===================================================
  // IMAGE CAROUSEL METHODS
  // ===================================================
  
  /**
   * Load room images from backend API
   */
  loadRoomImages(): void {
    if (!this.roomType?.room_type_id) return;
    
    this.isLoadingImages = true;
    this.imagesError = '';
    this.cdr.markForCheck();
    
    // Get image API URL from service and construct endpoint
    const imageApiUrl = this.bookingService.getImageApiUrl();
    const apiUrl = `${imageApiUrl}/types/${this.roomType.room_type_id}/images`;
    
    this.http.get<RoomImage[]>(apiUrl)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (images: RoomImage[]) => {
          this.roomImages = images && images.length > 0 ? images : [];
          this.currentImageIndex = 0;
          this.isLoadingImages = false;
          this.cdr.markForCheck();
          console.log(`✅ Loaded ${this.roomImages.length} images for ${this.roomType?.type_name}`);
        },
        error: (err: any) => {
          console.error(`❌ Failed to load images:`, err);
          this.imagesError = 'Failed to load room images';
          this.isLoadingImages = false;
          this.roomImages = [];
          this.cdr.markForCheck();
        }
      });
  }

  /**
   * Get current image URL
   */
  getCurrentImage(): RoomImage | null {
    if (this.roomImages.length === 0) return null;
    return this.roomImages[this.currentImageIndex] || null;
  }

  /**
   * Get image URL to display (from carousel or fallback)
   */
  getDisplayImageUrl(): string {
    const currentImage = this.getCurrentImage();
    if (currentImage?.image_url) {
      return currentImage.image_url;
    }
    // Fallback to roomType image_url or default
    return this.roomType?.image_url || '/assets/images/room1.jpg';
  }

  /**
   * Navigate to next image
   */
  nextImage(): void {
    if (this.roomImages.length === 0) return;
    this.currentImageIndex = (this.currentImageIndex + 1) % this.roomImages.length;
    this.cdr.markForCheck();
  }

  /**
   * Navigate to previous image
   */
  prevImage(): void {
    if (this.roomImages.length === 0) return;
    this.currentImageIndex = (this.currentImageIndex - 1 + this.roomImages.length) % this.roomImages.length;
    this.cdr.markForCheck();
  }

  /**
   * Go to specific image by index
   */
  goToImage(index: number): void {
    if (index >= 0 && index < this.roomImages.length) {
      this.currentImageIndex = index;
      this.cdr.markForCheck();
    }
  }

  /**
   * Check if carousel should be shown
   */
  hasMultipleImages(): boolean {
    return this.roomImages.length > 1;
  }

  /**
   * Get image position display (e.g., "1 / 5")
   */
  getImagePosition(): string {
    if (this.roomImages.length === 0) return '';
    return `${this.currentImageIndex + 1} / ${this.roomImages.length}`;
  }
}
