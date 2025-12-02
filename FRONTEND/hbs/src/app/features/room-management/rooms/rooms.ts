import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { RoomsService, Room, RoomType, PaginatedRoomsResponse, RoomsFilterParams } from '../../../core/services/rooms/rooms.service';
import { AdminNavbarComponent } from '../../../core/components/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../core/components/admin-sidebar/admin-sidebar.component';
import { SpinnerComponent } from '../../../core/components/spinner/spinner.component';
import { EditRoomComponent } from '../edit-room/edit-room';
import { AddRoomComponent } from '../add-room/add-room';
import { BulkUploadComponent } from '../bulk-upload/bulk-upload.component';

@Component({
  selector: 'app-rooms',
  standalone: true,
  imports: [CommonModule, HttpClientModule, RouterModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent, SpinnerComponent, EditRoomComponent, AddRoomComponent, BulkUploadComponent],
  templateUrl: './rooms.html',
  styleUrl: './rooms.css',
  providers: [RoomsService]
})
export class Rooms implements OnInit, OnDestroy {
  rooms: Room[] = [];
  filteredRooms: Room[] = [];
  roomTypes: RoomType[] = [];
  allRooms: Room[] = [];
  loading = false;
  error: string | null = null;

  // Math for template
  Math = Math;

  // Pagination properties
  currentPage: number = 1;
  pageSize: number = 10;
  totalRecords: number = 0;
  totalPages: number = 0;
  pageSizeOptions = [5, 10, 25, 50];

  // Filter properties
  minPrice: number | null = null;
  maxPrice: number | null = null;
  filterStatus: string = 'All';
  filterType: string | number = 'All';
  availableRoomTypes: string[] = [];

  // Sorting properties
  sortColumn = 'room_id';
  sortDirection: 'asc' | 'desc' = 'asc';

  // Freeze/Unfreeze Modal properties
  showFreezeModal = false;
  freezeReason: string = '';
  selectedRoomForFreeze: Room | null = null;
  freezing = false;
  
  // Edit Room Modal properties
  showEditRoomModal = false;
  editingRoomId: number | null = null;

  // Add Room Modal properties
  showAddRoomModal = false;
  
  // Bulk Upload Modal properties
  showBulkUploadModal = false;
  
  // Freeze reason options matching backend enum
  freezeReasonOptions = [
    { value: 'CLEANING', label: 'Cleaning / Maintenance' },
    { value: 'ADMIN_LOCK', label: 'Admin Lock' },
  ];

  statusOptions = ['AVAILABLE', 'BOOKED', 'MAINTENANCE', 'FROZEN'];

  // RxJS Cleanup
  private destroy$ = new Subject<void>();

  constructor(private roomsService: RoomsService, private router: Router) {}

  ngOnInit(): void {
    this.loadRoomTypes();
    this.loadRooms();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRoomTypes(): void {
    this.roomsService.getRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.roomTypes = data;
          // Extract unique room type names for the dropdown
          this.availableRoomTypes = [...new Set(data.map(rt => rt.type_name))].sort();
        },
        error: (err) => {
          console.error('Failed to load room types', err);
        }
      });
  }

  loadRooms(page: number = 1): void {
    this.loading = true;
    this.error = null;
    this.currentPage = page;

    // Calculate skip based on current page and page size
    const skip = (page - 1) * this.pageSize;

    // Build filter parameters - include all active filters
    const filters: RoomsFilterParams = {
      skip,
      limit: this.pageSize,
      sort_by: this.sortColumn,
      sort_order: this.sortDirection
    };

    // Add status filter if selected
    if (this.filterStatus && this.filterStatus !== 'All') {
      filters.status_filter = this.filterStatus;
    }

    // Add room type filter if selected
    if (this.filterType && this.filterType !== 'All') {
      filters.room_type_id = Number(this.filterType);
    }

    this.roomsService.getRooms(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: PaginatedRoomsResponse) => {
          this.rooms = response.data;
          this.totalRecords = response.total;
          this.totalPages = response.total_pages;
          this.allRooms = response.data;
          
          // Apply client-side price filters to the fetched data
          this.applyClientSideFilters();
          
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Failed to load rooms';
          this.loading = false;
          console.error(err);
        }
      });
  }

  applyFilters(): void {
    // Reset to first page when filters change
    this.currentPage = 1;
    
    // Reload rooms with new filters
    this.loadRooms(1);
  }

  applyClientSideFilters(): void {
    // Apply price filters on the current page results
    this.filteredRooms = this.allRooms.filter((room) => {
      // Filter by min price
      if (this.minPrice !== null && room.room_type.price_per_night < this.minPrice) {
        return false;
      }

      // Filter by max price
      if (this.maxPrice !== null && room.room_type.price_per_night > this.maxPrice) {
        return false;
      }

      return true;
    });

    this.rooms = this.filteredRooms;
  }

  resetFilters(): void {
    this.filterStatus = 'All';
    this.filterType = 'All';
    this.minPrice = null;
    this.maxPrice = null;
    this.filteredRooms = this.allRooms;
    this.rooms = this.allRooms;
    this.currentPage = 1;
    this.loadRooms(1);
  }

  validateMinPrice(): void {
    if (this.minPrice !== null && this.minPrice <= 0) {
      this.minPrice = null;
    }
    this.applyClientSideFilters();
  }

  validateMaxPrice(): void {
    if (this.maxPrice !== null && this.maxPrice <= 0) {
      this.maxPrice = null;
    }
    this.applyClientSideFilters();
  }

  validatePriceRange(): void {
    if (this.minPrice !== null && this.maxPrice !== null && this.minPrice > this.maxPrice) {
      // Swap them
      const temp = this.minPrice;
      this.minPrice = this.maxPrice;
      this.maxPrice = temp;
    }
    this.applyClientSideFilters();
  }

  // Pagination methods
  previousPage(): void {
    if (this.currentPage > 1) {
      this.loadRooms(this.currentPage - 1);
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.loadRooms(this.currentPage + 1);
    }
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.loadRooms(page);
    }
  }

  changePageSize(newSize: number): void {
    this.pageSize = newSize;
    this.loadRooms(1);
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const startPage = Math.max(1, this.currentPage - 2);
    const endPage = Math.min(this.totalPages, this.currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }

  /**
   * Handle sort column change
   */
  sortBy(column: string): void {
    if (this.sortColumn === column) {
      // Toggle direction if same column
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      // New column, default to ascending
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.currentPage = 1; // Reset to first page on sort
    this.loadRooms(1);
  }

  /**
   * Get sort icon for column header
   */
  getSortIcon(column: string): string {
    if (this.sortColumn !== column) return 'fa-sort';
    return this.sortDirection === 'asc' ? 'fa-sort-up' : 'fa-sort-down';
  }

  getStatusColor(status: string): string {
    const statusMap: { [key: string]: string } = {
      'AVAILABLE': 'bg-green-100 text-green-700',
      'BOOKED': 'bg-yellow-100 text-yellow-700',
      'MAINTENANCE': 'bg-red-100 text-red-700',
      'FROZEN': 'bg-purple-100 text-purple-700'
    };
    return statusMap[status] || 'bg-gray-100 text-gray-700';
  }

  getStatusIcon(status: string): string {
    const iconMap: { [key: string]: string } = {
      'AVAILABLE': 'check_circle',
      'BOOKED': 'person',
      'MAINTENANCE': 'handyman',
      'FROZEN': 'lock'
    };
    return iconMap[status] || 'info';
  }

  // Freeze/Unfreeze Modal Methods
  openFreezeModal(room: Room): void {
    this.selectedRoomForFreeze = room;
    this.freezeReason = '';
    this.showFreezeModal = true;
  }

  closeFreezeModal(): void {
    this.showFreezeModal = false;
    this.selectedRoomForFreeze = null;
    this.freezeReason = '';
  }

  submitFreeze(): void {
    if (!this.selectedRoomForFreeze) {
      console.error('No room selected for freeze');
      return;
    }
    
    const roomId = this.selectedRoomForFreeze.room_id;
    const isFrozen = this.selectedRoomForFreeze.room_status === 'FROZEN';
    
    console.log(`Attempting to ${isFrozen ? 'unfreeze' : 'freeze'} room ID: ${roomId}`);
    
    this.freezing = true;
    
    if (isFrozen) {
      // Unfreeze - call delete API (which unfreezes)
      this.roomsService.unfreezeRoom(roomId)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (response: any) => {
            console.log('Room unfrozen successfully:', response);
            this.loadRooms(this.currentPage);
            this.closeFreezeModal();
            this.freezing = false;
          },
          error: (err: any) => {
            console.error('Failed to unfreeze room', err);
            this.error = err?.error?.detail || 'Failed to unfreeze room';
            this.freezing = false;
          }
        });
    } else {
      // Freeze - call freeze API with reason
      this.roomsService.freezeRoom(roomId, this.freezeReason)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (response: any) => {
            console.log('Room frozen successfully:', response);
            this.loadRooms(this.currentPage);
            this.closeFreezeModal();
            this.freezing = false;
          },
          error: (err: any) => {
            console.error('Failed to freeze room', err);
            this.error = err?.error?.detail || 'Failed to freeze room';
            this.freezing = false;
          }
        });
    }
  }

  // Room Navigation Methods
  viewRoom(room: Room): void {
    this.router.navigate(['/admin/rooms', room.room_id, 'view']);
  }

  // Room Edit Modal Methods
  editRoom(room: Room): void {
    this.editingRoomId = room.room_id;
    this.showEditRoomModal = true;
  }

  closeEditRoomModal(): void {
    this.showEditRoomModal = false;
    this.editingRoomId = null;
  }

  onRoomSaved(updatedRoom?: Room): void {
    this.closeEditRoomModal();
    this.loadRooms(this.currentPage);
  }

  // Add Room Modal Methods
  openAddRoomModal(): void {
    this.showAddRoomModal = true;
  }

  closeAddRoomModal(): void {
    this.showAddRoomModal = false;
  }

  onAddRoomSaved(): void {
    this.closeAddRoomModal();
    this.loadRooms(1); // Reset to first page and reload
  }

  // Bulk Upload Modal Methods
  openBulkUploadModal(): void {
    this.showBulkUploadModal = true;
  }

  closeBulkUploadModal(): void {
    this.showBulkUploadModal = false;
  }

  onBulkUploadComplete(): void {
    this.closeBulkUploadModal();
    this.loadRooms(1); // Reset to first page and reload
  }

  isRoomFrozen(room: Room | null): boolean {
    if (!room) return false;
    return room.room_status === 'FROZEN';
  }
}
