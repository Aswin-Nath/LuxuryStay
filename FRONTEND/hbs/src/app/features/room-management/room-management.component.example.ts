import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BulkUploadComponent } from './bulk-upload/bulk-upload.component';
import { HttpClient } from '@angular/common/http';

interface Room {
  id: number;
  room_no: string;
  room_type_id: number;
  room_type_name: string;
  room_status: 'AVAILABLE' | 'BOOKED' | 'MAINTENANCE' | 'FROZEN' | 'HELD';
  freeze_reason?: string;
}

@Component({
  selector: 'app-room-management',
  standalone: true,
  imports: [
    CommonModule  ],
  template: `<!-- See room-management.component.template.html for template -->`,
  styles: []
})
export class RoomManagementComponent implements OnInit {
  
  rooms: Room[] = [];
  filteredRooms: Room[] = [];
  currentPage = 1;
  rowsPerPage = 10;
  totalPages = 1;
  
  // Filter states
  filterStatus = 'All';
  filterType = 'All';
  filterCheckIn = '';
  filterCheckOut = '';

  loading = false;
  error: string | null = null;

  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/api';

  constructor() {}

  ngOnInit(): void {
    this.loadRooms();
  }

  /**
   * Load all rooms from backend
   */
  loadRooms(): void {
    this.loading = true;
    this.error = null;

    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    this.http.get<any>(`${this.apiUrl}/rooms`, { headers }).subscribe({
      next: (response: any) => {
        this.rooms = response.data || response;
        this.filteredRooms = this.rooms;
        this.totalPages = Math.ceil(this.filteredRooms.length / this.rowsPerPage);
        this.currentPage = 1;
        this.loading = false;
      },
      error: (err: any) => {
        this.error = 'Failed to load rooms';
        this.showToast('Failed to load rooms', 'error');
        this.loading = false;
      }
    });
  }

  /**
   * Show toast notification
   */
  private showToast(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'success'): void {
    const toast = document.getElementById('toast');
    if (toast) {
      const toastMsg = document.getElementById('toastMessage');
      if (toastMsg) {
        toastMsg.textContent = message;
      }
      
      toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2`;
      
      if (type === 'success') {
        toast.classList.add('bg-green-500', 'text-white');
      } else if (type === 'error') {
        toast.classList.add('bg-red-500', 'text-white');
      } else if (type === 'warning') {
        toast.classList.add('bg-orange-500', 'text-white');
      } else if (type === 'info') {
        toast.classList.add('bg-blue-500', 'text-white');
      }
      
      toast.classList.remove('hidden');
      
      setTimeout(() => {
        toast.classList.add('hidden');
      }, 3000);
    }
  }

  /**
   * Open bulk upload modal
   */
  openBulkUploadModal(): void {
    const modal = document.getElementById('bulkUploadModal');
    if (modal) {
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
    }
  }

  /**
   * Refresh rooms after bulk upload (called from BulkUploadComponent)
   */
  onBulkUploadComplete(): void {
    this.loadRooms();
    this.showToast('Rooms uploaded successfully', 'success');
  }

  /**
   * Apply filters
   */
  applyFilters(): void {
    this.filteredRooms = this.rooms.filter(room => {
      const statusMatch = this.filterStatus === 'All' || room.room_status === this.filterStatus;
      const typeMatch = this.filterType === 'All' || room.room_type_name === this.filterType;
      
      return statusMatch && typeMatch;
    });

    this.totalPages = Math.ceil(this.filteredRooms.length / this.rowsPerPage);
    this.currentPage = 1;
  }

  /**
   * Reset all filters
   */
  resetFilters(): void {
    this.filterStatus = 'All';
    this.filterType = 'All';
    this.filterCheckIn = '';
    this.filterCheckOut = '';
    this.filteredRooms = this.rooms;
    this.totalPages = Math.ceil(this.filteredRooms.length / this.rowsPerPage);
    this.currentPage = 1;
    this.showToast('Filters reset', 'info');
  }

  /**
   * Get paginated rooms
   */
  getPaginatedRooms(): Room[] {
    const start = (this.currentPage - 1) * this.rowsPerPage;
    const end = start + this.rowsPerPage;
    return this.filteredRooms.slice(start, end);
  }

  /**
   * Navigate pages
   */
  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  jumpToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  /**
   * Get status badge CSS
   */
  getStatusBadge(status: string): string {
    switch (status) {
      case 'AVAILABLE':
        return 'bg-green-100 text-green-700';
      case 'BOOKED':
        return 'bg-yellow-100 text-yellow-700';
      case 'MAINTENANCE':
        return 'bg-red-100 text-red-700';
      case 'FROZEN':
        return 'bg-purple-100 text-purple-700';
      case 'HELD':
        return 'bg-blue-100 text-blue-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  }

  /**
   * Get status icon
   */
  getStatusIcon(status: string): string {
    switch (status) {
      case 'AVAILABLE':
        return 'check_circle';
      case 'BOOKED':
        return 'person';
      case 'MAINTENANCE':
        return 'handyman';
      case 'FROZEN':
        return 'lock';
      case 'HELD':
        return 'schedule';
      default:
        return 'help';
    }
  }

  /**
   * View room details
   */
  viewRoom(room: Room): void {
    // Navigate to room details page
    localStorage.setItem('selectedRoomId', String(room.id));
    window.location.href = '/rooms/' + room.id;
  }

  /**
   * Edit room
   */
  editRoom(room: Room): void {
    localStorage.setItem('selectedRoomId', String(room.id));
    window.location.href = '/rooms/' + room.id + '/edit';
  }

  /**
   * Freeze/unfreeze room
   */
  toggleFreeze(room: Room): void {
    const action = room.room_status === 'FROZEN' ? 'unfreeze' : 'freeze';
    
    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const updateData = {
      room_status: room.room_status === 'FROZEN' ? 'AVAILABLE' : 'FROZEN',
      freeze_reason: room.room_status === 'FROZEN' ? 'NONE' : 'ADMIN_LOCK'
    };

    this.http.put<any>(`${this.apiUrl}/rooms/${room.id}`, updateData, { headers }).subscribe({
      next: () => {
        this.showToast(`Room ${action}d successfully`, 'success');
        this.loadRooms();
      },
      error: (err: any) => {
        this.showToast(`Failed to ${action} room`, 'error');
      }
    });
  }

  /**
   * Delete room
   */
  deleteRoom(room: Room): void {
    if (!confirm(`Are you sure you want to delete room ${room.room_no}?`)) {
      return;
    }

    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    this.http.delete<any>(`${this.apiUrl}/rooms/${room.id}`, { headers }).subscribe({
      next: () => {
        this.showToast('Room deleted successfully', 'success');
        this.loadRooms();
      },
      error: (err: any) => {
        this.showToast('Failed to delete room', 'error');
      }
    });
  }

  /**
   * Get page numbers for pagination display
   */
  getPageNumbers(): number[] {
    const pages = [];
    for (let i = 1; i <= this.totalPages; i++) {
      pages.push(i);
    }
    return pages;
  }
}
