import { Component, Input, Output, EventEmitter, OnInit, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Room, RoomType, RoomsService } from '../../../../../shared/services/rooms.service';

@Component({
  selector: 'app-edit-room',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './edit-room.html',
  styleUrl: './edit-room.css',
})
export class EditRoomComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() roomId: number | null = null;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  room: Room | null = null;
  roomTypes: RoomType[] = [];
  
  roomNo: string = '';
  selectedRoomTypeId: number | null = null;

  isSaving = false;
  loading = false;
  error: string | null = null;

  constructor(private roomsService: RoomsService) {}

  ngOnInit(): void {
    this.loadRoomTypes();
  }

  ngOnChanges(): void {
    if (this.isOpen && this.roomId) {
      this.loadRoom();
    }
  }

  loadRoom(): void {
    if (!this.roomId) return;
    this.loading = true;
    this.roomsService.getRoom(this.roomId).subscribe(
      (data: any) => {
        this.room = data;
        this.roomNo = data.room_no;
        this.selectedRoomTypeId = data.room_type_id;
        this.loading = false;
      },
      (error) => {
        this.error = 'Failed to load room';
        this.loading = false;
      }
    );
  }

  loadRoomTypes(): void {
    this.roomsService.getRoomTypes().subscribe(
      (data) => {
        this.roomTypes = data;
      },
      (error) => {
        console.error('Failed to load room types', error);
      }
    );
  }

  saveChanges(): void {
    if (!this.roomId) return;

    this.isSaving = true;
    const payload = {
      room_no: this.roomNo,
      room_type_id: this.selectedRoomTypeId
    };

    this.roomsService.updateRoom(this.roomId, payload).subscribe(
      (response) => {
        this.isSaving = false;
        this.saved.emit();
        this.closeModal();
      },
      (error) => {
        this.error = 'Failed to update room';
        this.isSaving = false;
      }
    );
  }

  closeModal(): void {
    this.close.emit();
    this.roomNo = '';
    this.selectedRoomTypeId = null;
    this.error = null;
    this.room = null;
  }
}
