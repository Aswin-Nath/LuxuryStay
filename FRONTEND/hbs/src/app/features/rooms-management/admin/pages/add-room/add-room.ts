import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
// import { RoomsService, RoomType } from '../../../core/services/rooms/rooms.service';
import { RoomsService,RoomType } from '../../../../../shared/services/rooms.service';
@Component({
  selector: 'app-add-room',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-room.html',
  styleUrl: './add-room.css',
})
export class AddRoomComponent implements OnInit {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  roomNo: string = '';
  selectedRoomTypeId: number | null = null;
  roomTypes: RoomType[] = [];
  isSaving = false;
  loading = false;
  error: string | null = null;
  success: string | null = null;

  constructor(private roomsService: RoomsService) {}

  ngOnInit(): void {
    this.loadRoomTypes();
  }

  loadRoomTypes(): void {
    this.loading = true;
    this.roomsService.getRoomTypes().subscribe(
      (data) => {
        this.roomTypes = data;
        this.loading = false;
      },
      (error) => {
        this.error = 'Failed to load room types';
        this.loading = false;
      }
    );
  }

  saveRoom(): void {
    if (!this.roomNo.trim()) {
      this.error = 'Room number is required';
      return;
    }

    if (!this.selectedRoomTypeId) {
      this.error = 'Room type is required';
      return;
    }

    this.isSaving = true;
    this.error = null;
    this.success = null;

    const payload = {
      room_no: this.roomNo,
      room_type_id: this.selectedRoomTypeId
    };

    this.roomsService.createRoom(payload).subscribe(
      (response: any) => {
        this.success = `Room ${this.roomNo} created successfully`;
        this.isSaving = false;
        setTimeout(() => {
          this.saved.emit();
          this.closeModal();
        }, 1000);
      },
      (error: any) => {
        this.error = error.error?.detail || 'Failed to create room';
        this.isSaving = false;
      }
    );
  }

  closeModal(): void {
    this.close.emit();
    this.roomNo = '';
    this.selectedRoomTypeId = null;
    this.error = null;
    this.success = null;
  }
}
