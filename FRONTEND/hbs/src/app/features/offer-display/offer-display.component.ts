import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { OfferService } from '../../services/offer.service';
import { WishlistService } from '../../services/wishlist.service';
import { ImageService } from '../../services/image.service';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';
import { CustomerSearchComponent, SearchFilters } from '../customer-search/customer-search.component';

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
}

@Component({
  selector: 'app-offer-display',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent, CustomerSearchComponent],
  templateUrl: './offer-display.component.html',
  styleUrl: './offer-display.component.css',
})
export class OfferDisplayComponent implements OnInit, OnDestroy {
  offers: Offer[] = [];
  filteredOffers: Offer[] = [];
  loading = true;
  error = '';
  
  // Unified search filters
  searchFilters: SearchFilters = {
    searchText: '',
    priceMin: undefined,
    priceMax: undefined,
    discountMin: undefined,
    discountMax: undefined,
    sortBy: 'newest',
  };

  // Deprecated filter properties (kept for compatibility)
  packageTypeFilter: string = 'all';
  priceRangeFilter: string = 'all';
  durationFilter: string = 'all';
  sortByFilter: string = 'newest';

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
    private imageService: ImageService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadOffers();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadOffers(): void {
    this.loading = true;
    this.offerService
      .listOffers(0, 100)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (offersList: any) => {
          // Convert to full offer objects
          this.offers = offersList.map((o: any) => ({
            ...o,
            room_types: o.room_types || [],
          }));
          
          // Load images for each offer
          this.offers.forEach(offer => {
            this.imageService.getPrimaryOfferImageUrl(offer.offer_id)
              .pipe(takeUntil(this.destroy$))
              .subscribe({
                next: (imageUrl: string | null) => {
                  if (imageUrl) {
                    this.offerImages.set(offer.offer_id, imageUrl);
                  }
                },
                error: (err) => {
                  console.warn(`Failed to load image for offer ${offer.offer_id}:`, err);
                  // Set default placeholder if image load fails
                  this.offerImages.set(offer.offer_id, 'assets/images/placeholder-offer.jpg');
                }
              });
          });
          
          this.applyFilters();
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Failed to load offers';
          console.error(err);
          this.loading = false;
        },
      });
  }

  applyFilters(): void {
    let filtered = [...this.offers];

    // Package type filter
    if (this.packageTypeFilter !== 'all') {
      filtered = filtered.filter(
        (o) => o.offer_name.toLowerCase().includes(this.packageTypeFilter.toLowerCase())
      );
    }

    // Price range filter
    if (this.priceRangeFilter !== 'all') {
      filtered = filtered.filter((o) => {
        const basePrice = o.discount_percent;
        switch (this.priceRangeFilter) {
          case 'low':
            return basePrice < 10;
          case 'medium':
            return basePrice >= 10 && basePrice < 20;
          case 'high':
            return basePrice >= 20;
          default:
            return true;
        }
      });
    }

    // Sort
    filtered.sort((a, b) => {
      switch (this.sortByFilter) {
        case 'newest':
          return new Date(b.valid_from).getTime() - new Date(a.valid_from).getTime();
        case 'highest-discount':
          return b.discount_percent - a.discount_percent;
        case 'lowest-discount':
          return a.discount_percent - b.discount_percent;
        default:
          return 0;
      }
    });

    this.filteredOffers = filtered;
  }

  resetFilters(): void {
    this.packageTypeFilter = 'all';
    this.priceRangeFilter = 'all';
    this.durationFilter = 'all';
    this.sortByFilter = 'newest';
    this.searchFilters = {
      searchText: '',
      priceMin: undefined,
      priceMax: undefined,
      discountMin: undefined,
      discountMax: undefined,
      sortBy: 'newest',
    };
    this.applyFilters();
  }

  onSearchFiltersChanged(filters: SearchFilters): void {
    this.searchFilters = filters;
    this.applyUnifiedFilters();
  }

  applyUnifiedFilters(): void {
    let filtered = [...this.offers];

    // Text search - search in offer name and description
    if (this.searchFilters.searchText && this.searchFilters.searchText.trim()) {
      const searchTerm = this.searchFilters.searchText.toLowerCase();
      filtered = filtered.filter(offer =>
        offer.offer_name.toLowerCase().includes(searchTerm) ||
        offer.description.toLowerCase().includes(searchTerm)
      );
    }

    // Discount range filter
    if (this.searchFilters.discountMin !== undefined && this.searchFilters.discountMin !== null) {
      filtered = filtered.filter(offer => offer.discount_percent >= this.searchFilters.discountMin!);
    }

    if (this.searchFilters.discountMax !== undefined && this.searchFilters.discountMax !== null) {
      filtered = filtered.filter(offer => offer.discount_percent <= this.searchFilters.discountMax!);
    }

    // Sort
    if (this.searchFilters.sortBy) {
      filtered.sort((a, b) => {
        switch (this.searchFilters.sortBy) {
          case 'highest-discount':
            return b.discount_percent - a.discount_percent;
          case 'lowest-discount':
            return a.discount_percent - b.discount_percent;
          default:
            return new Date(b.valid_from).getTime() - new Date(a.valid_from).getTime();
        }
      });
    }

    this.filteredOffers = filtered;
  }

  openBookingModal(offer: Offer): void {
    this.selectedOffer = offer;
    this.bookingModalOpen = true;
    this.selectedRooms = [{ room_index: 0, adults: 1, children: 0 }];
  }

  closeBookingModal(): void {
    this.bookingModalOpen = false;
    this.selectedOffer = null;
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
    });
  }

  saveToWishlist(offer: Offer): void {
    this.wishlistService.addOfferToWishlist(offer.offer_id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          alert(`Saved "${offer.offer_name}" to wishlist!`);
        },
        error: (err) => {
          console.error('Error saving to wishlist:', err);
          alert(`Saved "${offer.offer_name}" to wishlist!`);
        }
      });
  }

  viewOfferDetails(offer: Offer): void {
    this.router.navigate([`/admin/offers/view/${offer.offer_id}`]);
  }

  getRoomTypesText(offer: Offer): string {
    if (!offer.room_types || offer.room_types.length === 0) {
      return 'Various rooms';
    }
    return offer.room_types.map((rt: any) => rt.type_name).join(', ');
  }
}
