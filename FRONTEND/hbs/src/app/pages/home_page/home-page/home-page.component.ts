import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RoomsService, RoomType } from '../../../core/services/rooms/rooms.service';
import { HasPermissionDirective } from "../../../core/directives/has-permission.directive";

@Component({
  selector: 'app-home-page',
  standalone: true,
  imports: [CommonModule, HasPermissionDirective],
  templateUrl: './home-page.component.html',
  styleUrls: ['./home-page.component.css'],
})
export class HomePageComponent {
  roomTypes: RoomType[] = [];
  rooms: any[] = [];
  loading = false;
  error = '';

  constructor(private roomsService: RoomsService) {}

  fetchRoomTypes() {
    this.loading = true;
    this.error = '';
    this.roomsService.getRoomTypes(false).subscribe({
      next: (res) => {
        this.roomTypes = res;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Failed to load room types';
        this.loading = false;
      }
    });
  }

  fetchRooms() {
    this.loading = true;
    this.error = '';
    this.roomsService.getRooms().subscribe({
      next: (res) => {
        this.rooms = res;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || err?.message || 'Failed to load rooms';
        this.loading = false;
      }
    });
  }
}
