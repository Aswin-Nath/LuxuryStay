import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { HasPermissionDirective } from '../../../core/directives/has-permission.directive';
import { PermissionService } from '../../../core/services/permissions/permissions';
import { filter } from 'rxjs/operators';

interface SidebarLink {
  label: string;
  route: string;
  icon: string;
  permission?: string;
}

@Component({
  selector: 'app-admin-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './admin-sidebar.component.html',
  styleUrls: ['./admin-sidebar.component.css']
})
export class AdminSidebarComponent implements OnInit {
  sidebarLinks: SidebarLink[] = [
    { label: 'Dashboard', route: '/admin/dashboard', icon: 'fa-tachometer-alt' },
    { label: 'Bookings', route: '/admin/bookings', icon: 'fa-calendar-check' },
        { label: 'Offer', route: '/admin/offers', icon: 'fa-tag' },
    { label: 'Rooms', route: '/admin/rooms', icon: 'fa-bed' },
    { label: 'Room Types & Amenities', route: '/admin/room-types-amenities', icon: 'fa-layer-group' },
    { label: 'Guests', route: '/admin/guests', icon: 'fa-users' },
    { label: 'Admin Management', route: '/admin/management', icon: 'fa-user-shield', permission: 'ADMIN_CREATION:READ' },
    { label: 'Role Management', route: '/admin/roles', icon: 'fa-user-tag', permission: 'ADMIN_CREATION:READ' },
    { label: 'Reports', route: '/admin/reports', icon: 'fa-chart-bar' },
    { label: 'Issues', route: '/admin/issues', icon: 'fa-exclamation-circle' },
    { label: 'Refunds', route: '/admin/refunds', icon: 'fa-money-bill-wave' },
    { label: 'Content', route: '/admin/content', icon: 'fa-file-alt' },
    { label: 'Profile', route: '/admin/profile', icon: 'fa-bell' },
    { label: 'Settings', route: '/admin/settings', icon: 'fa-cog' }  ];

  currentRoute: string = '';

  constructor(public permissionService: PermissionService, private router: Router) {}

  ngOnInit(): void {
    // Track current route changes
    this.currentRoute = this.router.url;
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        this.currentRoute = event.url;
      });
  }

  /**
   * Check if a menu item should be visible
   * Show if: no permission required OR user has the permission
   */
  isMenuItemVisible(permission?: string): boolean {
    // If no permission is set, show the item
    if (!permission) {
      return true;
    }
    // If permission is set, check if user has it
    return this.permissionService.hasPermission(permission);
  }

  /**
   * Check if a route is currently active (including sub-routes)
   * E.g., /admin/room-types-amenities/view/123 matches /admin/room-types-amenities
   * Also handles related routes like /admin/room-type/:id/view which should highlight /admin/room-types-amenities
   */
  isRouteActive(route: string): boolean {
    // Direct match or sub-route match
    if (this.currentRoute.startsWith(route)) {
      return true;
    }
    
    // Special handling for room-types-amenities and related routes
    if (route === '/admin/room-types-amenities') {
      // Highlight if on any of these related routes
      const relatedRoutes = [
        '/admin/room-types-amenities',
        '/admin/room-type/',
        '/admin/edit-room-type/'
      ];
      return relatedRoutes.some(r => this.currentRoute.startsWith(r));
    }
    
    return false;
  }
}
