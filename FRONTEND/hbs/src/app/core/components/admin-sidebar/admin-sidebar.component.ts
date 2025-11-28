import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

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
    { label: 'Rooms', route: '/admin/rooms', icon: 'fa-bed' },
    { label: 'Guests', route: '/admin/guests', icon: 'fa-users' },
    { label: 'Admin Management', route: '/admin/admins', icon: 'fa-user-shield', permission: 'ADMIN_CREATION:READ' },
    { label: 'Role Management', route: '/admin/roles', icon: 'fa-user-tag', permission: 'ADMIN_CREATION:READ' },
    { label: 'Reports', route: '/admin/reports', icon: 'fa-chart-bar' },
    { label: 'Issues', route: '/admin/issues', icon: 'fa-exclamation-circle' },
    { label: 'Refunds', route: '/admin/refunds', icon: 'fa-money-bill-wave' },
    { label: 'Content', route: '/admin/content', icon: 'fa-file-alt' },
    { label: 'Notifications', route: '/admin/notifications', icon: 'fa-bell' },
    { label: 'Settings', route: '/admin/settings', icon: 'fa-cog' }
  ];

  constructor() {}

  ngOnInit(): void {}
}
