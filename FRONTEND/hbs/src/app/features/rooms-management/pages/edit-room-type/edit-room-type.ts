import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RoomsService } from '../../../../shared/services/rooms.service';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
@Component({
  selector: 'app-edit-room-type',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent, SpinnerComponent],
  templateUrl: './edit-room-type.html',
  styleUrl: './edit-room-type.css',
})
export class EditRoomTypeComponent implements OnInit {
  roomTypeId: number | null = null;
  roomType: any = null;
  
  // Form fields
  typeName: string = '';
  price: number | string = '';
  maxAdults: number | string = '';
  maxChildren: number | string = '';
  description: string = '';
  descriptionCharCount = 0;
  maxDescriptionChars = 500;

  allAmenities: any[] = [];
  selectedAmenities: number[] = [];

  uploadedImages: File[] = [];
  imagePreviews: string[] = [];
  maxImages = 5;

  // Existing images
  existingImages: any[] = [];
  loadingImages = false;

  uploadedVideos: File[] = [];
  videoPreviews: string[] = [];
  maxVideos = 3;

  showConfirmModal = false;
  showRoomsModal = false;
  roomsForThisType: any[] = [];
  isSaving = false;
  loading = false;
  error: string | null = null;
  success: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private roomsService: RoomsService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.roomTypeId = parseInt(params['id'], 10);
        this.resetForm();
        // Load room type first, then amenities
        this.loadRoomType();
      }
    });
  }

  resetForm(): void {
    this.typeName = '';
    this.price = '';
    this.maxAdults = '';
    this.maxChildren = '';
    this.description = '';
    this.descriptionCharCount = 0;
    this.selectedAmenities = [];
    this.uploadedImages = [];
    this.imagePreviews = [];
    this.uploadedVideos = [];
    this.videoPreviews = [];
    this.error = null;
    this.success = null;
  }

  loadRoomType(): void {
    if (!this.roomTypeId) return;
    this.loading = true;
    this.roomsService.getRoomType(this.roomTypeId).subscribe(
      (data) => {
        this.roomType = data;
        this.typeName = data.type_name;
        this.price = data.price_per_night;
        this.maxAdults = data.max_adult_count;
        this.maxChildren = data.max_child_count;
        this.description = data.description || '';
        this.descriptionCharCount = this.description.length;
        
        // Load existing amenities for this room type (NEW ENDPOINT)
        this.loadRoomTypeAmenities();
        
        // Load existing images
        this.loadExistingImages();
        
        // Load all available amenities after loading room type
        this.loadAmenities();
        this.loading = false;
      },
      (error) => {
        this.error = 'Failed to load room type';
        this.loading = false;
      }
    );
  }

  loadRoomTypeAmenities(): void {
    if (!this.roomTypeId) return;
    
    this.roomsService.getAmenitiesForRoomType(this.roomTypeId).subscribe(
      (response: any) => {
        // Response contains { room_type_id, amenities: [{amenity_id, amenity_name}, ...] }
        if (response.amenities && Array.isArray(response.amenities)) {
          this.selectedAmenities = response.amenities.map((a: any) => a.amenity_id);
        }
      },
      (error) => {
        console.error('Failed to load amenities for room type', error);
        this.selectedAmenities = [];
      }
    );
  }

  loadExistingImages(): void {
    if (!this.roomTypeId) return;
    this.loadingImages = true;
    this.roomsService.getRoomTypeImages(this.roomTypeId).subscribe(
      (data) => {
        this.existingImages = data || [];
        this.loadingImages = false;
      },
      (error) => {
        console.error('Failed to load existing images', error);
        this.loadingImages = false;
      }
    );
  }

  loadAmenities(): void {
    this.roomsService.getAmenities().subscribe(
      (data) => {
        this.allAmenities = data;
      },
      (error) => {
        console.error('Failed to load amenities', error);
      }
    );
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

  onDescriptionInput(event: any): void {
    this.descriptionCharCount = event.target.value.length;
  }

  onImageSelect(event: any): void {
    const files = event.target.files;
    if (files) {
      for (let i = 0; i < files.length && this.uploadedImages.length < this.maxImages; i++) {
        this.uploadedImages.push(files[i]);
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.imagePreviews.push(e.target.result);
        };
        reader.readAsDataURL(files[i]);
      }
    }
  }

  removeImage(index: number): void {
    this.uploadedImages.splice(index, 1);
    this.imagePreviews.splice(index, 1);
  }

  deleteExistingImage(imageId: number, index: number): void {
    if (!this.roomTypeId) return;
    if (confirm('Are you sure you want to delete this image?')) {
      this.roomsService.deleteRoomTypeImages(this.roomTypeId, [imageId]).subscribe(
        () => {
          this.existingImages.splice(index, 1);
          this.success = 'Image deleted successfully';
          setTimeout(() => {
            this.success = null;
          }, 3000);
        },
        (error) => {
          this.error = 'Failed to delete image';
        }
      );
    }
  }

  setImageAsPrimary(imageId: number): void {
    if (!this.roomTypeId) return;
    this.roomsService.markRoomTypeImagePrimary(this.roomTypeId, imageId).subscribe(
      () => {
        // Update the is_primary flag for all images
        this.existingImages.forEach(img => {
          img.is_primary = img.image_id === imageId;
        });
        this.success = 'Image set as primary';
        setTimeout(() => {
          this.success = null;
        }, 3000);
      },
      (error) => {
        this.error = 'Failed to set image as primary';
      }
    );
  }

  onVideoSelect(event: any): void {
    const files = event.target.files;
    if (files) {
      for (let i = 0; i < files.length && this.uploadedVideos.length < this.maxVideos; i++) {
        this.uploadedVideos.push(files[i]);
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.videoPreviews.push(e.target.result);
        };
        reader.readAsDataURL(files[i]);
      }
    }
  }

  removeVideo(index: number): void {
    this.uploadedVideos.splice(index, 1);
    this.videoPreviews.splice(index, 1);
  }

  openConfirmModal(): void {
    this.showConfirmModal = true;
  }

  closeConfirmModal(): void {
    this.showConfirmModal = false;
  }

  openRoomsModal(): void {
    if (this.roomTypeId) {
      this.roomsService.getRooms({ skip: 0, limit: 100, room_type_id: this.roomTypeId }).subscribe({
        next: (response: any) => {
          this.roomsForThisType = response.data || [];
          this.showRoomsModal = true;
        },
        error: (err) => {
          console.error('Failed to load rooms', err);
        }
      });
    }
  }

  closeRoomsModal(): void {
    this.showRoomsModal = false;
    this.roomsForThisType = [];
  }

  viewRoom(roomId: number): void {
    this.router.navigate(['/admin/rooms', roomId, 'view']);
  }

  saveChanges(): void {
    if (!this.roomTypeId) return;

    this.isSaving = true;
    const payload = {
      type_name: this.typeName,
      price_per_night: Number(this.price),
      max_adult_count: Number(this.maxAdults),
      max_child_count: Number(this.maxChildren),
      description: this.description
    };

    this.roomsService.updateRoomType(this.roomTypeId, payload).subscribe(
      (response) => {
        // After updating room type, upload images if any
        if (this.uploadedImages.length > 0) {
          this.uploadImages();
        } else {
          // If no images to upload, proceed to update amenities
          this.updateAmenities();
        }
      },
      (error) => {
        this.error = 'Failed to update room type';
        this.isSaving = false;
      }
    );
  }

  uploadImages(): void {
    if (!this.roomTypeId || this.uploadedImages.length === 0) {
      this.updateAmenities();
      return;
    }

    this.roomsService.uploadRoomTypeImages(this.roomTypeId, this.uploadedImages).subscribe(
      (response: any[]) => {
        this.success = `${response.length} image(s) uploaded successfully!`;
        this.uploadedImages = [];
        this.imagePreviews = [];
        this.updateAmenities();
      },
      (error) => {
        console.error('Image upload error:', error);
        this.error = 'Failed to upload some images. Updates were saved but images may not have been uploaded.';
        this.isSaving = false;
      }
    );
  }

  updateAmenities(): void {
    if (!this.roomTypeId) return;

    // ✅ ALWAYS call the API, even if selectedAmenities is empty (to unmap all)
    this.roomsService.updateRoomTypeAmenities(this.roomTypeId, this.selectedAmenities).subscribe(
      (response: any) => {
        const message = this.selectedAmenities.length === 0 
          ? 'Room type updated successfully - all amenities removed!' 
          : 'Room type updated successfully with amenities!';
        this.success = message;
        this.isSaving = false;
        console.log('[AMENITY_UPDATE] Success:', response);
        setTimeout(() => {
          this.router.navigate(['/admin/room-types-amenities']);
        }, 1500);
      },
      (error: any) => {
        console.error('[AMENITY_UPDATE] Error updating amenities:', error);
        this.success = 'Room type updated but amenities may not have been fully updated';
        this.isSaving = false;
        setTimeout(() => {
          this.router.navigate(['/admin/room-types-amenities']);
        }, 1500);
      }
    );
  }

  cancel(): void {
    this.router.navigate(['/admin/room-types-amenities']);
  }
}
