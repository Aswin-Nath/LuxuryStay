import { Injectable } from '@angular/core';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private config: ConfigService) {}

  getUrl(endpoint: string): string {
    return this.config.getFullUrl(endpoint);
  }

  getAuthUrl(): string { return this.config.getFullUrl('auth'); }
  getProfileUrl(): string { return this.config.getFullUrl('profile'); }
  getBookingsUrl(): string { return this.config.getFullUrl('bookings'); }
  getV2RoomsUrl(): string { return this.config.getFullUrl('v2/rooms'); }
  getRoomManagementUrl(): string { return this.config.getFullUrl('room-management'); }
  getImagesUrl(): string { return this.config.getFullUrl('images'); }
  getOffersUrl(): string { return this.config.getFullUrl('offers'); }
  getRefundsUrl(): string { return this.config.getFullUrl('refunds'); }
  getReviewsUrl(): string { return this.config.getFullUrl('reviews'); }
  getWishlistUrl(): string { return this.config.getFullUrl('wishlist'); }
  getIssuesUrl(): string { return this.config.getFullUrl('issues'); }
  getPaymentsUrl(): string { return this.config.getFullUrl('payments'); }
  getRolesUrl(): string { return this.config.getFullUrl('roles'); }
  getUsersUrl(): string { return this.config.getFullUrl('users'); }
}
