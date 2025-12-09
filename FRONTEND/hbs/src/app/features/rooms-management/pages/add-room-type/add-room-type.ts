import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoomsService } from '../../../../shared/services/rooms.service';

interface Amenity {
  amenity_id: number;
  amenity_name: string;
  roomCount?: number;
}

@Component({
  selector: 'app-add-room-type',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-room-type.html',
  styleUrl: './add-room-type.css',
})
export class AddRoomTypeComponent implements OnInit {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  // Form fields
  roomTypeName: string = '';
  pricePerNight: number | null = null;
  adultsCapacity: number | null = null;
  childrenCapacity: number | null = null;
  squareFeet: number | null = null;
  description: string = '';
  selectedAmenities: number[] = [];
  uploadedImages: File[] = [];
  imagePreview: string | null = null;

  isSaving = false;
  isLoadingAmenities = false;
  error: string | null = null;
  success: string | null = null;

  // Amenities loaded from database
  availableAmenities: Amenity[] = [];

  constructor(private roomsService: RoomsService) {}

  ngOnInit(): void {
    this.loadAmenities();
  }

  loadAmenities(): void {
    this.isLoadingAmenities = true;
    this.roomsService.getAmenitiesWithRoomCount().subscribe({
      next: (amenities) => {
        this.availableAmenities = amenities;
        this.isLoadingAmenities = false;
      },
      error: (err) => {
        console.error('Failed to load amenities:', err);
        this.isLoadingAmenities = false;
      }
    });
  }

  toggleAmenity(amenityId: number): void {
    const index = this.selectedAmenities.indexOf(amenityId);
    if (index > -1) {
      this.selectedAmenities.splice(index, 1);
    } else {
      this.selectedAmenities.push(amenityId);
    }
  }

  isAmenitySelected(amenityId: number): boolean {
    return this.selectedAmenities.includes(amenityId);
  }

  onImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadedImages = Array.from(input.files);
      
      // Show preview of first image
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imagePreview = e.target?.result as string;
      };
      reader.readAsDataURL(input.files[0]);
    }
  }

  removeImage(): void {
    this.uploadedImages = [];
    this.imagePreview = null;
  }

  saveRoomType(): void {
    // Validation
    if (!this.roomTypeName.trim()) {
      this.error = 'Room type name is required';
      return;
    }

    if (!this.pricePerNight || this.pricePerNight <= 0) {
      this.error = 'Price per night must be greater than 0';
      return;
    }

    if (!this.adultsCapacity || this.adultsCapacity <= 0) {
      this.error = 'Adults capacity must be at least 1';
      return;
    }

    if (this.childrenCapacity === null || this.childrenCapacity < 0) {
      this.error = 'Children capacity cannot be negative';
      return;
    }

    if (!this.squareFeet || this.squareFeet <= 0) {
      this.error = 'Square feet must be greater than 0';
      return;
    }

    this.isSaving = true;
    this.error = null;
    this.success = null;

    // Create FormData for file upload
    const formData = new FormData();
    formData.append('room_type_name', this.roomTypeName);
    formData.append('price_per_night', this.pricePerNight.toString());
    formData.append('occupancy_limit_adults', this.adultsCapacity.toString());
    formData.append('occupancy_limit_children', this.childrenCapacity.toString());
    formData.append('square_ft', this.squareFeet.toString());
    formData.append('description', this.description);
    formData.append('amenities', JSON.stringify(this.selectedAmenities));

    // Append images
    if (this.uploadedImages.length > 0) {
      for (const image of this.uploadedImages) {
        formData.append('images', image);
      }
    }

    this.roomsService.createRoomTypeWithImages(formData).subscribe({
      next: (response: any) => {
        this.success = 'Room type created successfully';
        this.isSaving = false;
        setTimeout(() => {
          this.saved.emit();
          this.closeModal();
        }, 1000);
      },
      error: (error: any) => {
        this.error = error.error?.detail || 'Failed to create room type';
        this.isSaving = false;
      }
    });
  }

  closeModal(): void {
    this.resetForm();
    this.close.emit();
  }

  resetForm(): void {
    this.roomTypeName = '';
    this.pricePerNight = null;
    this.adultsCapacity = null;
    this.childrenCapacity = null;
    this.squareFeet = null;
    this.description = '';
    this.selectedAmenities = [];
    this.uploadedImages = [];
    this.imagePreview = null;
    this.error = null;
    this.success = null;
  }
}
