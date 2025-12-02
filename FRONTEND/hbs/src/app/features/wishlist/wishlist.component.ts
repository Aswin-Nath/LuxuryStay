import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { WishlistService } from '../../services/wishlist.service';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';
import { CustomerSearchComponent, SearchFilters } from '../customer-search/customer-search.component';

interface WishlistItem {
  id: string;
  type: 'room' | 'offer';
  name: string;
  image?: string;
  price: number;
  originalPrice?: number;
  discount?: string;
  description?: string;
  rating?: number;
  reviews?: number;
  dateAdded: string;
  available?: boolean;
}

@Component({
  selector: 'app-wishlist',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent, CustomerSearchComponent],
  templateUrl: './wishlist.component.html',
  styleUrl: './wishlist.component.css',
})
export class WishlistComponent implements OnInit, OnDestroy {
  wishlistItems: WishlistItem[] = [];
  filteredItems: WishlistItem[] = [];
  currentTab: 'all' | 'rooms' | 'offers' = 'all';
  loading = true;
  error = '';

  // Filter properties
  minPriceFilter = 0;
  maxPriceFilter = 50000;
  availabilityFilter = 'all';

  // Details modal
  showDetailsModal = false;
  selectedItem: WishlistItem | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private router: Router,
    private wishlistService: WishlistService
  ) {}

  ngOnInit(): void {
    this.loadWishlist();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadWishlist(): void {
    this.loading = true;
    this.wishlistService.getWishlist()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (items: any[]) => {
          this.wishlistItems = items.map((item: any) => ({
            id: item.wishlist_id?.toString() || `${item.item_type}${item.room_type_id || item.offer_id}`,
            type: item.item_type,
            name: item.name,
            image: item.image || '/assets/placeholder.jpg',
            price: item.price,
            originalPrice: item.original_price,
            discount: item.discount ? `${item.discount}% OFF` : undefined,
            rating: item.rating,
            reviews: item.review_count,
            description: item.description,
            dateAdded: item.created_at,
            available: item.available !== false,
          }));
          this.filterItems();
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading wishlist:', err);
          // Load fallback dummy data
          this.wishlistItems = [
            {
              id: 'room1',
              type: 'room',
              name: 'Deluxe Room',
              image: '/assets/room1.jpg',
              price: 4500,
              rating: 4.8,
              reviews: 124,
              description: 'Spacious deluxe room with sea view',
              dateAdded: '2024-01-15',
              available: true,
            },
            {
              id: 'offer1',
              type: 'offer',
              name: 'Weekend Getaway Package',
              image: '/assets/hotel_luxury.jpg',
              price: 12000,
              originalPrice: 15000,
              discount: '20% OFF',
              description: '2 nights stay + breakfast + spa access',
              dateAdded: '2024-01-12',
            },
            {
              id: 'room2',
              type: 'room',
              name: 'Executive Suite',
              image: '/assets/room3.jpg',
              price: 8500,
              rating: 4.9,
              reviews: 89,
              description: 'Luxurious suite with premium amenities',
              dateAdded: '2024-01-10',
              available: true,
            },
          ];
          this.filterItems();
          this.loading = false;
        }
      });
  }

  switchTab(tab: 'all' | 'rooms' | 'offers'): void {
    this.currentTab = tab;
    this.filterItems();
  }

  filterItems(): void {
    let filtered = this.wishlistItems;

    // Filter by tab
    if (this.currentTab === 'rooms') {
      filtered = filtered.filter((item) => item.type === 'room');
    } else if (this.currentTab === 'offers') {
      filtered = filtered.filter((item) => item.type === 'offer');
    }

    // Filter by price
    filtered = filtered.filter((item) => item.price >= this.minPriceFilter && item.price <= this.maxPriceFilter);

    // Filter by availability
    if (this.availabilityFilter === 'available' && this.currentTab === 'rooms') {
      filtered = filtered.filter((item) => item.available);
    }

    this.filteredItems = filtered;
  }

  onSearchFiltersChanged(filters: SearchFilters): void {
    let filtered = this.wishlistItems;

    // Text search - search in item name and description
    if (filters.searchText && filters.searchText.trim()) {
      const searchTerm = filters.searchText.toLowerCase();
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(searchTerm) ||
        (item.description && item.description.toLowerCase().includes(searchTerm))
      );
    }

    // Price filter
    if (filters.priceMin !== undefined && filters.priceMin !== null) {
      filtered = filtered.filter(item => item.price >= filters.priceMin!);
    }

    if (filters.priceMax !== undefined && filters.priceMax !== null) {
      filtered = filtered.filter(item => item.price <= filters.priceMax!);
    }

    // Sort
    if (filters.sortBy) {
      filtered.sort((a, b) => {
        switch (filters.sortBy) {
          case 'price-low':
            return a.price - b.price;
          case 'price-high':
            return b.price - a.price;
          default:
            return 0;
        }
      });
    }

    this.filteredItems = filtered;
  }

  removeFromWishlist(itemId: string): void {
    const item = this.wishlistItems.find((i) => i.id === itemId);
    if (!item) return;

    this.wishlistService.removeFromWishlist(parseInt(itemId))
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          const index = this.wishlistItems.findIndex((i) => i.id === itemId);
          if (index > -1) {
            this.wishlistItems.splice(index, 1);
            this.filterItems();
            alert('Item removed from wishlist');
          }
        },
        error: (err) => {
          console.error('Error removing from wishlist:', err);
          // Still remove locally on error
          const index = this.wishlistItems.findIndex((i) => i.id === itemId);
          if (index > -1) {
            this.wishlistItems.splice(index, 1);
            this.filterItems();
          }
        }
      });
  }

  viewDetails(item: WishlistItem): void {
    this.selectedItem = item;
    this.showDetailsModal = true;
  }

  closeDetailsModal(): void {
    this.showDetailsModal = false;
    this.selectedItem = null;
  }

  bookNow(item: WishlistItem): void {
    if (item.type === 'room') {
      this.router.navigate(['/booking'], {
        queryParams: { room_type_id: item.id },
      });
    } else if (item.type === 'offer') {
      this.router.navigate(['/booking'], {
        queryParams: { offer_id: item.id },
      });
    }
  }

  claimOffer(item: WishlistItem): void {
    alert(`Claim offer: ${item.name}`);
    this.bookNow(item);
  }

  clearAllFilters(): void {
    this.minPriceFilter = 0;
    this.maxPriceFilter = 50000;
    this.availabilityFilter = 'all';
    this.filterItems();
  }

  applyFilters(): void {
    this.filterItems();
  }

  getRoomCard(item: WishlistItem): string {
    if (!item.rating) return 'No rating';
    return `${item.rating}/5 (${item.reviews} reviews)`;
  }

  getDiscountBadge(item: WishlistItem): string {
    if (item.discount) return item.discount;
    if (item.originalPrice && item.price) {
      const discount = Math.round(((item.originalPrice - item.price) / item.originalPrice) * 100);
      return `${discount}% OFF`;
    }
    return '';
  }

  getRoomCount(): number {
    return this.wishlistItems.filter((item) => item.type === 'room').length;
  }

  getOfferCount(): number {
    return this.wishlistItems.filter((item) => item.type === 'offer').length;
  }
}
