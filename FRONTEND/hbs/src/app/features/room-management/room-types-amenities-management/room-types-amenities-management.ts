import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { RoomsService } from '../../../core/services/rooms/rooms.service';
import { AdminNavbarComponent } from '../../../core/components/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../core/components/admin-sidebar/admin-sidebar.component';
import { EditRoomComponent } from '../edit-room/edit-room';
import { EditAmenityComponent } from '../edit-amenity/edit-amenity';
import { AddAmenityComponent } from '../add-amenity/add-amenity';
import { AddRoomComponent } from '../add-room/add-room';
import { AddRoomTypeComponent } from '../add-room-type/add-room-type';

@Component({
  selector: 'app-room-types-amenities-management',
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent, EditRoomComponent, EditAmenityComponent, AddAmenityComponent, AddRoomComponent, AddRoomTypeComponent],
  templateUrl: './room-types-amenities-management.html',
  styleUrl: './room-types-amenities-management.css',
  providers: [RoomsService]
})
export class RoomTypesAmenitiesManagementComponent implements OnInit {
  activeTab: 'room-types' | 'amenities' = 'room-types';
  
  // Room Types
  roomTypes: any[] = [];
  loadingRoomTypes = false;
  errorRoomTypes: string | null = null;
  roomTypeKpis = {
    totalTypes: 0,
    activeRooms: 0,
    frozenRooms: 0,
    availableRooms: 0,
    totalRevenue: 0
  };
  
  // Amenities
  amenities: any[] = [];
  loadingAmenities = false;
  errorAmenities: string | null = null;
  selectedAmenityForRooms: any = null;
  amenityRooms: any[] = [];

  // Modal states
  showEditRoomModal = false;
  editingRoomId: number | null = null;
  showEditAmenityModal = false;
  editingAmenityId: number | null = null;
  editingAmenityName: string = '';
  showAddAmenityModal = false;
  showAddRoomModal = false;
  showAddRoomTypeModal = false;

  constructor(private roomsService: RoomsService, private router: Router) {}

  ngOnInit(): void {
    this.loadRoomTypes();
    this.loadAmenities();
    this.calculateRoomTypeKpis();
  }

  setActiveTab(tab: 'room-types' | 'amenities'): void {
    this.activeTab = tab;
  }

  isActiveTab(tab: string): boolean {
    return this.activeTab === tab;
  }

  loadRoomTypes(): void {
    this.loadingRoomTypes = true;
    this.roomsService.getRoomTypesWithStats().subscribe(
      (data) => {
        this.roomTypes = data;
        this.loadingRoomTypes = false;
      },
      (error) => {
        this.errorRoomTypes = 'Failed to load room types';
        this.loadingRoomTypes = false;
      }
    );
  }

  loadAmenities(): void {
    this.loadingAmenities = true;
    this.roomsService.getAmenitiesWithRoomCount().subscribe(
      (data) => {
        this.amenities = data;
        this.loadingAmenities = false;
      },
      (error) => {
        this.errorAmenities = 'Failed to load amenities';
        this.loadingAmenities = false;
      }
    );
  }

  calculateRoomTypeKpis(): void {
    this.roomsService.getRoomKpis().subscribe(
      (data) => {
        this.roomTypeKpis = {
          totalTypes: data.total_types || 0,
          activeRooms: data.active_rooms || 0,
          frozenRooms: data.frozen_rooms || 0,
          availableRooms: data.available_rooms || 0,
          totalRevenue: data.total_revenue || 0
        };
      },
      (error) => {
        console.error('Failed to load KPIs', error);
      }
    );
  }

  showAmenityRooms(amenity: any): void {
    this.selectedAmenityForRooms = amenity;
    this.roomsService.getRoomsForAmenity(amenity.amenity_id).subscribe(
      (rooms) => {
        this.amenityRooms = rooms;
      },
      (error) => {
        console.error('Failed to load rooms for amenity', error);
        this.amenityRooms = [];
      }
    );
  }

  closeAmenityRooms(): void {
    this.selectedAmenityForRooms = null;
    this.amenityRooms = [];
  }

  unmapAmenity(amenityId: number, roomId: number): void {
    if (confirm('Are you sure you want to unmap this amenity from this room?')) {
      this.roomsService.unmapAmenity(roomId, amenityId).subscribe(
        () => {
          // Remove the room from the list
          this.amenityRooms = this.amenityRooms.filter(r => r.room_id !== roomId);
          // Update the room count
          if (this.selectedAmenityForRooms) {
            this.selectedAmenityForRooms.roomCount = this.amenityRooms.length;
          }
        },
        (error: any) => {
          console.error('Failed to unmap amenity', error);
          alert('Failed to unmap amenity');
        }
      );
    }
  }

  deleteAmenity(amenityId: number): void {
    if (confirm('Are you sure you want to delete this amenity? It will be unmapped from all rooms.')) {
      this.roomsService.deleteAmenity(amenityId).subscribe(
        () => {
          // Reload amenities
          this.loadAmenities();
          this.closeAmenityRooms();
        },
        (error: any) => {
          console.error('Failed to delete amenity', error);
          alert('Failed to delete amenity');
        }
      );
    }
  }

  // Edit room modal handlers
  openEditRoomModal(roomId: number): void {
    this.editingRoomId = roomId;
    this.showEditRoomModal = true;
  }

  closeEditRoomModal(): void {
    this.showEditRoomModal = false;
    this.editingRoomId = null;
  }

  onRoomSaved(): void {
    this.closeEditRoomModal();
    // Reload amenity rooms if viewing them
    if (this.selectedAmenityForRooms) {
      this.showAmenityRooms(this.selectedAmenityForRooms);
    }
  }

  // Edit amenity modal handlers
  openEditAmenityModal(amenity: any): void {
    this.editingAmenityId = amenity.amenity_id;
    this.editingAmenityName = amenity.amenity_name;
    this.showEditAmenityModal = true;
  }

  closeEditAmenityModal(): void {
    this.showEditAmenityModal = false;
    this.editingAmenityId = null;
    this.editingAmenityName = '';
  }

  onAmenitySaved(): void {
    this.closeEditAmenityModal();
    this.loadAmenities();
  }

  // Navigate to edit room type
  viewRoomType(roomTypeId: number): void {
    this.router.navigate(['/admin/room-type', roomTypeId, 'view']);
  }

  // Navigate to edit room type
  editRoomType(roomTypeId: number): void {
    this.router.navigate(['/admin/edit-room-type', roomTypeId]);
  }

  // Open edit room modal from amenity rooms list
  openEditRoomFromAmenity(room: any): void {
    this.editingRoomId = room.room_id;
    this.showEditRoomModal = true;
  }

  // Add amenity modal handlers
  openAddAmenityModal(): void {
    this.showAddAmenityModal = true;
  }

  closeAddAmenityModal(): void {
    this.showAddAmenityModal = false;
  }

  onAddAmenitySaved(): void {
    this.closeAddAmenityModal();
    this.loadAmenities();
  }

  // Add room modal handlers
  openAddRoomModal(): void {
    this.showAddRoomModal = true;
  }

  closeAddRoomModal(): void {
    this.showAddRoomModal = false;
  }

  onAddRoomSaved(): void {
    this.closeAddRoomModal();
    // Reload amenity rooms if viewing them
    if (this.selectedAmenityForRooms) {
      this.showAmenityRooms(this.selectedAmenityForRooms);
    }
  }

  // Add room type modal handlers
  openAddRoomTypeModal(): void {
    this.showAddRoomTypeModal = true;
  }

  closeAddRoomTypeModal(): void {
    this.showAddRoomTypeModal = false;
  }

  onAddRoomTypeSaved(): void {
    this.closeAddRoomTypeModal();
    this.loadRoomTypes();
  }
}
