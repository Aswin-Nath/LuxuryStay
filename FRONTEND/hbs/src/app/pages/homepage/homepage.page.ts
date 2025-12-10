import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthenticationService } from '../../services/authentication.service';
import { BookingStateService } from '../../shared/services/booking-state.service';
import { DatePickerModalComponent } from '../../shared/components/date-picker-modal/date-picker-modal.component';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { HeroSectionComponent } from './components/hero-section/hero-section.component';
import { AboutSectionComponent } from './components/about-section/about-section.component';
import { RoomsSectionComponent } from './components/rooms-section/rooms-section.component';
import { OffersSectionComponent } from './components/offers-section/offers-section.component';
import { FacilitiesSectionComponent } from './components/facilities-section/facilities-section.component';
import { TestimonialsSectionComponent } from './components/testimonials-section/testimonials-section.component';
import { DestinationsSectionComponent } from './components/destinations-section/destinations-section.component';
import { HotelInfoSectionComponent } from './components/hotel-info-section/hotel-info-section.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-homepage',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    DatePickerModalComponent,
    CustomerNavbarComponent,
    HeroSectionComponent,
    AboutSectionComponent,
    RoomsSectionComponent,
    OffersSectionComponent,
    FacilitiesSectionComponent,
    TestimonialsSectionComponent,
    DestinationsSectionComponent,
    HotelInfoSectionComponent,
    FooterComponent
  ],
  templateUrl: './homepage.page.html',
  styleUrl: './homepage.page.css'
})
export class HomepageComponent implements OnInit {
  isLoggedIn = false;
  showDatePickerModal = false;
  datePickerCheckIn: string = '';
  datePickerCheckOut: string = '';
  datePickerError: string = '';

  // Room showcase data
  rooms = [
    {
      id: 1,
      name: 'Deluxe Room',
      image: '/assets/images/room1.jpg',
      description: 'Elegant room with stunning city views, modern amenities, and luxury comfort.',
      price: '$150/night'
    },
    {
      id: 2,
      name: 'Executive Suite',
      image: 'https://images.unsplash.com/photo-1505691723518-36a5ac3be353?auto=format&fit=crop&w=600&q=80',
      description: 'Spacious suite with premium furnishings, dedicated workspace, and exclusive services.',
      price: '$250/night'
    },
    {
      id: 3,
      name: 'Presidential Suite',
      image: '/assets/images/room3.jpg',
      description: 'Luxurious penthouse suite with panoramic views, private spa, and concierge service.',
      price: '$500/night'
    }
  ];

  // Offers data
  offers = [
    {
      id: 1,
      name: 'Weekend Getaway',
      image: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80',
      description: 'Escape for a relaxing weekend with 20% discount on all room types.',
      discount: '20%'
    },
    {
      id: 2,
      name: 'Family Package',
      image: 'https://images.unsplash.com/photo-1505691723518-36a5ac3be353?auto=format&fit=crop&w=600&q=80',
      description: 'Perfect for families with complimentary breakfast and kids activities.',
      discount: '15%'
    },
    {
      id: 3,
      name: 'Honeymoon Special',
      image: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=600&q=80',
      description: 'Romantic getaway with champagne, spa vouchers, and special dinner.',
      discount: '25%'
    }
  ];

  // Facilities data
  facilities = [
    {
      id: 1,
      name: 'Wellness Spa',
      image: '/assets/images/spa.png',
      description: 'Rejuvenating spa treatments and wellness therapies.'
    },
    {
      id: 2,
      name: 'Infinity Pool',
      image: '/assets/images/pool.jpg',
      description: 'Olympic-size pool with stunning sunset views.'
    },
    {
      id: 3,
      name: 'Fine Dining',
      image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=600&q=80',
      description: 'Award-winning restaurants and 24-hour room service.'
    },
    {
      id: 4,
      name: 'Fitness Center',
      image: '/assets/images/gym.png',
      description: 'State-of-the-art gym equipment and personal trainers.'
    },
    {
      id: 5,
      name: 'Conference Hall',
      image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=600&q=80',
      description: 'Professional event spaces for meetings and conferences.'
    },
    {
      id: 6,
      name: 'Luxury Lounge',
      image: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=600&q=80',
      description: 'Exclusive lounge with premium amenities and services.'
    }
  ];

  // Testimonials data
  testimonials = [
    {
      name: 'Sarah Johnson',
      role: 'Business Executive',
      message: 'Exceptional service and luxurious accommodations. Best hotel experience ever!',
      rating: 5
    },
    {
      name: 'Michael Chen',
      role: 'Travel Blogger',
      message: 'The attention to detail is remarkable. Every moment was memorable.',
      rating: 5
    },
    {
      name: 'Emma Wilson',
      role: 'Honeymooner',
      message: 'Perfect for our special celebration. Thank you for making it unforgettable!',
      rating: 5
    }
  ];

  // Destinations data
  destinations = [
    {
      name: 'New York',
      image: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&w=600&q=80',
      description: 'Experience the vibrant energy of NYC'
    },
    {
      name: 'Maldives',
      image: 'https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=600&q=80',
      description: 'Tropical paradise with pristine beaches'
    },
    {
      name: 'Paris',
      image: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=600&q=80',
      description: 'City of love and romantic getaways'
    }
  ];

  constructor(
    private authService: AuthenticationService,
    private router: Router,
    private bookingStateService: BookingStateService
  ) {}

  ngOnInit(): void {
    this.authService.authState$.subscribe((isLoggedIn) => {
      this.isLoggedIn = isLoggedIn;
    });
  }

  onHeroBookNow(): void {
    this.openBookingModal();
  }

  onAboutLearnMore(): void {
    this.navigateToFacilities();
  }

  onRoomsViewAll(): void {
    this.navigateToRooms();
  }

  onRoomsAddToWishlist(roomId: number): void {
    this.addToWishlist(roomId);
  }

  onOffersLearnMore(): void {
    this.navigateToOffers();
  }

  onFacilitiesExplore(): void {
    this.navigateToFacilities();
  }

  onDestinationsViewAll(): void {
    this.navigateToRooms();
  }

  onDestinationsExplore(destination: string): void {
    this.exploreDestination(destination);
  }

  openBookingModal(): void {
    if (!this.isLoggedIn) {
      this.router.navigate(['/login']);
      return;
    }

    this.showDatePickerModal = true;
    const today = new Date();
    this.datePickerCheckIn = this.formatDateForInput(today);

    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.datePickerCheckOut = this.formatDateForInput(tomorrow);

    this.datePickerError = '';
  }

  private formatDateForInput(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  onDatePickerClose(): void {
    this.showDatePickerModal = false;
    this.datePickerCheckIn = '';
    this.datePickerCheckOut = '';
    this.datePickerError = '';
  }

  onDatePickerProceed(data: { checkIn: string; checkOut: string; roomTypeId?: number; offerId?: number }): void {
    this.showDatePickerModal = false;

    this.bookingStateService.setBookingState({
      checkIn: data.checkIn,
      checkOut: data.checkOut
    });

    this.router.navigate(['/booking']);
  }

  navigateToRooms(): void {
    this.router.navigate(['/rooms']);
  }

  navigateToOffers(): void {
    this.router.navigate(['/offers']);
  }

  navigateToFacilities(): void {
    this.router.navigate(['/facilities']);
  }

  exploreDestination(destination: string): void {
    this.router.navigate(['/rooms'], { queryParams: { filter: destination } });
  }

  addToWishlist(roomId: number): void {
    if (!this.isLoggedIn) {
      this.router.navigate(['/login']);
      return;
    }
    this.showToast('Added to wishlist!', 'favorite');
  }

  showToast(message: string, icon: string = 'check_circle'): void {
    const toast = document.getElementById('toast');
    if (toast) {
      document.getElementById('toastMessage')!.textContent = message;
      document.getElementById('toastIcon')!.textContent = icon;
      toast.classList.remove('translate-x-full', 'opacity-0');
      toast.classList.add('translate-x-0', 'opacity-100');

      setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        toast.classList.remove('translate-x-0', 'opacity-100');
      }, 3000);
    }
  }
}
