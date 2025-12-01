import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { CustomerNavbarComponent } from '../../../core/components/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../../core/components/customer-sidebar/customer-sidebar.component';

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
  imports: [CommonModule, FormsModule, RouterModule, CustomerNavbarComponent, CustomerSidebarComponent],
  templateUrl: './customer-dashboard.component.html',
  styleUrls: ['./customer-dashboard.component.css']
})
export class CustomerDashboardComponent implements OnInit {
  // Stats
  bookingsCount = 3;
  offersCount = 6;
  rewardPoints = 2450;

  // Date picker modal properties
  showDatePickerModal: boolean = false;
  checkIn: string = '';
  checkOut: string = '';
  datePickerError: string = '';

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

  currentPage = 'dashboard';

  constructor(private router: Router) { }

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

  bookNow(): void {
    // Initialize with today and tomorrow dates
    const today = new Date().toISOString().split('T')[0];
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    this.checkIn = today;
    this.checkOut = tomorrow;
    this.datePickerError = '';
    this.showDatePickerModal = true;
  }

  /**
   * Close date picker modal
   */
  closeBookingModal(): void {
    this.showDatePickerModal = false;
    this.datePickerError = '';
  }

  /**
   * Proceed with booking - navigate to booking component with dates
   */
  proceedWithBooking(): void {
    if (!this.checkIn || !this.checkOut) {
      this.datePickerError = 'Please select check-in and check-out dates';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.datePickerError = 'Check-out date must be after check-in date';
      return;
    }

    this.datePickerError = '';
    
    // Navigate to booking component with dates as query parameters
    this.router.navigate(['/booking'], {
      queryParams: {
        checkIn: this.checkIn,
        checkOut: this.checkOut
      }
    });
  }

  /**
   * Calculate number of nights
   */
  calculateNumberOfNights(): number {
    if (!this.checkIn || !this.checkOut) return 1;
    const start = new Date(this.checkIn);
    const end = new Date(this.checkOut);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(1, diffDays);
  }
}
