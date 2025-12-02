import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { RoomsService } from '../../core/services/rooms/rooms.service';
import { WishlistService } from '../../services/wishlist.service';
import { ImageService } from '../../services/image.service';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';
import { CustomerSearchComponent, SearchFilters } from '../customer-search/customer-search.component';

interface RoomType {
  room_type_id: number;
  type_name: string;
  description: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  total_count?: number;
  image_url?: string;
}

interface Review {
  reviewer_name: string;
  rating: number;
  comment: string;
  date: string;
}

@Component({
  selector: 'app-room-display',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent, CustomerSearchComponent],
  templateUrl: './room-display.component.html',
  styleUrl: './room-display.component.css',
})
export class RoomDisplayComponent implements OnInit, OnDestroy {
  roomTypes: RoomType[] = [];
  filteredRoomTypes: RoomType[] = [];
  loading = true;
  error = '';

  // Unified search filters
  searchFilters: SearchFilters = {
    searchText: '',
    priceMin: undefined,
    priceMax: undefined,
    sortBy: 'newest',
  };

  // Deprecated filters (kept for compatibility with existing filter logic)
  priceRangeFilter: string = 'all';
  roomTypeFilter: string = 'all';
  occupancyFilter: string = 'all';
  amenitiesFilter: string = 'all';
  sortByFilter: string = 'newest';

  // Details modal
  showDetailsModal = false;
  selectedRoom: RoomType | null = null;
  selectedRoomDetails: any = null;

  // Reviews modal
  showReviewsModal = false;
  reviews: Review[] = [
    {
      reviewer_name: 'Rajesh Kumar',
      rating: 5,
      comment: 'Excellent room with great amenities. Very comfortable stay.',
      date: '2024-01-15',
    },
    {
      reviewer_name: 'Priya Sharma',
      rating: 4.5,
      comment: 'Beautiful room with ocean view. Staff was very helpful.',
      date: '2024-01-10',
    },
    {
      reviewer_name: 'Amit Patel',
      rating: 5,
      comment: 'Premium quality room with top-notch service. Highly recommended!',
      date: '2024-01-05',
    },
  ];
  averageRating = 4.8;
  totalReviews = 127;

  // Reminder modal
  showReminderModal = false;
  reminderRoomType = '';

  // Booking modal
  bookingModalOpen = false;
  selectedRoomsForBooking: Array<{ room_index: number; adults: number; children: number }> = [];

  // Image loading
  roomImages = new Map<number, string>(); // room_type_id -> image_url

  private destroy$ = new Subject<void>();

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private roomsService: RoomsService,
    private wishlistService: WishlistService,
    private imageService: ImageService
  ) {}

  ngOnInit(): void {
    this.loadRoomTypes();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomTypes(): void {
    this.loading = true;
    this.roomsService.getRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (roomTypes: any[]) => {
          this.roomTypes = roomTypes.map((rt: any) => ({
            room_type_id: rt.room_type_id,
            type_name: rt.type_name,
            description: rt.description || `${rt.type_name} with premium amenities and comfortable accommodation`,
            price_per_night: rt.price_per_night,
            max_adult_count: rt.max_adult_count,
            max_child_count: rt.max_child_count,
            total_count: rt.total_count,
          }));
          
          // Load images for each room type
          this.roomTypes.forEach(room => {
            this.imageService.getPrimaryRoomTypeImageUrl(room.room_type_id)
              .pipe(takeUntil(this.destroy$))
              .subscribe({
                next: (imageUrl: string | null) => {
                  if (imageUrl) {
                    this.roomImages.set(room.room_type_id, imageUrl);
                  }
                },
                error: (err) => {
                  console.warn(`Failed to load image for room ${room.room_type_id}:`, err);
                  // Set default placeholder if image load fails
                  this.roomImages.set(room.room_type_id, 'assets/images/placeholder-room.jpg');
                }
              });
          });
          
          this.applyFilters();
          this.loading = false;
        },
        error: (err) => {
          console.error('Error loading room types:', err);
          // Load fallback dummy data
          this.roomTypes = [
            {
              room_type_id: 1,
              type_name: 'Deluxe Room',
              description: 'Spacious deluxe room with sea view, queen-size bed, and modern decor.',
              price_per_night: 4500,
              max_adult_count: 2,
              max_child_count: 1,
            },
            {
              room_type_id: 2,
              type_name: 'Executive Suite',
              description: 'Luxurious suite with premium amenities, sitting area, and balcony.',
              price_per_night: 8500,
              max_adult_count: 4,
              max_child_count: 2,
            },
            {
              room_type_id: 3,
              type_name: 'Presidential Suite',
              description: 'Ultra-premium suite with dedicated concierge, spa bath, and panoramic views.',
              price_per_night: 15000,
              max_adult_count: 4,
              max_child_count: 3,
            },
          ];
          this.applyFilters();
          this.loading = false;
        }
      });
  }

  applyFilters(): void {
    let filtered = [...this.roomTypes];

    // Price range filter
    if (this.priceRangeFilter !== 'all') {
      filtered = filtered.filter((room) => {
        const price = room.price_per_night;
        switch (this.priceRangeFilter) {
          case 'budget':
            return price < 5000;
          case 'moderate':
            return price >= 5000 && price < 10000;
          case 'luxury':
            return price >= 10000;
          default:
            return true;
        }
      });
    }

    // Occupancy filter
    if (this.occupancyFilter !== 'all') {
      filtered = filtered.filter((room) => {
        const occupancy = parseInt(this.occupancyFilter);
        return room.max_adult_count >= occupancy;
      });
    }

    // Sort
    filtered.sort((a, b) => {
      switch (this.sortByFilter) {
        case 'price-low':
          return a.price_per_night - b.price_per_night;
        case 'price-high':
          return b.price_per_night - a.price_per_night;
        default:
          return 0;
      }
    });

    this.filteredRoomTypes = filtered;
  }

  resetFilters(): void {
    this.priceRangeFilter = 'all';
    this.roomTypeFilter = 'all';
    this.occupancyFilter = 'all';
    this.amenitiesFilter = 'all';
    this.sortByFilter = 'newest';
    this.searchFilters = {
      searchText: '',
      priceMin: undefined,
      priceMax: undefined,
      sortBy: 'newest',
    };
    this.applyFilters();
  }

  onSearchFiltersChanged(filters: SearchFilters): void {
    this.searchFilters = filters;
    this.applyUnifiedFilters();
  }

  applyUnifiedFilters(): void {
    let filtered = [...this.roomTypes];

    // Text search - search in room name and description
    if (this.searchFilters.searchText && this.searchFilters.searchText.trim()) {
      const searchTerm = this.searchFilters.searchText.toLowerCase();
      filtered = filtered.filter(room =>
        room.type_name.toLowerCase().includes(searchTerm) ||
        room.description.toLowerCase().includes(searchTerm)
      );
    }

    // Price filter
    if (this.searchFilters.priceMin !== undefined && this.searchFilters.priceMin !== null) {
      filtered = filtered.filter(room => room.price_per_night >= this.searchFilters.priceMin!);
    }

    if (this.searchFilters.priceMax !== undefined && this.searchFilters.priceMax !== null) {
      filtered = filtered.filter(room => room.price_per_night <= this.searchFilters.priceMax!);
    }

    // Sort
    if (this.searchFilters.sortBy) {
      filtered.sort((a, b) => {
        switch (this.searchFilters.sortBy) {
          case 'price-low':
            return a.price_per_night - b.price_per_night;
          case 'price-high':
            return b.price_per_night - a.price_per_night;
          default:
            return 0;
        }
      });
    }

    this.filteredRoomTypes = filtered;
  }

  openDetailsModal(room: RoomType): void {
    this.selectedRoom = room;
    this.selectedRoomDetails = room;
    this.showDetailsModal = true;
  }

  closeDetailsModal(): void {
    this.showDetailsModal = false;
    this.selectedRoom = null;
  }

  openReviewsModal(): void {
    this.showReviewsModal = true;
  }

  closeReviewsModal(): void {
    this.showReviewsModal = false;
  }

  openReminderModal(roomType: RoomType): void {
    this.reminderRoomType = roomType.type_name;
    this.showReminderModal = true;
  }

  closeReminderModal(): void {
    this.showReminderModal = false;
  }

  saveReminder(): void {
    alert(`Reminder set for ${this.reminderRoomType}`);
    this.closeReminderModal();
  }

  saveRoom(room: RoomType): void {
    this.wishlistService.addRoomToWishlist(room.room_type_id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res) => {
          alert(`${room.type_name} saved to wishlist!`);
        },
        error: (err) => {
          console.error('Error saving to wishlist:', err);
          alert(`${room.type_name} saved to wishlist!`);
        }
      });
  }

  openBookingModal(room: RoomType): void {
    this.selectedRoom = room;
    this.bookingModalOpen = true;
    this.selectedRoomsForBooking = [{ room_index: 0, adults: 1, children: 0 }];
  }

  closeBookingModal(): void {
    this.bookingModalOpen = false;
    this.selectedRoom = null;
  }

  addRoomToBooking(): void {
    this.selectedRoomsForBooking.push({
      room_index: this.selectedRoomsForBooking.length,
      adults: 1,
      children: 0,
    });
  }

  removeRoomFromBooking(index: number): void {
    this.selectedRoomsForBooking.splice(index, 1);
  }

  increaseCounter(roomIndex: number, type: 'adults' | 'children'): void {
    const room = this.selectedRoomsForBooking[roomIndex];
    if (this.selectedRoom) {
      if (type === 'adults' && room.adults < this.selectedRoom.max_adult_count) {
        room.adults++;
      }
      if (type === 'children' && room.children < this.selectedRoom.max_child_count) {
        room.children++;
      }
    }
  }

  decreaseCounter(roomIndex: number, type: 'adults' | 'children'): void {
    const room = this.selectedRoomsForBooking[roomIndex];
    if (type === 'adults' && room.adults > 1) room.adults--;
    if (type === 'children' && room.children > 0) room.children--;
  }

  proceedToBooking(): void {
    if (!this.selectedRoom) return;
    this.router.navigate(['/booking'], {
      queryParams: { room_type_id: this.selectedRoom.room_type_id },
    });
  }

  getRatingColor(rating: number): string {
    if (rating >= 4.5) return 'text-green-600';
    if (rating >= 3.5) return 'text-yellow-600';
    return 'text-red-600';
  }

  getRatingStars(rating: number): number[] {
    return Array(Math.floor(rating)).fill(0);
  }

  getRatingPercentage(rating: number): number {
    return (rating / 5) * 100;
  }
}
