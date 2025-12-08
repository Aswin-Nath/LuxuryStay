import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoomsService } from '../../../../shared/services/rooms.service';

@Component({
  selector: 'app-add-amenity',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-amenity.html',
  styleUrl: './add-amenity.css',
})
export class AddAmenityComponent {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  amenityName: string = '';
  isSaving = false;
  error: string | null = null;
  success: string | null = null;

  constructor(private roomsService: RoomsService) {}

  saveAmenity(): void {
    if (!this.amenityName.trim()) {
      this.error = 'Amenity name is required';
      return;
    }

    this.isSaving = true;
    this.error = null;
    this.success = null;

    const payload = { amenity_name: this.amenityName };

    this.roomsService.createAmenity(payload).subscribe(
      (response) => {
        this.success = 'Amenity created successfully';
        this.isSaving = false;
        setTimeout(() => {
          this.saved.emit();
          this.closeModal();
        }, 1000);
      },
      (error) => {
        this.error = error.error?.detail || 'Failed to create amenity';
        this.isSaving = false;
      }
    );
  }

  closeModal(): void {
    this.close.emit();
    this.amenityName = '';
    this.error = null;
    this.success = null;
  }
}
