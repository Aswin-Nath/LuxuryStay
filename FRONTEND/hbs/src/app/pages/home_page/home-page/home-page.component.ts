import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RoomsService, RoomType, Room, PaginatedRoomsResponse } from '../../../core/services/rooms/rooms.service';
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
  rooms: Room[] = [];
  loading = false;
  error = '';

  constructor(private roomsService: RoomsService) {}

  fetchRoomTypes() {
    this.loading = true;
    this.error = '';
    this.roomsService.getRoomTypes().subscribe({
      next: (res: RoomType[]) => {
        this.roomTypes = res;
        this.loading = false;
      },
      error: (err: any) => {
        this.error = err?.error?.detail || err?.message || 'Failed to load room types';
        this.loading = false;
      }
    });
  }

  fetchRooms() {
    this.loading = true;
    this.error = '';
    this.roomsService.getRooms().subscribe({
      next: (res: PaginatedRoomsResponse) => {
        this.rooms = res.data;
        this.loading = false;
      },
      error: (err: any) => {
        this.error = err?.error?.detail || err?.message || 'Failed to load rooms';
        this.loading = false;
      }
    });
  }
}
