import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface Role {
  role_id: number;
  role_name: string;
  role_description?: string;
}

export interface Permission {
  permission_id: number;
  permission_name: string;
}

export interface PermissionGroup {
  resource: string; // ADMIN_CREATION, ROOM_MANAGEMENT, etc.
  permissions: PermissionAction[];
}

export interface PermissionAction {
  action: string; // READ, WRITE, DELETE, UPDATE
  permission_id: number;
  permission_name: string;
}

export interface RolePermissions {
  role_id: number;
  role_name: string;
  permissions: Permission[];
  permission_ids: number[];
}

export interface AssignPermissionsRequest {
  permission_ids: number[];
}

@Injectable({
  providedIn: 'root'
})
export class RoleManagementService {
  private apiUrl = `${environment.apiUrl}`;

  constructor(private http: HttpClient) {}

  /**
   * Get all roles
   */
  getRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(`${this.apiUrl}/roles`);
  }

  /**
   * Create a new role
   */
  createRole(roleData: { role_name: string; role_description: string }): Observable<Role> {
    return this.http.post<Role>(`${this.apiUrl}/roles`, roleData);
  }

  /**
   * Get all permissions grouped by resource
   */
  getPermissionsGrouped(): Observable<PermissionGroup[]> {
    return this.http.get<Permission[]>(`${this.apiUrl}/roles/all-permissions`).pipe(
      // Transform flat permission list to grouped structure
      (source: any) => new Observable(observer => {
        source.subscribe({
          next: (permissions: Permission[]) => {
            const grouped = this.groupPermissions(permissions);
            observer.next(grouped);
            observer.complete();
          },
          error: (err: any) => observer.error(err)
        });
      })
    );
  }

  /**
   * Get all permissions
   */
  getPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(`${this.apiUrl}/roles/all-permissions`);
  }

  /**
   * Get permissions for a specific role
   */
  getRolePermissions(roleId: number): Observable<Permission[]> {
    const params = new HttpParams().set('role_id', roleId.toString());
    return this.http.get<Permission[]>(`${this.apiUrl}/roles/permissions`, { params });
  }

  /**
   * Assign permissions to a role
   */
  assignPermissionsToRole(
    roleId: number,
    permissionIds: number[]
  ): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/roles/assign`,
      {
        role_id: roleId,
        permission_ids: permissionIds
      }
    );
  }

  /**
   * Group permissions by resource and action
   */
  private groupPermissions(permissions: Permission[]): PermissionGroup[] {
    const groupMap: { [key: string]: PermissionAction[] } = {};

    permissions.forEach((perm: Permission) => {
      const [resource, action] = perm.permission_name.split(':');

      if (!groupMap[resource]) {
        groupMap[resource] = [];
      }

      groupMap[resource].push({
        action: action || 'OTHER',
        permission_id: perm.permission_id,
        permission_name: perm.permission_name
      });
    });

    // Convert map to array and sort by resource name
    return Object.entries(groupMap)
      .map(([resource, permissions]) => ({
        resource,
        permissions: permissions.sort((a, b) =>
          this.getActionOrder(a.action) - this.getActionOrder(b.action)
        )
      }))
      .sort((a, b) => a.resource.localeCompare(b.resource));
  }

  /**
   * Get sort order for permission actions
   */
  private getActionOrder(action: string): number {
    const order: { [key: string]: number } = {
      'READ': 1,
      'WRITE': 2,
      'UPDATE': 3,
      'DELETE': 4
    };
    return order[action] || 99;
  }

  /**
   * Transform grouped permissions to flat permission IDs
   */
  getSelectedPermissionIds(selectedGroups: {
    [resource: string]: string[]
  }): number[] {
    // This will be implemented based on how we track selected permissions
    return [];
  }
}
