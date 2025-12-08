import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';
import { AdminManagementService, AdminUser, Role } from '../../../../core/services/admin-management/admin-management.service';
// import { AdminFormModalComponent } from '../users-management/admin-form-modal.component';
import { AdminFormModalComponent } from '../admin-addition/admin-addition.component';

@Component({
  selector: 'app-admin-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, AdminNavbarComponent, AdminSidebarComponent, AdminFormModalComponent],
  templateUrl: './admins-display.html',
  styleUrls: ['./admins-display.css']
})
export class AdminManagementComponent implements OnInit {
  // Make Math available in template
  Math = Math;
  
  // Data
  admins: AdminUser[] = [];
  roles: Role[] = [];
  filteredAdmins: AdminUser[] = [];
  
  // Pagination
  currentPage = 1;
  itemsPerPage = 10;
  totalItems = 0;
  totalPages = 0;
  
  // Filtering
  searchTerm = '';
  selectedRole: number | null = null;
  selectedStatus = '';
  dateFrom = '';
  dateTo = '';
  
  // Sorting
  sortColumn = 'created_at';
  sortDirection: 'asc' | 'desc' = 'desc';
  
  // UI State
  isLoading = false;
  showCreateModal = false;
  showEditModal = false;
  showSuspendModal = false;
  selectedAdmin: AdminUser | null = null;
  suspendReason = '';
  suspendReasonError = '';
  errorMessage = '';
  successMessage = '';
  
  // Pagination options
  pageSizeOptions = [5, 10, 20, 50];

  constructor(
    private adminService: AdminManagementService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadRoles();
    this.loadAdmins();
  }

  /**
   * Load all roles for filtering
   */
  loadRoles(): void {
    this.adminService.getRoles().subscribe({
      next: (roles: Role[]) => {
        // Filter out customer role (role_id = 1)
        this.roles = roles.filter((r: Role) => r.role_id !== 1);
      },
      error: (err: any) => {
        console.error('Error loading roles:', err);
      }
    });
  }

  /**
   * Load admins with current filters and pagination
   */
  loadAdmins(): void {
    this.isLoading = true;
    this.errorMessage = '';
    
    const params = {
      page: this.currentPage,
      limit: this.itemsPerPage,
      search: this.searchTerm,
      role_id: this.selectedRole || undefined,
      status: this.selectedStatus,
      date_from: this.dateFrom,
      date_to: this.dateTo,
      sort_by: this.sortColumn,
      sort_order: this.sortDirection
    };

    this.adminService.listAdmins(params).subscribe({
      next: (response: any) => {
        this.admins = response.users;
        this.filteredAdmins = this.admins;
        this.totalItems = response.total;
        this.totalPages = Math.ceil(this.totalItems / this.itemsPerPage);
        this.isLoading = false;
      },
      error: (err: any) => {
        this.errorMessage = this.extractErrorMessage(err);
        this.isLoading = false;
        this.admins = [];
        this.filteredAdmins = [];
      }
    });
  }

  /**
   * Handle search input
   */
  onSearch(): void {
    this.currentPage = 1; // Reset to first page on new search
    this.loadAdmins();
  }

  /**
   * Handle filter changes
   */
  onFilterChange(): void {
    this.currentPage = 1; // Reset to first page on filter change
    this.loadAdmins();
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
    this.loadAdmins();
  }

  /**
   * Get sort icon for column header
   */
  getSortIcon(column: string): string {
    if (this.sortColumn !== column) return 'fa-sort';
    return this.sortDirection === 'asc' ? 'fa-sort-up' : 'fa-sort-down';
  }

  /**
   * Pagination controls
   */
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadAdmins();
    }
  }

  previousPage(): void {
    this.goToPage(this.currentPage - 1);
  }

  nextPage(): void {
    this.goToPage(this.currentPage + 1);
  }

  onPageSizeChange(): void {
    this.currentPage = 1;
    this.loadAdmins();
  }

  /**
   * Get page numbers for pagination display
   */
  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    
    let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(this.totalPages, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    
    return pages;
  }

  /**
   * Modal controls
   */
  openCreateModal(): void {
    this.selectedAdmin = null;
    this.showCreateModal = true;
  }

  openEditModal(admin: AdminUser): void {
    this.selectedAdmin = admin;
    this.showEditModal = true;
  }

  openSuspendModal(admin: AdminUser): void {
    this.selectedAdmin = admin;
    this.suspendReason = '';
    this.suspendReasonError = '';
    this.showSuspendModal = true;
  }

  openSuspendReasonModal(admin: AdminUser): void {
    this.selectedAdmin = admin;
    this.suspendReason = '';
    this.suspendReasonError = '';
    this.showSuspendModal = true;
  }

  closeModals(): void {
    this.showCreateModal = false;
    this.showEditModal = false;
    this.showSuspendModal = false;
    this.selectedAdmin = null;
    this.suspendReason = '';
    this.suspendReasonError = '';
  }

  /**
   * Handle admin creation from modal
   */
  onAdminCreated(): void {
    this.closeModals();
    this.showSuccessMessage('Admin created successfully');
    this.loadAdmins();
  }

  /**
   * Handle success message from modal
   */
  handleModalSuccess(message: string): void {
    this.closeModals();
    this.showSuccessMessage(message);
    this.loadAdmins();
  }

  /**
   * Handle admin update from modal
   */
  onAdminUpdated(): void {
    this.closeModals();
    this.showSuccessMessage('Admin updated successfully');
    this.loadAdmins();
  }

  /**
   * Handle admin suspension
   */
  confirmSuspend(): void {
    if (!this.selectedAdmin) return;
    
    const isSuspended = this.selectedAdmin.status === 'suspended';
    
    // Validate suspend reason if suspending
    if (!isSuspended) {
      if (!this.suspendReason || this.suspendReason.trim().length < 5) {
        this.suspendReasonError = 'Suspension reason must be at least 5 characters';
        return;
      }
      if (this.suspendReason.length > 500) {
        this.suspendReasonError = 'Suspension reason cannot exceed 500 characters';
        return;
      }
    }
    
    const userId = this.selectedAdmin.user_id;
    
    if (isSuspended) {
      // Unsuspend
      this.adminService.suspendAdmin(userId, false).subscribe({
        next: () => {
          this.showSuccessMessage('Admin activated successfully');
          this.closeModals();
          this.loadAdmins();
        },
        error: (err: any) => {
          this.errorMessage = this.extractErrorMessage(err);
          this.closeModals();
        }
      });
    } else {
      // Suspend
      this.adminService.suspendAdmin(userId, true, this.suspendReason).subscribe({
        next: () => {
          this.showSuccessMessage('Admin suspended successfully');
          this.closeModals();
          this.loadAdmins();
        },
        error: (err: any) => {
          this.errorMessage = this.extractErrorMessage(err);
          this.closeModals();
        }
      });
    }
  }

  /**
   * Navigate to admin detail view
   */
  viewAdmin(admin: AdminUser): void {
    this.router.navigate(['/admin/management', admin.user_id]);
  }

  /**
   * Get role name from role_id
   */
  getRoleName(roleId: number): string {
    const role = this.roles.find(r => r.role_id === roleId);
    return role?.role_name || 'Unknown';
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'active':
        return 'bg-green-100 text-green-700';
      case 'suspended':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  }

  /**
   * Format date for display
   */
  formatDate(date: string): string {
    if (!date) return 'N/A';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  /**
   * Clear all filters
   */
  clearFilters(): void {
    this.searchTerm = '';
    this.selectedRole = null;
    this.selectedStatus = '';
    this.dateFrom = '';
    this.dateTo = '';
    this.currentPage = 1;
    this.loadAdmins();
  }

  /**
   * Extract error message from error response
   */
  private extractErrorMessage(err: any): string {
    return err?.error?.detail || err?.error?.message || err.message || 'An error occurred';
  }

  /**
   * Show success message with auto-clear
   */
  private showSuccessMessage(message: string): void {
    this.successMessage = message;
    setTimeout(() => (this.successMessage = ''), 3000);
  }

  /**
   * Clear messages
   */
  clearMessages(): void {
    this.errorMessage = '';
    this.successMessage = '';
  }
}
