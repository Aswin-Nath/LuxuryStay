import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface RoomTypeOffer {
  room_type_id: number;
  available_count: number;
  discount_percent: number;
}

export interface RoomType {
  room_type_id: number;
  type_name: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  square_ft: number;
  description: string;
  available_count?: number;
}

export interface RoomTypeWithCount {
  room_type_id: number;
  type_name: string;
  total_count: number;
  price_per_night: number;
  description: string;
}

export interface OfferCreate {
  offer_name: string;
  description?: string;
  discount_percent: number;
  room_types: RoomTypeOffer[];
  is_active: boolean;
  valid_from: string;
  valid_to: string;
  max_uses?: number;
}

export interface OfferUpdate {
  offer_name?: string;
  description?: string;
  discount_percent?: number;
  room_types?: RoomTypeOffer[];
  is_active?: boolean;
  valid_from?: string;
  valid_to?: string;
  max_uses?: number;
}

export interface Offer {
  offer_id: number;
  offer_name: string;
  description?: string;
  discount_percent: number;
  room_types: RoomTypeOffer[];
  is_active: boolean;
  valid_from: string;
  valid_to: string;
  max_uses?: number;
  current_uses: number;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface OfferListItem {
  offer_id: number;
  offer_name: string;
  description?: string;
  discount_percent: number;
  is_active: boolean;
  valid_from: string;
  valid_to: string;
  current_uses: number;
  max_uses?: number;
  created_at:string
}

export interface OfferImage {
  image_id: number;
  entity_type: string;
  entity_id: number;
  image_url: string;
  caption?: string;
  is_primary: boolean;
  created_at: string;
}

@Injectable({
  providedIn: 'root',
})
export class OfferService {
  private apiUrl = `${environment.apiUrl}/offers`;

  constructor(private http: HttpClient) {}

  // ===============================================
  // OFFER CRUD OPERATIONS
  // ===============================================

  createOffer(offer: OfferCreate): Observable<Offer> {
    return this.http.post<Offer>(`${this.apiUrl}/create`, offer);
  }

  getOffer(offerId: number): Observable<Offer> {
    return this.http.get<Offer>(`${this.apiUrl}/${offerId}`);
  }

  listOffers(skip: number = 0, limit: number = 100, isActive?: boolean): Observable<OfferListItem[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString());

    if (isActive !== undefined) {
      params = params.set('is_active', isActive.toString());
    }

    return this.http.get<OfferListItem[]>(`${this.apiUrl}`, { params });
  }

  // Admin: List offers with advanced filters
  listOffersAdmin(
    skip: number = 0,
    limit: number = 100,
    filters?: {
      isActive?: boolean;
      searchTerm?: string;
      minDiscount?: number;
      maxDiscount?: number;
      startDate?: string;
      endDate?: string;
      roomTypeId?: number;
    }
  ): Observable<OfferListItem[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString());

    if (filters) {
      if (filters.isActive !== undefined) {
        params = params.set('is_active', filters.isActive.toString());
      }
      if (filters.searchTerm) {
        params = params.set('search', filters.searchTerm);
      }
      if (filters.minDiscount !== undefined) {
        params = params.set('min_discount', filters.minDiscount.toString());
      }
      if (filters.maxDiscount !== undefined) {
        params = params.set('max_discount', filters.maxDiscount.toString());
      }
      if (filters.startDate) {
        params = params.set('valid_from', filters.startDate);
      }
      if (filters.endDate) {
        params = params.set('valid_to', filters.endDate);
      }
      if (filters.roomTypeId) {
        params = params.set('room_type_id', filters.roomTypeId.toString());
      }
    }

    return this.http.get<OfferListItem[]>(`${this.apiUrl}`, { params });
  }

  // Customer: List available offers with filters
  listOffersCustomer(
    skip: number = 0,
    limit: number = 100,
    filters?: {
      searchTerm?: string;
      isActive?: boolean;
      minDiscount?: number;
      maxDiscount?: number;
      startDate?: string;
      endDate?: string;
      roomTypeId?: number;
      sortBy?: string;
    }
  ): Observable<OfferListItem[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString())
      .set('is_active', 'true'); // Customers only see active offers

    if (filters) {
      if (filters.searchTerm) {
        params = params.set('search', filters.searchTerm);
      }
      if (filters.isActive !== undefined) {
        params = params.set('is_active', filters.isActive.toString());
      }
      if (filters.minDiscount !== undefined) {
        params = params.set('min_discount', filters.minDiscount.toString());
      }
      if (filters.maxDiscount !== undefined) {
        params = params.set('max_discount', filters.maxDiscount.toString());
      }
      if (filters.startDate) {
        params = params.set('valid_from', filters.startDate);
      }
      if (filters.endDate) {
        params = params.set('valid_to', filters.endDate);
      }
      if (filters.roomTypeId) {
        params = params.set('room_type_id', filters.roomTypeId.toString());
      }
      if (filters.sortBy) {
        params = params.set('sort_by', filters.sortBy);
      }
    }

    return this.http.get<OfferListItem[]>(`${this.apiUrl}`, { params });
  }

  updateOffer(offerId: number, offer: OfferUpdate): Observable<Offer> {
    return this.http.put<Offer>(`${this.apiUrl}/${offerId}`, offer);
  }

  toggleOfferStatus(offerId: number, isActive: boolean): Observable<Offer> {
    return this.http.patch<Offer>(
      `${this.apiUrl}/${offerId}/status`,
      {},
      { params: new HttpParams().set('is_active', isActive.toString()) }
    );
  }

  deleteOffer(offerId: number): Observable<{ message: string; offer_id: number }> {
    return this.http.delete<{ message: string; offer_id: number }>(`${this.apiUrl}/${offerId}`);
  }

  // ===============================================
  // ROOM TYPE OPERATIONS
  // ===============================================

  getRoomTypes(): Observable<RoomType[]> {
    return this.http.get<RoomType[]>(`${environment.apiUrl}/room-management/room-types`);
  }

  getRoomTypesWithCounts(): Observable<RoomTypeWithCount[]> {
    return this.http.get<RoomTypeWithCount[]>(`${this.apiUrl}/room-types/with-counts`);
  }

  // Get available rooms for a specific room type
  getAvailableRoomsForType(roomTypeId: number): Observable<{ available_count: number }> {
    return this.http.get<{ available_count: number }>(
      `${environment.apiUrl}/room-management/room-types/${roomTypeId}/available`
    );
  }

  // ===============================================
  // MEDIA OPERATIONS (Optimized batch fetch)
  // ===============================================

  /**
   * Get images for all offers in a single optimized call.
   * This fetches all offer images at once instead of calling getOfferImages() for each offer.
   * 
   * Returns:
   * {
   *   "offer_id": {
   *     "images": [...]
   *   }
   * }
   */
  getOfferMedias(): Observable<{ [offer_id: number]: { images: any[] } }> {
    return this.http.get<{ [offer_id: number]: { images: any[] } }>(
      `${this.apiUrl}/medias`
    );
  }

  // ===============================================
  // IMAGE OPERATIONS
  // ===============================================

  uploadOfferImage(offerId: number, file: File, isPrimary: boolean = false, caption?: string): Observable<OfferImage> {
    const formData = new FormData();
    formData.append('image', file);
    if (caption) {
      formData.append('caption', caption);
    }
    formData.append('is_primary', isPrimary ? 'true' : 'false');

    return this.http.post<OfferImage>(
      `${environment.apiUrl}/images/offers/${offerId}/images`,
      formData
    );
  }

  getOfferImages(offerId: number): Observable<OfferImage[]> {
    return this.http.get<OfferImage[]>(
      `${environment.apiUrl}/images/offers/${offerId}/images`
    );
  }

  deleteOfferImage(imageId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${environment.apiUrl}/images/${imageId}`);
  }

  setOfferImageAsPrimary(offerId: number, imageId: number): Observable<{ message: string }> {
    return this.http.put<{ message: string }>(
      `${environment.apiUrl}/images/offers/${offerId}/images/${imageId}/primary`,
      {}
    );
  }

  bulkUploadOfferImages(offerId: number, files: File[], primaryIndex: number = 0): Observable<OfferImage[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('images', file);
    });
    formData.append('primary_index', primaryIndex.toString());

    return this.http.post<OfferImage[]>(
      `${environment.apiUrl}/images/offers/${offerId}/images/bulk`,
      formData
    );
  }

  // ===============================================
  // VALIDATION & CALCULATION
  // ===============================================

  validateOfferApplication(
    offerId: number,
    roomTypeId: number,
    checkDate: string
  ): Observable<{ can_apply: boolean; offer_id: number; room_type_id: number }> {
    return this.http.get<{ can_apply: boolean; offer_id: number; room_type_id: number }>(
      `${this.apiUrl}/validate/can-apply`,
      {
        params: new HttpParams()
          .set('offer_id', offerId.toString())
          .set('room_type_id', roomTypeId.toString())
          .set('check_date', checkDate),
      }
    );
  }

  calculateDiscount(
    offerId: number,
    roomTypeId: number,
    originalPrice: number,
    checkDate: string
  ): Observable<{
    original_price: number;
    discount_percent: number;
    discount_amount: number;
    discounted_price: number;
  }> {
    return this.http.post<{
      original_price: number;
      discount_percent: number;
      discount_amount: number;
      discounted_price: number;
    }>(`${this.apiUrl}/apply/calculate-discount`, null, {
      params: new HttpParams()
        .set('offer_id', offerId.toString())
        .set('room_type_id', roomTypeId.toString())
        .set('original_price', originalPrice.toString())
        .set('check_date', checkDate),
    });
  }
}
