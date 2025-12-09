import {
  Component,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { OfferService } from '../../../../services/offer.service';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';

interface RoomTypeSelection {
  room_type_id: number;
  room_type_name: string;
  total_available: number;
  selected_count: number;
  discount_percent: number;
}

const MAX_ROOMS_PER_OFFER = 5;

@Component({
  selector: 'app-create-offer',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './create-offer.component.html',
  styleUrl: './create-offer.component.css',
})
export class CreateOfferComponent implements OnInit, OnDestroy {
  form!: FormGroup;
  roomTypes: any[] = [];
  selectedRoomTypes: RoomTypeSelection[] = [];
  discountMode: 'same' | 'per-room' = 'same';
  loading = false;
  error = '';
  successMessage = '';

  // Image upload properties
  imageFiles: File[] = [];
  imagePreviews: string[] = [];
  primaryImageIndex: number | null = null;
  uploadingImages = false;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private offerService: OfferService,
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
    this.loadRoomTypes();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomTypes(): void {
    this.loading = true;
    this.offerService
      .getRoomTypesWithCounts()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (types) => {
          this.roomTypes = types;
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Failed to load room types';
          console.error(err);
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
      room_type_name: roomType.type_name,
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

  // ============================================================
  // IMAGE UPLOAD METHODS
  // ============================================================

  onImageSelected(event: any): void {
    const files = event.target.files;
    if (files) {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('image/')) {
          this.imageFiles.push(file);
          
          // Create preview
          const reader = new FileReader();
          reader.onload = (e: any) => {
            this.imagePreviews.push(e.target.result);
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
      this.primaryImageIndex = null;
    } else if (this.primaryImageIndex !== null && this.primaryImageIndex > index) {
      this.primaryImageIndex--;
    }
  }

  setImageAsPrimary(index: number): void {
    this.primaryImageIndex = this.primaryImageIndex === index ? null : index;
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
    this.offerService.createOffer(payload).pipe(takeUntil(this.destroy$)).subscribe({
      next: (response) => {
        const offerId = response.offer_id;
        
        // Upload images if any
        if (this.imageFiles.length > 0) {
          this.uploadImages(offerId);
        } else {
          this.successMessage = 'Offer created successfully';
          this.loading = false;
          setTimeout(() => this.router.navigate(['admin/offers']), 1500);
        }
      },
      error: (err) => {
        this.error = err.error?.message || 'Failed to create offer';
        this.loading = false;
      },
    });
  }

  uploadImages(offerId: number): void {
    this.uploadingImages = true;
    
    // Determine primary image: either selected one or first image
    const primaryIndex = this.primaryImageIndex !== null ? this.primaryImageIndex : 0;
    
    let uploadedCount = 0;
    this.imageFiles.forEach((file, index) => {
      const isPrimary = index === primaryIndex;
      
      this.offerService.uploadOfferImage(offerId, file, isPrimary).pipe(takeUntil(this.destroy$)).subscribe({
        next: () => {
          uploadedCount++;
          if (uploadedCount === this.imageFiles.length) {
            this.successMessage = 'Offer created successfully with images!';
            this.uploadingImages = false;
            this.loading = false;
            setTimeout(() => this.router.navigate(['admin/offers']), 1500);
          }
        },
        error: (err) => {
          console.error('Failed to upload image', err);
          // Continue with other images even if one fails
          uploadedCount++;
          if (uploadedCount === this.imageFiles.length) {
            this.successMessage = 'Offer created but some images failed to upload';
            this.uploadingImages = false;
            this.loading = false;
            setTimeout(() => this.router.navigate(['admin/offers']), 1500);
          }
        },
      });
    });
  }

  private allSame(arr: any[]): boolean {
    return arr.every((val) => val === arr[0]);
  }

  cancel(): void {
    this.router.navigate(['admin/offers']);
  }
}
