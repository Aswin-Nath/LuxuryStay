import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RoomsService, Room } from '../../../../services/room-management.service';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';
import { SpinnerComponent } from '../../../../shared/components/spinner/spinner.component';
import { EditRoomComponent } from '../edit-room/edit-room';

@Component({
  selector: 'app-individual-room',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent, SpinnerComponent, EditRoomComponent],
  templateUrl: './individual-room.html',
  styleUrl: './individual-room.css',
})
export class IndividualRoomComponent implements OnInit {
  room: Room | null = null;
  roomDetails: any = null;
  loading = false;
  error: string | null = null;
  showFreezeModal = false;
  freezeReason = '';
  freezing = false;
  showEditRoomModal = false;

  constructor(
    private roomsService: RoomsService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadRoom();
  }

  loadRoom(): void {
    this.route.params.subscribe(params => {
      const roomId = params['id'];
      if (roomId) {
        this.loading = true;
        // Fetch individual room using room_id query parameter
        this.roomsService.getRooms({ skip: 0, limit: 100, room_id: parseInt(roomId) }).subscribe({
          next: (response: any) => {
            // Backend returns a Room object directly when room_id is specified
            this.room = response.data ? response.data[0] : response;
            if (this.room) {
              this.loadRoomDetails();
            } else {
              this.error = 'Room not found';
            }
            this.loading = false;
          },
          error: (err: any) => {
            this.error = 'Failed to load room';
            this.loading = false;
          }
        });
      }
    });
  }

  loadRoomDetails(): void {
    if (this.room) {
      this.roomDetails = {
        ...this.room,
        statusColor: this.getStatusColor(this.room.room_status),
        statusIcon: this.getStatusIcon(this.room.room_status),
      };
    }
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'AVAILABLE': 'bg-green-100 text-green-700',
      'BOOKED': 'bg-yellow-100 text-yellow-700',
      'MAINTENANCE': 'bg-red-100 text-red-700',
      'FROZEN': 'bg-purple-100 text-purple-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  }

  getStatusIcon(status: string): string {
    const icons: { [key: string]: string } = {
      'AVAILABLE': 'check_circle',
      'BOOKED': 'event_busy',
      'MAINTENANCE': 'build',
      'FROZEN': 'lock'
    };
    return icons[status] || 'info';
  }

  isRoomFrozen(): boolean {
    return this.room?.room_status === 'FROZEN';
  }

  onEdit(): void {
    if (this.room) {
      this.showEditRoomModal = true;
    }
  }

  closeEditRoomModal(): void {
    this.showEditRoomModal = false;
  }

  onEditRoomSaved(): void {
    this.showEditRoomModal = false;
    this.loadRoom();
  }

  onFreeze(): void {
    this.showFreezeModal = true;
  }

  closeFreezeModal(): void {
    this.showFreezeModal = false;
    this.freezeReason = '';
  }

  goBack(): void {
    this.router.navigate(['/admin/rooms']);
  }

  submitFreeze(): void {
    if (!this.room) return;
    
    this.freezing = true;
    if (this.isRoomFrozen()) {
      this.roomsService.unfreezeRoom(this.room.room_id).subscribe({
        next: () => {
          this.freezing = false;
          this.closeFreezeModal();
          this.loadRoom();
        },
        error: (err) => {
          console.error('Error unfreezing room:', err);
          this.freezing = false;
        }
      });
    } else {
      this.roomsService.freezeRoom(this.room.room_id, this.freezeReason).subscribe({
        next: () => {
          this.freezing = false;
          this.closeFreezeModal();
          this.loadRoom();
        },
        error: (err) => {
          console.error('Error freezing room:', err);
          this.freezing = false;
        }
      });
    }
  }
}
