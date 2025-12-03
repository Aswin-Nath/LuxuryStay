import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CustomerNavbarComponent } from '../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../core/components/customer-sidebar/customer-sidebar.component';
import { RoomTypeService } from '../../services/room-types.service';
import { ImageService } from '../../services/image.service';
import { RoomsService } from '../../core/services/rooms/rooms.service';
import { ReviewsService, Review } from '../../services/reviews.service';
import { WishlistService } from '../../services/wishlist.service';
interface Amenity{
    amenity_id:number,
    amenity_name:string
}
interface RoomDetail {
  room_type_id: number;
  type_name: string;
  description: string;
  price_per_night: number;
  square_ft: number;
  max_adult_count: number;
  max_child_count: number;
  amenities: Amenity[];
  primary_image: string | null;
  images: string[];
}

@Component({
  selector: 'app-customer-room-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, CustomerNavbarComponent],
  templateUrl: './customer-room-detail.component.html',
  styleUrl: './customer-room-detail.component.css',
})
export class CustomerRoomDetailComponent implements OnInit, OnDestroy {
  roomId: number | null = null;
  room: RoomDetail | null = null;
  reviews: Review[] = [];
  loading = true;
  error = '';
  previousPage = 'room-display';
  
  selectedImageIndex = 0;
  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    public router: Router,
    private imageService: ImageService,
    private roomTypeService: RoomTypeService,
    private reviewsService: ReviewsService,
    private wishlistService: WishlistService,
    private roomService:RoomsService
  ) {
    const navigation = this.router.getCurrentNavigation();
    this.previousPage = navigation?.extras?.state?.['from'] || 'rooms';
  }

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      console.log(this.previousPage);
      this.roomId = +params['id'];
      this.loadRoomDetails();
      this.loadReviews();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomDetails(): void {
    if (!this.roomId) return;
    
    this.loading = true;
    const roomTypeId = this.roomId;
    
    // Fetch room type details
    this.roomTypeService.getRoomType(roomTypeId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (roomType: any) => {
        // Fetch room type images
        this.imageService.getRoomTypeImages(roomTypeId).pipe(takeUntil(this.destroy$)).subscribe({
          next: (images: any[]) => {
            // Fetch room type amenities
            this.roomService.getAmenitiesForRoomType(roomTypeId).pipe(takeUntil(this.destroy$)).subscribe({
              next: (details: any) => {
                this.room = {
                  room_type_id: roomType.room_type_id,
                  type_name: roomType.type_name,
                  description: roomType.description,
                  price_per_night: roomType.price_per_night,
                  square_ft: roomType.square_ft,
                  max_adult_count: roomType.max_adult_count,
                  max_child_count: roomType.max_child_count,
                  amenities: details.amenities || [],
                  primary_image: images.find((img: any) => img.is_primary)?.image_url || images[0]?.image_url || null,
                  images: images.map((img: any) => img.image_url)
                };
                this.loading = false;
              },
              error: () => {
                this.loading = false;
                this.error = 'Failed to load room amenities';
              }
            });
          },
          error: () => {
            // Images might be empty, continue with room details
            this.room = {
              room_type_id: roomType.room_type_id,
              type_name: roomType.type_name,
              description: roomType.description,
              price_per_night: roomType.price_per_night,
              square_ft: roomType.square_ft,
              max_adult_count: roomType.max_adult_count,
              max_child_count: roomType.max_child_count,
              amenities: [],
              primary_image: null,
              images: []
            };
            this.loading = false;
          }
        });
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load room details';
      }
    });
  }

  loadReviews(): void {
    if (!this.roomId) return;

    const roomTypeId = this.roomId;
    this.reviewsService.getReviewsByRoomType(roomTypeId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (reviews: Review[]) => {
        this.reviews = reviews || [];
      },
      error: () => {
        this.reviews = [];
      }
    });
  }

  selectImage(index: number): void {
    this.selectedImageIndex = index;
  }

  bookNow(): void {
    this.router.navigate(['/booking'], { 
      queryParams: { room_type_id: this.roomId },
      state: { from: this.previousPage }
    });
  }

  goBack(): void {
    if (this.previousPage === 'wishlist') {
      this.router.navigate(['/wishlist']);
    } else if (this.previousPage === 'rooms' || this.previousPage === 'room-display') {
      this.router.navigate(['/rooms']);
    } else {
      this.router.navigate(['/rooms']);
    }
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
}
