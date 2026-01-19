import { Component, Input, Output, EventEmitter, OnInit, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoomsService } from '../../../../services/room-management.service';

@Component({
  selector: 'app-edit-amenity',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './edit-amenity.html',
  styleUrl: './edit-amenity.css',
})
export class EditAmenityComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() amenityId: number | null = null;
  @Input() amenityName: string = '';
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  name: string = '';
  isSaving = false;
  error: string | null = null;

  constructor(private roomsService: RoomsService) {}

  ngOnInit(): void {}

  ngOnChanges(): void {
    if (this.isOpen && this.amenityId) {
      this.name = this.amenityName;
    }
  }

  saveChanges(): void {
    if (!this.amenityId || !this.name.trim()) {
      this.error = 'Amenity name is required';
      return;
    }

    this.isSaving = true;
    const payload = { amenity_name: this.name };

    this.roomsService.updateAmenity(this.amenityId, payload).subscribe(
      (response) => {
        this.isSaving = false;
        this.saved.emit();
        this.closeModal();
      },
      (error) => {
        this.error = 'Failed to update amenity';
        this.isSaving = false;
      }
    );
  }

  closeModal(): void {
    this.close.emit();
    this.name = '';
    this.error = null;
  }
}
