import {
  Component,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { OfferService } from '../../../../services/offer.service';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';

interface RoomTypeSelection {
  room_type_id: number;
  type_name: string;
  total_available: number;
  selected_count: number;
  discount_percent: number;
}

const MAX_ROOMS_PER_OFFER = 5;

@Component({
  selector: 'app-edit-offer',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './edit-offer.component.html',
  styleUrl: './edit-offer.component.css',
})
export class EditOfferComponent implements OnInit, OnDestroy {
  offerId: number | null = null;
  form!: FormGroup;
  roomTypes: any[] = [];
  selectedRoomTypes: RoomTypeSelection[] = [];
  discountMode: 'same' | 'per-room' = 'same';
  loading = false;
  error = '';
  successMessage = '';
  imageFile: File | null = null;
  imagePreviewUrl: string | null = null;
  existingImages: any[] = [];
  imagePreviews: string[] = [];
  imageFiles: File[] = [];
  primaryImageIndex: number = -1;
  uploadingImages = false;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private offerService: OfferService,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.form = this.fb.group({
      offer_name: ['', [Validators.required, Validators.minLength(3)]],
      description: ['', [Validators.minLength(10)]],
      discount_percent: [0, [Validators.required, Validators.min(0), Validators.max(100)]],
      valid_from: [new Date().toISOString().split('T')[0], Validators.required],
      valid_to: ['', Validators.required],
      max_uses: [null],
    });
  }

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      if (params['id']) {
        this.offerId = parseInt(params['id'], 10);
        this.loadRoomTypes();
      } else {
        this.error = 'Invalid offer ID';
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomTypes(): void {
    this.offerService
      .getRoomTypesWithCounts()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (types) => {
          this.roomTypes = types;
          this.loadOfferData()
          this.loadOfferData()
        },
        error: (err) => {
          this.error = 'Failed to load room types';
          console.error(err);
        },
      });
  }

  loadOfferData(): void {
    if (!this.offerId) return;
    this.loading = true;
    this.offerService
      .getOffer(this.offerId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (offer) => {
          this.form.patchValue({
            offer_name: offer.offer_name,
            description: offer.description,
            discount_percent: offer.discount_percent,
            valid_from: offer.valid_from,
            valid_to: offer.valid_to,
            max_uses: offer.max_uses,
          });

          if (offer.room_types && Array.isArray(offer.room_types)) {
            this.selectedRoomTypes = offer.room_types.map((rt: any) => ({
              room_type_id: rt.room_type_id,
              type_name: this.getRoomTypeName(rt.room_type_id),
              total_available: this.getTotalAvailableForType(rt.room_type_id),
              selected_count: rt.available_count,
              discount_percent: rt.discount_percent,
            }));

            const discountPercentages = this.selectedRoomTypes.map((rt) => rt.discount_percent);
            this.discountMode = this.allSame(discountPercentages) ? 'same' : 'per-room';
          }

          this.loadExistingImages();
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Failed to load offer details';
          this.loading = false;
        },
      });
  }

  get totalSelectedRooms(): number {
    return this.selectedRoomTypes.reduce((sum, rt) => sum + rt.selected_count, 0);
  }

  get canAddMoreRooms(): boolean {
    return this.totalSelectedRooms < MAX_ROOMS_PER_OFFER;
  }

  getRoomTypeName(roomTypeId: number): string {
    console.log(roomTypeId,this.roomTypes);
    const rt = this.roomTypes.find((r) => r.room_type_id === roomTypeId);
    return rt ? rt.type_name : 'Unknown';
  }

  getTotalAvailableForType(roomTypeId: number): number {
    const rt = this.roomTypes.find((r) => r.room_type_id === roomTypeId);
    return rt ? rt.total_count : 0;
  }

  onDiscountModeChange(): void {
    if (this.discountMode === 'same') {
      const baseDiscount = this.form.get('discount_percent')?.value || 0;
      this.selectedRoomTypes.forEach((rt) => {
        rt.discount_percent = baseDiscount;
      });
    }
  }

  addRoomType(roomTypeId: number): void {
    if (!roomTypeId) return;
    
    if (this.selectedRoomTypes.some((rt) => rt.room_type_id === roomTypeId)) {
      this.error = 'Room type already selected';
      return;
    }

    if (!this.canAddMoreRooms) {
      this.error = `Maximum ${MAX_ROOMS_PER_OFFER} rooms limit reached. Remove a room type first.`;
      return;
    }

    const roomType = this.roomTypes.find((r) => r.room_type_id === roomTypeId);
    if (!roomType) {
      this.error = 'Room type not found';
      return;
    }

    const availableCount = roomType.total_count || 0;
    const remainingSlots = MAX_ROOMS_PER_OFFER - this.totalSelectedRooms;
    const maxSelectable = Math.min(availableCount, remainingSlots);

    if (maxSelectable === 0) {
      this.error = `No more room slots available. Cannot add more than ${MAX_ROOMS_PER_OFFER} rooms total.`;
      return;
    }

    this.selectedRoomTypes.push({
      room_type_id: roomTypeId,
      type_name: roomType.type_name,
      total_available: availableCount,
      selected_count: Math.min(1, maxSelectable),
      discount_percent: this.form.get('discount_percent')?.value || 0,
    });

    this.error = '';
  }

  removeRoomType(roomTypeId: number): void {
    this.selectedRoomTypes = this.selectedRoomTypes.filter(
      (rt) => rt.room_type_id !== roomTypeId
    );
  }

  validateRoomCount(): void {
    let total = this.totalSelectedRooms;
    if (total > MAX_ROOMS_PER_OFFER) {
      this.error = `Total rooms cannot exceed ${MAX_ROOMS_PER_OFFER}. Please adjust the counts.`;
      let excess = total - MAX_ROOMS_PER_OFFER;
      for (let i = this.selectedRoomTypes.length - 1; i >= 0 && excess > 0; i--) {
        const rt = this.selectedRoomTypes[i];
        if (rt.selected_count > 1) {
          const reduction = Math.min(rt.selected_count - 1, excess);
          rt.selected_count -= reduction;
          excess -= reduction;
        }
      }
    } else {
      this.error = '';
    }
  }

  isRoomTypeSelected(roomTypeId: number): boolean {
    return this.selectedRoomTypes.some((rt) => rt.room_type_id === roomTypeId);
  }

  onBasicDiscountChange(): void {
    if (this.discountMode === 'same') {
      const baseDiscount = this.form.get('discount_percent')?.value || 0;
      this.selectedRoomTypes.forEach((rt) => {
        rt.discount_percent = baseDiscount;
      });
    }
  }

  validateForm(): boolean {
    if (!this.form.valid) {
      this.error = 'Please fill in all required fields correctly';
      return false;
    }

    if (this.selectedRoomTypes.length === 0) {
      this.error = 'Please add at least one room type';
      return false;
    }

    const validFrom = new Date(this.form.get('valid_from')?.value);
    const validTo = new Date(this.form.get('valid_to')?.value);
    if (validTo <= validFrom) {
      this.error = 'End date must be after start date';
      return false;
    }

    return true;
  }

  onSubmit(): void {
    if (!this.validateForm()) return;

    const formData = this.form.value;
    const payload = {
      offer_name: formData.offer_name,
      description: formData.description,
      discount_percent: formData.discount_percent,
      room_types: this.selectedRoomTypes.map((rt) => ({
        room_type_id: rt.room_type_id,
        available_count: rt.selected_count,
        discount_percent: rt.discount_percent,
      })),
      valid_from: formData.valid_from,
      valid_to: formData.valid_to,
      max_uses: formData.max_uses || null,
      is_active: true,
    };

    this.loading = true;
    this.offerService.updateOffer(this.offerId!, payload).pipe(takeUntil(this.destroy$)).subscribe({
      next: async () => {
        // If image file is selected, upload it after offer update
        if (this.imageFile) {
          this.offerService
            .uploadOfferImage(this.offerId!, this.imageFile)
            .pipe(takeUntil(this.destroy$))
            .subscribe({
              next: () => {
                this.successMessage = 'Offer updated and image uploaded successfully';
                this.loading = false;
                setTimeout(() => this.router.navigate(['admin/offers']), 1500);
              },
              error: (err) => {
                this.successMessage = 'Offer updated but image upload failed';
                this.loading = false;
                setTimeout(() => this.router.navigate(['admin/offers']), 1500);
              },
            });
        } else if (this.imageFiles.length > 0) {
          // Upload new multiple images
          await this.uploadNewImages();
          this.loading = false;
          setTimeout(() => this.router.navigate(['admin/offers']), 1500);
        } else {
          this.successMessage = 'Offer updated successfully';
          this.loading = false;
          setTimeout(() => this.router.navigate(['admin/offers']), 1500);
        }
      },
      error: (err) => {
        this.error = err.error?.message || 'Failed to update offer';
        this.loading = false;
      },
    });
  }

  private allSame(arr: any[]): boolean {
    return arr.every((val) => val === arr[0]);
  }

  onImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (files && files.length > 0) {
      this.imageFile = files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imagePreviewUrl = e.target?.result as string;
      };
      reader.readAsDataURL(this.imageFile);
    }
  }

  loadExistingImages(): void {
    if (!this.offerId) return;
    this.offerService
      .getOfferImages(this.offerId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (images) => {
          this.existingImages = images || [];
        },
        error: (err) => {
          console.error('Failed to load existing images', err);
          this.existingImages = [];
        },
      });
  }

  deleteExistingImage(imageId: number, index: number): void {
    if (!this.offerId) return;
    this.offerService
      .deleteOfferImage(imageId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.existingImages.splice(index, 1);
          this.successMessage = 'Image deleted successfully';
          setTimeout(() => (this.successMessage = ''), 2000);
        },
        error: (err: any) => {
          this.error = 'Failed to delete image';
        },
      });
  }

  setImageAsPrimary(imageId: number): void {
    if (!this.offerId) return;
    this.offerService
      .setOfferImageAsPrimary(this.offerId, imageId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.existingImages.forEach((img) => {
            img.is_primary = img.image_id === imageId;
          });
          this.successMessage = 'Primary image updated';
          setTimeout(() => (this.successMessage = ''), 2000);
        },
        error: (err: any) => {
          this.error = 'Failed to set primary image';
        },
      });
  }

  removePreviewImage(): void {
    this.imageFile = null;
    this.imagePreviewUrl = null;
  }

  onMultipleImagesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (files) {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('image/')) {
          this.imageFiles.push(file);
          const reader = new FileReader();
          reader.onload = (e) => {
            this.imagePreviews.push(e.target?.result as string);
          };
          reader.readAsDataURL(file);
        }
      }
    }
  }

  removeImagePreview(index: number): void {
    this.imageFiles.splice(index, 1);
    this.imagePreviews.splice(index, 1);
    if (this.primaryImageIndex === index) {
      this.primaryImageIndex = -1;
    } else if (this.primaryImageIndex > index) {
      this.primaryImageIndex--;
    }
  }

  setImageAsPrimaryNew(index: number): void {
    this.primaryImageIndex = this.primaryImageIndex === index ? -1 : index;
  }

  async uploadNewImages(): Promise<void> {
    if (this.imageFiles.length === 0) return;

    this.uploadingImages = true;
    const primaryIndex = this.primaryImageIndex === -1 ? 0 : this.primaryImageIndex;

    try {
      const response = await new Promise<any>((resolve, reject) => {
        this.offerService
          .bulkUploadOfferImages(this.offerId!, this.imageFiles, primaryIndex)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: (result) => resolve(result),
            error: (err) => reject(err),
          });
      });

      this.uploadingImages = false;
      this.successMessage = `${this.imageFiles.length} image(s) uploaded successfully`;
      this.imageFiles = [];
      this.imagePreviews = [];
      this.primaryImageIndex = -1;
      this.loadExistingImages();
    } catch (err) {
      console.error('Failed to upload images:', err);
      this.error = 'Failed to upload images';
      this.uploadingImages = false;
    }
  }

  cancel(): void {
    this.router.navigate(['admin/offers']);
  }
}
