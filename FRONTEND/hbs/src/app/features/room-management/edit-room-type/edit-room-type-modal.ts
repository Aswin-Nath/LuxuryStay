import { Component, Input, Output, EventEmitter, OnInit, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RoomsService, RoomType } from '../../../core/services/rooms/rooms.service';

@Component({
  selector: 'app-edit-room-type-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './edit-room-type-modal.html',
  styleUrl: './edit-room-type-modal.css',
})
export class EditRoomTypeModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() roomTypeId: number | null = null;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  roomType: RoomType | null = null;
  
  // Form fields
  typeName: string = '';
  price: number | null = null;
  maxAdults: number | null = null;
  maxChildren: number | null = null;
  squareFt: number | null = null;

  isSaving = false;
  loading = false;
  error: string | null = null;

  constructor(private roomsService: RoomsService) {}

  ngOnInit(): void {
    // Component initialization
  }

  ngOnChanges(): void {
    if (this.isOpen && this.roomTypeId) {
      this.loadRoomType();
    }
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
        this.squareFt = data.square_ft;
        this.loading = false;
      },
      (error) => {
        this.error = 'Failed to load room type';
        this.loading = false;
      }
    );
  }

  saveChanges(): void {
    if (!this.roomTypeId) return;

    this.isSaving = true;
    const payload = {
      type_name: this.typeName,
      price_per_night: this.price,
      max_adult_count: this.maxAdults,
      max_child_count: this.maxChildren,
      square_ft: this.squareFt
    };

    this.roomsService.updateRoomType(this.roomTypeId, payload).subscribe(
      (response) => {
        this.isSaving = false;
        this.saved.emit();
        this.closeModal();
      },
      (error) => {
        this.error = 'Failed to update room type';
        this.isSaving = false;
      }
    );
  }

  closeModal(): void {
    this.close.emit();
    this.typeName = '';
    this.price = null;
    this.maxAdults = null;
    this.maxChildren = null;
    this.squareFt = null;
    this.error = null;
    this.roomType = null;
  }
}
