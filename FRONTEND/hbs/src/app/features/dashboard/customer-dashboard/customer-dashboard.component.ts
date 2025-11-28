import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../../core/components/customer-navbar/customer-navbar.component';

interface Booking {
  id: string;
  roomType: string;
  roomNo: string;
  checkIn: string;
  checkOut: string;
  guests: string;
  rooms: number;
}

interface Offer {
  id: string;
  title: string;
  description: string;
  discount: string;
  discountType: 'percent' | 'special';
  imageUrl: string;
  validTill: string;
  buttonColor: string;
  isSaved: boolean;
}

@Component({
  selector: 'app-customer-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent],
  templateUrl: './customer-dashboard.component.html',
  styleUrls: ['./customer-dashboard.component.css']
})
export class CustomerDashboardComponent implements OnInit {
  // Stats
  bookingsCount = 3;
  offersCount = 6;
  rewardPoints = 2450;

  // Upcoming Bookings
  upcomingBookings: Booking[] = [
    {
      id: 'BK001',
      roomType: 'Deluxe Room',
      roomNo: '205',
      checkIn: '10th Oct 2025, 2:00 PM',
      checkOut: '13th Oct 2025, 11:00 AM',
      guests: '2 Adults, 1 Child',
      rooms: 1
    },
    {
      id: 'BK002',
      roomType: 'Standard Rooms',
      roomNo: '110, 111',
      checkIn: '20th Nov 2025, 3:00 PM',
      checkOut: '24th Nov 2025, 12:00 PM',
      guests: '4 Adults',
      rooms: 2
    }
  ];

  // Offers
  offers: Offer[] = [
    {
      id: 'offer1',
      title: 'Breakfast Inclusive Rate',
      description: 'Wake up to a symphony of flavours with our breakfast spread.',
      discount: '20% OFF',
      discountType: 'percent',
      imageUrl: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80',
      validTill: 'Dec 31',
      buttonColor: 'bg-yellow-500 hover:bg-yellow-600',
      isSaved: false
    },
    {
      id: 'offer2',
      title: 'Romantic Getaway',
      description: 'Special package for couples with wine & candlelight dinner.',
      discount: 'Special',
      discountType: 'special',
      imageUrl: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80',
      validTill: 'Jan 15',
      buttonColor: 'bg-pink-500 hover:bg-pink-600',
      isSaved: false
    }
  ];

  // Toast
  showToast = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' = 'success';

  // Sidebar links
  sidebarLinks = [
    { label: 'Overview', route: '/customer/dashboard', icon: 'fa-home', page: 'dashboard' },
    { label: 'My Bookings', route: '/customer/bookings', icon: 'fa-calendar-check', page: 'booking' },
    { label: 'Wishlist', route: '/customer/wishlist', icon: 'fa-heart', page: 'saved' },
    { label: 'My Issues', route: '/customer/issues', icon: 'fa-exclamation-circle', page: 'issues' },
    { label: 'My Refunds', route: '/customer/refunds', icon: 'fa-money-bill-wave', page: 'refunds' },
    { label: 'Profile', route: '/customer/profile', icon: 'fa-user', page: 'profile' },
    { label: 'Reports', route: '/customer/reports', icon: 'fa-chart-bar', page: 'report' }
  ];

  currentPage = 'dashboard';

  constructor() { }

  ngOnInit(): void {
    this.loadSavedOffers();
  }

  loadSavedOffers(): void {
    const savedOffers = JSON.parse(localStorage.getItem('savedOffers') || '[]');
    this.offers.forEach(offer => {
      offer.isSaved = savedOffers.includes(offer.id);
    });
  }

  toggleSaveOffer(offer: Offer): void {
    offer.isSaved = !offer.isSaved;

    const savedOffers = JSON.parse(localStorage.getItem('savedOffers') || '[]');

    if (offer.isSaved) {
      if (!savedOffers.includes(offer.id)) {
        savedOffers.push(offer.id);
      }
      this.displayToast('Offer saved to your wishlist!', 'success');
    } else {
      const index = savedOffers.indexOf(offer.id);
      if (index > -1) {
        savedOffers.splice(index, 1);
      }
      this.displayToast('Offer removed from wishlist', 'info');
    }

    localStorage.setItem('savedOffers', JSON.stringify(savedOffers));
  }

  displayToast(message: string, type: 'success' | 'error' | 'info'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.showToast = true;

    setTimeout(() => {
      this.showToast = false;
    }, 3000);
  }

  getToastIcon(): string {
    switch (this.toastType) {
      case 'success': return 'check_circle';
      case 'error': return 'error';
      case 'info': return 'info';
      default: return 'check_circle';
    }
  }

  getToastClass(): string {
    switch (this.toastType) {
      case 'success': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'info': return 'bg-blue-500';
      default: return 'bg-green-500';
    }
  }

  getDiscountBadgeClass(type: string): string {
    return type === 'percent' ? 'bg-green-100 text-green-800' : 'bg-pink-100 text-pink-800';
  }
}
