import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { WishlistService } from '../../wishlist.service';
import { CustomerNavbarComponent } from '../../../../layout/Customer/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../../../layout/Customer/customer-sidebar/customer-sidebar.component';

interface WishlistRoom {
  wishlist_id: number;
  room_type_id: number;
  type_name: string;
  price_per_night: number;
  description: string;
  square_ft: number;
  max_adult_count: number;
  max_child_count: number;
  amenities: string[];
  added_at: string;
  primary_image: string | null;
}

interface WishlistOffer {
  wishlist_id: number;
  offer_id: number;
  offer_name: string;
  description: string;
  discount_percent: number;
  valid_from: string;
  valid_to: string;
  room_types: any[];
  added_at: string;
  primary_image: string | null;
}

@Component({
  selector: 'app-wishlist',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent, CustomerSidebarComponent],
  templateUrl: './wishlist-display.html',
  styleUrl: './wishlist-display.css',
})
export class WishlistComponent implements OnInit, OnDestroy {
  currentTab: 'rooms' | 'offers' = 'rooms';
  loading = true;
  error = '';

  // Data arrays
  wishlistRooms: WishlistRoom[] = [];
  wishlistOffers: WishlistOffer[] = [];



  // Modal properties
  showDetailsModal = false;
  selectedRoom: WishlistRoom | null = null;
  showOfferModal = false;
  selectedOffer: WishlistOffer | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    public router: Router,
    private wishlistService: WishlistService
  ) {}

  ngOnInit(): void {
    this.loadWishlistData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ============================================================================
  // 🔹 LOAD WISHLIST DATA
  // ============================================================================

  loadWishlistData(): void {
    this.loading = true;
    this.error = '';

    // Load rooms and offers in parallel
    this.wishlistService.getWishlistRooms()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (rooms: WishlistRoom[]) => {
          this.wishlistRooms = rooms;
          this.loadOffers();
        },
        error: (err) => {
          console.error('Error loading wishlist rooms:', err);
          this.wishlistRooms = [];
          this.loading = false;
          this.error = 'Failed to load wishlist';
        }
      });
  }

  private loadOffers(): void {
    this.wishlistService.getWishlistOffers()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (offers: WishlistOffer[]) => {
          this.wishlistOffers = offers;
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading wishlist offers:', err);
          this.wishlistOffers = [];
          this.loading = false;
          this.error = 'Failed to load offers';
        }
      });
  }

  // ============================================================================
  // 🔹 TAB SWITCHING
  // ============================================================================

  switchTab(tab: 'rooms' | 'offers'): void {
    this.currentTab = tab;
  }


  








  // ============================================================================
  // 🔹 MODAL ACTIONS
  // ============================================================================

  openRoomDetails(room: WishlistRoom): void {
    this.selectedRoom = room;
    this.showDetailsModal = true;
  }

  closeRoomModal(): void {
    this.showDetailsModal = false;
    this.selectedRoom = null;
  }

  openOfferDetails(offer: WishlistOffer): void {
    this.selectedOffer = offer;
    this.showOfferModal = true;
  }

  closeOfferModal(): void {
    this.showOfferModal = false;
    this.selectedOffer = null;
  }

  // ============================================================================
  // 🔹 WISHLIST ACTIONS
  // ============================================================================

  removeFromWishlist(wishlistId: number): void {
    if (!confirm('Remove this item from your wishlist?')) return;

    this.wishlistService.removeFromWishlist(wishlistId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          // Remove from local arrays
          this.wishlistRooms = this.wishlistRooms.filter(r => r.wishlist_id !== wishlistId);
          this.wishlistOffers = this.wishlistOffers.filter(o => o.wishlist_id !== wishlistId);
          alert('Item removed from wishlist');
        },
        error: (err) => {
          console.error('Error removing from wishlist:', err);
          alert('Failed to remove item');
        }
      });
  }

  bookRoom(room: WishlistRoom): void {
    this.router.navigate(['/booking'], {
      queryParams: { room_type_id: room.room_type_id },
      state: { from: '/wishlist' }
    });
  }

  bookOffer(offer: WishlistOffer): void {
    this.router.navigate(['/booking'], {
      queryParams: { offer_id: offer.offer_id },
      state: { from: '/wishlist' }
    });
  }

  viewRoomDetails(roomTypeId: number): void {
    this.router.navigate(['/room-details', roomTypeId], { state: { from: 'wishlist' } });
  }

  viewOfferDetails(offerId: number): void {
    this.router.navigate(['/offer-details', offerId], { state: { from: 'wishlist' } });
  }

  // ============================================================================
  // 🔹 COUNTERS
  // ============================================================================

  getRoomCount(): number {
    return this.wishlistRooms.length;
  }

  getOfferCount(): number {
    return this.wishlistOffers.length;
  }

  getTotalCount(): number {
    return this.getRoomCount() + this.getOfferCount();
  }

  // ============================================================================
  // 🔹 HELPER METHODS
  // ============================================================================

  isOfferExpired(offer: WishlistOffer): boolean {
    const today = new Date();
    return new Date(offer.valid_to) < today;
  }

  getRoomTypesText(offer: WishlistOffer): string {
    if (!offer.room_types || offer.room_types.length === 0) {
      return 'Various rooms';
    }
    return offer.room_types.map((rt: any) => `Room ${rt.room_type_id}`).join(', ');
  }
}
