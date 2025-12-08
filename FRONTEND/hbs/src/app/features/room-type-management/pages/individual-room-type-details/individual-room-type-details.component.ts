import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { RoomsService } from '../../../core/services/rooms/rooms.service';
import { AdminNavbarComponent } from '../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../layout/Admin/admin-sidebar/admin-sidebar.component';
import { SpinnerComponent } from '../../../shared/components/spinner/spinner.component';

@Component({
  selector: 'app-view-room-type',
  standalone: true,
  imports: [CommonModule, AdminNavbarComponent, AdminSidebarComponent, SpinnerComponent],
  templateUrl: './view-room-type.html',
  styleUrl: './view-room-type.css',
})
export class ViewRoomTypeComponent implements OnInit {
  roomTypeId: number | null = null;
  roomType: any = null;
  loading = false;
  error: string | null = null;
  
  // Images
  images: any[] = [];
  loadingImages = false;

  // Amenities
  amenities: any[] = [];
  
  // Room stats
  roomStats = {
    totalRooms: 0,
    availableRooms: 0,
    bookedRooms: 0,
    frozenRooms: 0,
    maintenanceRooms: 0
  };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private roomsService: RoomsService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      console.log('Route params:', params);
      if (params['id']) {
        this.roomTypeId = parseInt(params['id'], 10);
        console.log('Room Type ID extracted:', this.roomTypeId);
        this.loadRoomTypeDetails();
      }
    });
  }

  loadRoomTypeDetails(): void {
    if (!this.roomTypeId) return;
    this.loading = true;

    // Load basic room type details
    this.roomsService.getRoomType(this.roomTypeId).subscribe(
      (data) => {
        this.roomType = data;
        
        // Load images
        this.loadImages();
        
        // Load amenities for this room type (NEW ENDPOINT)
        this.loadAmenitiesForRoomType();
        
        // Load room type with stats to get the counts
        this.loadRoomTypeStats();
        
        this.loading = false;
      },
      (error) => {
        this.error = 'Failed to load room type details';
        this.loading = false;
      }
    );
  }

  loadAmenitiesForRoomType(): void {
    if (!this.roomTypeId) return;
    
    this.roomsService.getAmenitiesForRoomType(this.roomTypeId).subscribe(
      (response: any) => {
        // Response contains { room_type_id, amenities: [...] }
        this.amenities = response.amenities || [];
      },
      (error) => {
        console.error('Failed to load amenities for room type', error);
        this.amenities = [];
      }
    );
  }

  loadRoomTypeStats(): void {
    if (!this.roomTypeId) {
      console.error('Room Type ID is null or undefined');
      return;
    }
    
    console.log('=== LOADING STATS FOR ROOM TYPE ID:', this.roomTypeId);
    
    // Use the SAME API as the table - getRoomTypesWithStats
    this.roomsService.getRoomTypesWithStats().subscribe(
      (data: any[]) => {
        console.log('=== API RESPONSE from getRoomTypesWithStats:', data);
        
        // Find the matching room type
        const roomTypeWithStats = data.find(rt => {
          console.log('Comparing: rt.room_type_id =', rt.room_type_id, 'vs this.roomTypeId =', this.roomTypeId);
          return rt.room_type_id === this.roomTypeId;
        });
        console.log('=== FOUND ROOM TYPE WITH STATS:', roomTypeWithStats);
        
        if (roomTypeWithStats) {
          this.roomStats = {
            totalRooms: roomTypeWithStats.totalCount || 0,
            availableRooms: roomTypeWithStats.availableCount || 0,
            bookedRooms: roomTypeWithStats.bookedCount || 0,
            frozenRooms: roomTypeWithStats.frozenCount || 0,
            maintenanceRooms: roomTypeWithStats.maintenanceCount || 0
          };
          console.log('=== UPDATED ROOM STATS:', this.roomStats);
        } else {
          console.warn('=== ROOM TYPE NOT FOUND IN STATS DATA for ID:', this.roomTypeId);
          console.log('=== ALL ROOM TYPE IDs IN RESPONSE:', data.map(rt => rt.room_type_id));
        }
      },
      (error) => {
        console.error('=== FAILED TO LOAD ROOM TYPE STATS:', error);
      }
    );
  }

  loadImages(): void {
    if (!this.roomTypeId) return;
    this.loadingImages = true;

    this.roomsService.getRoomTypeImages(this.roomTypeId).subscribe(
      (data) => {
        this.images = data || [];
        this.loadingImages = false;
      },
      (error) => {
        console.error('Failed to load images', error);
        this.loadingImages = false;
      }
    );
  }

  goBack(): void {
    this.router.navigate(['/admin/room-types-amenities']);
  }

  editRoomType(): void {
    if (this.roomTypeId) {
      this.router.navigate(['/admin/edit-room-type', this.roomTypeId]);
    }
  }

  getStatusColor(status: string): string {
    switch (status?.toUpperCase()) {
      case 'AVAILABLE':
        return 'bg-green-100 text-green-700';
      case 'BOOKED':
        return 'bg-blue-100 text-blue-700';
      case 'MAINTENANCE':
        return 'bg-yellow-100 text-yellow-700';
      case 'FROZEN':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  }
}
