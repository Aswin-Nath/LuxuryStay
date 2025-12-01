import { Component, Input, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

export interface SidebarLink {
  label: string;
  route: string;
  page: string;
  icon?: string;
}

@Component({
  selector: 'app-customer-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './customer-sidebar.component.html',
  styles: []
})
export class CustomerSidebarComponent implements OnInit {
  @Input() currentPage: string = 'dashboard';
  
  isSidebarOpen: boolean = false;
  screenSize: 'mobile' | 'tablet' | 'desktop' = 'desktop';
  
  sidebarLinks: SidebarLink[] = [
    { label: 'Overview', route: '/dashboard', page: 'dashboard', icon: 'fa-home' },
    { label: 'My Bookings', route: '/bookings', page: 'bookings', icon: 'fa-calendar' },
    { label: 'Wishlist', route: '/wishlist', page: 'wishlist', icon: 'fa-heart' },
    { label: 'My Issues', route: '/issues', page: 'issues', icon: 'fa-exclamation-circle' },
    { label: 'My Refunds', route: '/refunds', page: 'refunds', icon: 'fa-money-bill' },
    { label: 'Profile', route: '/profile', page: 'profile', icon: 'fa-user' },
    { label: 'Reports', route: '/reports', page: 'reports', icon: 'fa-chart-bar' }
  ];

  ngOnInit(): void {
    this.updateScreenSize();
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    this.updateScreenSize();
  }

  private updateScreenSize(): void {
    const width = window.innerWidth;
    if (width < 768) {
      this.screenSize = 'mobile';
      this.isSidebarOpen = false;
    } else if (width < 1024) {
      this.screenSize = 'tablet';
      this.isSidebarOpen = false;
    } else {
      this.screenSize = 'desktop';
      this.isSidebarOpen = true;
    }
  }

  onLinkClick(): void {
    // Close sidebar on mobile when link is clicked
    if (this.screenSize === 'mobile') {
      this.isSidebarOpen = false;
    }
  }
}
