import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PermissionGroup, Permission } from '../../../../services/role-management.service';

@Component({
  selector: 'app-role-permission-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './role-mapping.html',
  styleUrls: ['./role-mapping.css']
})
export class RolePermissionModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Input() roleName = '';
  @Input() permissionsGrouped: PermissionGroup[] = [];
  @Input() selectedPermissions: number[] = [];
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<number[]>();

  // Track expanded/collapsed resources
  expandedResources: { [key: string]: boolean } = {};
  selectedResourcePermissions: { [resource: string]: number[] } = {};
  isSubmitting = false;

  ngOnInit(): void {
    this.initializeResourceSelection();
  }

  /**
   * Detect changes to inputs (selectedPermissions) and re-initialize
   */
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['selectedPermissions'] && !changes['selectedPermissions'].firstChange) {
      this.initializeResourceSelection();
    }
  }

  /**
   * Initialize resource selection based on selected permissions
   */
  initializeResourceSelection(): void {
    this.selectedResourcePermissions = {};
    
    // Group selected permissions by resource
    this.permissionsGrouped.forEach(group => {
      const permIds = group.permissions
        .filter(p => this.selectedPermissions.includes(p.permission_id))
        .map(p => p.permission_id);
      
      if (permIds.length > 0) {
        this.selectedResourcePermissions[group.resource] = permIds;
        this.expandedResources[group.resource] = true;
      }
    });
  }

  /**
   * Toggle resource expansion
   */
  toggleResource(resource: string): void {
    this.expandedResources[resource] = !this.expandedResources[resource];
  }

  /**
   * Check if resource has any selected permissions
   */
  isResourceSelected(resource: string): boolean {
    const perms = this.selectedResourcePermissions[resource];
    return perms && perms.length > 0;
  }

  /**
   * Toggle permission selection for a resource
   */
  togglePermission(permissionId: number, resource: string): void {
    if (!this.selectedResourcePermissions[resource]) {
      this.selectedResourcePermissions[resource] = [];
    }

    const index = this.selectedResourcePermissions[resource].indexOf(permissionId);
    if (index > -1) {
      this.selectedResourcePermissions[resource].splice(index, 1);
    } else {
      this.selectedResourcePermissions[resource].push(permissionId);
    }
  }

  /**
   * Check if all permissions in a resource are selected
   */
  areAllResourcePermissionsSelected(resource: string): boolean {
    const group = this.permissionsGrouped.find(g => g.resource === resource);
    if (!group) return false;
    
    const selectedPerms = this.selectedResourcePermissions[resource] || [];
    return group.permissions.length > 0 && selectedPerms.length === group.permissions.length;
  }

  /**
   * Toggle all permissions in a resource (select all or deselect all based on current state)
   */
  toggleAllResourcePermissions(resource: string): void {
    const group = this.permissionsGrouped.find(g => g.resource === resource);
    if (!group) return;

    if (!this.selectedResourcePermissions[resource]) {
      this.selectedResourcePermissions[resource] = [];
    }

    // If all are selected, deselect all. Otherwise, select all.
    if (this.areAllResourcePermissionsSelected(resource)) {
      // Deselect all
      this.selectedResourcePermissions[resource] = [];
    } else {
      // Select all
      this.selectedResourcePermissions[resource] = group.permissions.map(p => p.permission_id);
    }
  }

  /**
   * Check if permission is selected
   */
  isPermissionSelected(permissionId: number, resource: string): boolean {
    const perms = this.selectedResourcePermissions[resource];
    return perms && perms.includes(permissionId);
  }

  /**
   * Get all selected permission IDs
   */
  getAllSelectedPermissions(): number[] {
    const allSelected: number[] = [];
    Object.values(this.selectedResourcePermissions).forEach(ids => {
      allSelected.push(...ids);
    });
    return allSelected;
  }

  /**
   * Save permissions
   */
  onSave(): void {
    this.isSubmitting = true;
    const selectedIds = this.getAllSelectedPermissions();
    this.save.emit(selectedIds);
    setTimeout(() => {
      this.isSubmitting = false;
      this.onClose();
    }, 500);
  }

  /**
   * Close modal
   */
  onClose(): void {
    this.close.emit();
  }

  /**
   * Select all permissions
   */
  selectAll(): void {
    this.permissionsGrouped.forEach(group => {
      this.selectedResourcePermissions[group.resource] = group.permissions.map(p => p.permission_id);
      this.expandedResources[group.resource] = true;
    });
  }

  /**
   * Deselect all permissions
   */
  deselectAll(): void {
    this.selectedResourcePermissions = {};
    this.permissionsGrouped.forEach(group => {
      this.expandedResources[group.resource] = false;
    });
  }
}
