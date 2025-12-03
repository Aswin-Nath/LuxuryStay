import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { RoomsService } from '../../core/services/rooms/rooms.service';
import { WishlistService } from '../../services/wishlist.service';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';

export interface RoomType {
  room_type_id: number;
  type_name: string;
  description: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  square_ft?: number;
  total_count?: number;
  image_url?: string;
  is_saved_to_wishlist?: boolean;
  wishlist_id?: number;  // ID to use for removing from wishlist
}

export interface Review {
  reviewer_name: string;
  rating: number;
  comment: string;
  date: string;
}

@Component({
  selector: 'app-room-display',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent],
  templateUrl: './room-display.component.html',
  styleUrl: './room-display.component.css',
})
export class RoomDisplayComponent implements OnInit, OnDestroy {
  @ViewChild(CustomerNavbarComponent) navbarComponent!: CustomerNavbarComponent;
  roomTypes: RoomType[] = [];
  filteredRoomTypes: RoomType[] = [];
  loading = true;
  loadingRoomTypes = false;
  error = '';

  // Advanced filter properties
  selectedRoomTypeId: number | null = null;
  minPrice: number | null = null;
  maxPrice: number | null = null;
  minAdults: number | null = null;
  minChildren: number | null = null;
  minSquareFt: number | null = null;
  maxSquareFt: number | null = null;

  // Details modal
  showDetailsModal = false;
  selectedRoom: RoomType | null = null;
  selectedRoomDetails: any = null;
  viewRoomDetails(Room: RoomType): void {
    this.router.navigate(['/room-details', Room.room_type_id], { state: { from: 'rooms' } });
  }
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
  roomReviews = new Map<number, { rating: number; count: number }>(); // room_type_id -> {rating, count}

  private destroy$ = new Subject<void>();

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private roomsService: RoomsService,
    private wishlistService: WishlistService
  ) {}

  ngOnInit(): void {
    this.loadRoomTypes();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomTypes(): void {
    this.loadingRoomTypes = true;
    this.applyFilters();
  }

  applyFilters(): void {
    this.loading = true;
    
    // Build filter parameters
    const filters = {
      room_type_id: this.selectedRoomTypeId,
      price_min: this.minPrice,
      price_max: this.maxPrice,
      adult_count: this.minAdults,
      child_count: this.minChildren,
      square_ft_min: this.minSquareFt,
      square_ft_max: this.maxSquareFt,
    };

    this.roomsService.getRoomTypesCustomer(filters)
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
            square_ft: rt.square_ft,
            is_saved_to_wishlist: rt.is_saved_to_wishlist || false,
            wishlist_id: rt.wishlist_id,
          }));
          
          // Fetch all images and reviews in a single call (optimization)
          this.roomsService.getRoomMedias()
            .pipe(takeUntil(this.destroy$))
            .subscribe({
              next: (medias: any) => {
                // Process images and reviews for all room types
                for (const [roomTypeId, mediaData] of Object.entries(medias)) {
                  const id = parseInt(roomTypeId, 10);
                  const media = mediaData as any;
                  
                  // Process images - get primary image URL
                  if (media.images && media.images.length > 0) {
                    const primaryImage = media.images.find((img: any) => img.is_primary);
                    const imageUrl = primaryImage?.image_url || media.images[0]?.image_url;
                    if (imageUrl) {
                      this.roomImages.set(id, imageUrl);
                    }
                  }
                  
                  // Process reviews - calculate average rating
                  if (media.reviews && media.reviews.length > 0) {
                    const avgRating = media.reviews.reduce((sum: number, r: any) => sum + r.rating, 0) / media.reviews.length;
                    this.roomReviews.set(id, {
                      rating: Math.round(avgRating * 10) / 10,
                      count: media.reviews.length
                    });
                  } else {
                    this.roomReviews.set(id, { rating: 0, count: 0 });
                  }
                }
                
                this.filteredRoomTypes = this.roomTypes;
                this.loading = false;
                this.loadingRoomTypes = false;
              },
              error: (err) => {
                console.warn('Failed to load room medias:', err);
                // Set defaults if medias fail to load
                this.roomTypes.forEach(room => {
                  this.roomImages.set(room.room_type_id, 'assets/images/placeholder-room.jpg');
                  this.roomReviews.set(room.room_type_id, { rating: 0, count: 0 });
                });
                this.filteredRoomTypes = this.roomTypes;
                this.loading = false;
                this.loadingRoomTypes = false;
              }
            });
        },
        error: (err) => {
          console.error('Error loading room types:', err);
          // Fall back to client-side filtering with existing data
          this.loading = false;
          this.loadingRoomTypes = false;
        }
      });
  }

  resetFilters(): void {
    this.selectedRoomTypeId = null;
    this.minPrice = null;
    this.maxPrice = null;
    this.minAdults = null;
    this.minChildren = null;
    this.minSquareFt = null;
    this.maxSquareFt = null;
    this.applyFilters();
  }

  onFilterChange(): void {
    this.applyFilters();
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
    if (room.is_saved_to_wishlist && room.wishlist_id) {
      // Remove from wishlist using wishlist_id
      this.wishlistService.removeFromWishlist(room.wishlist_id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            room.is_saved_to_wishlist = false;
            room.wishlist_id = undefined;
          },
          error: (err: any) => {
            console.error('Error removing from wishlist:', err);
          }
        });
    } else {
      // Add to wishlist
      this.wishlistService.addRoomToWishlist(room.room_type_id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (res: any) => {
            room.is_saved_to_wishlist = true;
            room.wishlist_id = res.wishlist_id;
          },
          error: (err: any) => {
            console.error('Error saving to wishlist:', err);
          }
        });
    }
  }

  openBookingModal(room: RoomType): void {
    this.navbarComponent?.openBookingModal();
  }

  closeBookingModal(): void {
    this.navbarComponent?.closeBookingModal();
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
      state: { from: '/rooms' }
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
