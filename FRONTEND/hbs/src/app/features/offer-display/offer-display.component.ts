import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { OfferService } from '../../services/offer.service';
import { WishlistService } from '../../services/wishlist.service';
import { RoomsService } from '../../core/services/rooms/rooms.service';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';

interface Offer {
  offer_id: number;
  offer_name: string;
  description: string;
  discount_percent: number;
  is_active: boolean;
  valid_from: string;
  valid_to: string;
  max_uses: number | null;
  current_uses: number;
  room_types?: Array<any>;
  image_url?: string;
  is_saved_to_wishlist?: boolean;
  wishlist_id?: number;  // ID to use for removing from wishlist
}

export interface RoomType {
  room_type_id: number;
  type_name: string;
  description?: string;
  price_per_night?: number;
  max_adult_count?: number;
  max_child_count?: number;
}

@Component({
  selector: 'app-offer-display',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent],
  templateUrl: './offer-display.component.html',
  styleUrl: './offer-display.component.css',
})
export class OfferDisplayComponent implements OnInit, OnDestroy {
  @ViewChild(CustomerNavbarComponent) navbarComponent!: CustomerNavbarComponent;
  offers: Offer[] = [];
  filteredOffers: Offer[] = [];
  loading = true;
  loadingRoomTypes = false;
  error = '';
  roomTypes: RoomType[] = [];
  
  // Advanced filter properties
  filterActive: string = 'all';
  minDiscount: number | null = null;
  maxDiscount: number | null = null;
  startDate: string | null = null;
  endDate: string | null = null;
  selectedRoomTypeId: number | null = null;
  sortBy: string = 'date';

  // Booking modal
  bookingModalOpen = false;
  selectedOffer: Offer | null = null;
  selectedRooms: Array<{ room_index: number; adults: number; children: number }> = [];

  // Image loading
  offerImages = new Map<number, string>(); // offer_id -> image_url

  private destroy$ = new Subject<void>();

  constructor(
    private offerService: OfferService,
    private wishlistService: WishlistService,
    private roomsService: RoomsService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadRoomTypes();
    this.loadOffers();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomTypes(): void {
    this.loadingRoomTypes = true;
    this.roomsService.getRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (roomTypes: any[]) => {
          this.roomTypes = roomTypes;
          this.loadingRoomTypes = false;
        },
        error: (err: any) => {
          console.error('Error loading room types:', err);
          this.loadingRoomTypes = false;
        }
      });
  }

  loadOffers(skip: number = 0, limit: number = 100): void {
    this.loading = true;
    
    // Build filter object from advanced filter criteria
    const filters: any = {};
    
    // Active filter
    if (this.filterActive !== 'all') {
      filters.isActive = this.filterActive === 'active';
    }
    
    // Discount range
    if (this.minDiscount !== null && this.minDiscount !== undefined) {
      filters.minDiscount = this.minDiscount;
    }
    if (this.maxDiscount !== null && this.maxDiscount !== undefined) {
      filters.maxDiscount = this.maxDiscount;
    }
    
    // Date range
    if (this.startDate) {
      filters.startDate = this.startDate;
    }
    if (this.endDate) {
      filters.endDate = this.endDate;
    }
    
    // Room type filter
    if (this.selectedRoomTypeId !== null && this.selectedRoomTypeId !== undefined) {
      filters.roomTypeId = this.selectedRoomTypeId;
    }
    
    // Sort
    if (this.sortBy) {
      filters.sortBy = this.sortBy;
    }
    
    // Call backend with filters
    this.offerService
      .listOffersCustomer(skip, limit, filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (offersList: any) => {
          // Convert to full offer objects
          this.offers = offersList.map((o: any) => ({
            ...o,
            room_types: o.room_types || [],
          }));
          
          this.filteredOffers = [...this.offers];
          
          // Load all offer medias in a single optimized call
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
                  } else {
                    // Fallback to placeholder
                    this.offerImages.set(offer.offer_id, 'assets/images/placeholder-offer.jpg');
                  }
                }
              },
              error: (err: any) => {
                console.warn('Failed to load offer medias:', err);
                // Fallback: set placeholders for all offers
                this.offers.forEach(offer => {
                  this.offerImages.set(offer.offer_id, 'assets/images/placeholder-offer.jpg');
                });
              }
            });
          
          this.loading = false;
        },
        error: (err: any) => {
          this.error = 'Failed to load offers';
          console.error(err);
          this.loading = false;
        },
      });
  }

  onFilterChange(): void {
    this.loadOffers();
  }

  resetFilters(): void {
    this.filterActive = 'all';
    this.minDiscount = null;
    this.maxDiscount = null;
    this.startDate = null;
    this.endDate = null;
    this.selectedRoomTypeId = null;
    this.sortBy = 'date';
    this.loadOffers();
  }

  openBookingModal(offer: Offer): void {
    this.navbarComponent?.openBookingModal();
  }

  closeBookingModal(): void {
    this.navbarComponent?.closeBookingModal();
  }

  addRoom(): void {
    this.selectedRooms.push({ room_index: this.selectedRooms.length, adults: 1, children: 0 });
  }

  removeRoom(index: number): void {
    this.selectedRooms.splice(index, 1);
  }

  increaseCounter(roomIndex: number, type: 'adults' | 'children'): void {
    const room = this.selectedRooms[roomIndex];
    if (type === 'adults' && room.adults < 4) room.adults++;
    if (type === 'children' && room.children < 3) room.children++;
  }

  decreaseCounter(roomIndex: number, type: 'adults' | 'children'): void {
    const room = this.selectedRooms[roomIndex];
    if (type === 'adults' && room.adults > 1) room.adults--;
    if (type === 'children' && room.children > 0) room.children--;
  }

  proceedToBooking(): void {
    if (!this.selectedOffer) return;
    // Navigate to booking page with selected offer
    this.router.navigate(['/booking'], {
      queryParams: { offer_id: this.selectedOffer.offer_id },
      state: { from: '/offers' }
    });
  }

  saveToWishlist(offer: Offer): void {
    // OPTIMISTIC UPDATE - save previous state
    const previousState = offer.is_saved_to_wishlist;
    const previousWishlistId = offer.wishlist_id;
    
    // Update UI immediately (optimistic)
    offer.is_saved_to_wishlist = !offer.is_saved_to_wishlist;

    // Call unified toggle endpoint
    this.wishlistService.toggleWishlist('offer', offer.offer_id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res: any) => {
          if (res.action === 'added') {
            offer.wishlist_id = res.wishlist_id;
          } else if (res.action === 'removed') {
            offer.wishlist_id = undefined;
          }
        },
        error: (err: any) => {
          // Revert on error
          offer.is_saved_to_wishlist = previousState;
          offer.wishlist_id = previousWishlistId;
          console.error('Error toggling wishlist:', err);
        }
      });
  }

  viewOfferDetails(offer: Offer): void {
    this.router.navigate(['/offer-details', offer.offer_id], { state: { from: 'offers' } });
  }

  getRoomTypesText(offer: Offer): string {
    if (!offer.room_types || offer.room_types.length === 0) {
      return 'Various rooms';
    }
    return offer.room_types.map((rt: any) => rt.type_name).join(', ');
  }
}
