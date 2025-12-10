import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminNavbarComponent } from '../../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../../layout/Admin/admin-sidebar/admin-sidebar.component';
import { RoleManagementService, Role, PermissionGroup, Permission } from '../../../../services/role-management.service';
// import { RolePermissionModalComponent } from '../permissions-management/role-permission-modal.component';
// import { AddRoleModalComponent } from './add-role-modal.component';
import { AddRoleModalComponent } from '../create-role/create_role.component';
// import { RolePermissionModalComponent } from '../../role-permission-modal.component';
import { RolePermissionModalComponent } from '../role-mapping/role-mapping.component';
@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AdminNavbarComponent,
    AdminSidebarComponent,
    RolePermissionModalComponent,
    AddRoleModalComponent
  ],
  templateUrl: './roles-display.html',
  styleUrls: ['./roles-display.css']
})
export class RoleManagementComponent implements OnInit {
  // Data
  roles: Role[] = [];
  permissions: Permission[] = [];
  permissionsGrouped: PermissionGroup[] = [];
  rolePermissionsMap: { [roleId: number]: number[] } = {}; // Track permissions per role

  // UI State
  isLoading = false;
  showPermissionModal = false;
  showAddRoleModal = false;
  selectedRole: Role | null = null;
  selectedPermissions: number[] = [];
  errorMessage = '';
  successMessage = '';

  // Pagination
  Math = Math;
  currentPage = 1;
  pageSize = 10;
  pageSizeOptions = [5, 10, 15, 20];
  totalRecords = 0;
  totalPages = 0;

  constructor(private roleService: RoleManagementService) {}

  ngOnInit(): void {
    this.loadRoles();
    this.loadPermissions();
  }

  /**
   * Load all roles
   */
  loadRoles(): void {
    this.isLoading = true;
    this.roleService.getRoles().subscribe({
      next: (roles: Role[]) => {
        // Filter out customer role (role_id = 1)
        this.roles = roles.filter(r => r.role_id !== 1);
        this.totalRecords = this.roles.length;
        this.totalPages = Math.ceil(this.totalRecords / this.pageSize);
        this.currentPage = 1;
        // Load permissions for each role
        this.roles.forEach(role => {
          this.roleService.getRolePermissions(role.role_id).subscribe({
            next: (permissions: Permission[]) => {
              this.rolePermissionsMap[role.role_id] = permissions.map(p => p.permission_id) || [];
            },
            error: (err: any) => {
              console.error(`Error loading permissions for role ${role.role_id}:`, err);
              this.rolePermissionsMap[role.role_id] = [];
            }
          });
        });
        this.isLoading = false;
      },
      error: (err: any) => {
        this.errorMessage = 'Failed to load roles';
        this.isLoading = false;
      }
    });
  }

  /**
   * Load all permissions grouped by resource
   */
  loadPermissions(): void {
    this.roleService.getPermissionsGrouped().subscribe({
      next: (grouped: PermissionGroup[]) => {
        this.permissionsGrouped = grouped;
      },
      error: (err: any) => {
        console.error('Error loading permissions:', err);
      }
    });
  }

  /**
   * Open permission modal for a role
   */
  openPermissionModal(role: Role): void {
    this.selectedRole = role;
    // Load current permissions for this role
    this.roleService.getRolePermissions(role.role_id).subscribe({
      next: (permissions: Permission[]) => {
        // Extract permission IDs from the flat permission array
        this.selectedPermissions = permissions.map(p => p.permission_id) || [];
        // Store in map for reference
        this.rolePermissionsMap[role.role_id] = this.selectedPermissions;
        this.showPermissionModal = true;
      },
      error: (err: any) => {
        console.error('Error loading role permissions:', err);
        this.selectedPermissions = [];
        this.showPermissionModal = true;
      }
    });
  }

  /**
   * Open modal to add new role
   */
  openAddRoleModal(): void {
    this.showAddRoleModal = true;
  }

  /**
   * Close add role modal
   */
  closeAddRoleModal(): void {
    this.showAddRoleModal = false;
  }

  /**
   * Handle new role creation
   */
  onRoleCreated(roleData: { role_name: string; role_description: string }): void {
    this.roleService.createRole(roleData).subscribe({
      next: (newRole: Role) => {
        this.showSuccessMessage(`Role "${newRole.role_name}" created successfully!`);
        // Close the add role modal
        this.closeAddRoleModal();
        // Load roles again to refresh the list
        this.loadRoles();
        this.loadPermissions();
      },
      error: (err: any) => {
        this.errorMessage = err?.error?.detail || 'Failed to create role';
      }
    });
  }

  /**
   * Close permission modal
   */
  closePermissionModal(): void {
    this.showPermissionModal = false;
    this.selectedRole = null;
    this.selectedPermissions = [];
  }

  /**
   * Handle permission save from modal
   */
  onPermissionsSaved(permissionIds: number[]): void {
    if (!this.selectedRole) return;

    this.roleService.assignPermissionsToRole(this.selectedRole.role_id, permissionIds).subscribe({
      next: (response: any) => {
        this.showSuccessMessage('Permissions updated successfully');
        this.closePermissionModal();
        this.loadRoles();
      },
      error: (err: any) => {
        this.errorMessage = err?.error?.detail || 'Failed to update permissions';
      }
    });
  }

  /**
   * Show success message
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

  // Pagination Methods
  get paginatedRoles(): Role[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.roles.slice(start, start + this.pageSize);
  }

  changePageSize(size: number): void {
    this.pageSize = size;
    this.currentPage = 1;
    this.totalPages = Math.ceil(this.totalRecords / this.pageSize);
    this.loadRoles();
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPages = 5;
    
    if (this.totalPages <= maxPages) {
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, this.currentPage - 2);
      const endPage = Math.min(this.totalPages, this.currentPage + 2);
      
      if (startPage > 1) pages.push(1);
      if (startPage > 2) pages.push(-1);
      
      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }
      
      if (endPage < this.totalPages - 1) pages.push(-1);
      if (endPage < this.totalPages) pages.push(this.totalPages);
    }
    
    return pages;
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadRoles();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) this.currentPage--;
    this.loadRoles();
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) this.currentPage++;
    this.loadRoles();
  }  /**
   * Get count of permissions for a role (for display)
   */
  getPermissionCount(role: Role): number {
    return this.rolePermissionsMap[role.role_id]?.length || 0;
  }
}
