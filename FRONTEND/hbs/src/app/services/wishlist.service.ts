import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface WishlistItem {
  wishlist_id?: number;
  user_id?: number;
  room_type_id?: number;
  offer_id?: number;
  item_type: 'room' | 'offer';
  added_at?: string;
}

export interface WishlistToggleRequest {
  type: 'room' | 'offer';
  room_type_id?: number;
  offer_id?: number;
}

export interface WishlistToggleResponse {
  action: 'added' | 'removed';
  wishlist_id?: number;
}

@Injectable({
  providedIn: 'root',
})
export class WishlistService {
  private apiUrl = `${environment.apiUrl}/wishlist`;

  constructor(private http: HttpClient) {}

  // Get all wishlist items for current user
  getWishlist(): Observable<WishlistItem[]> {
    return this.http.get<WishlistItem[]>(`${this.apiUrl}`);
  }

  // Get wishlist rooms with full details and primary image
  getWishlistRooms(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/rooms`);
  }

  // Get wishlist offers with full details and primary image
  getWishlistOffers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/offers`);
  }

  // ============================================================
  // 🔹 UNIFIED TOGGLE ENDPOINT - Add/Remove in one call
  // ============================================================
  toggleWishlist(type: 'room' | 'offer', itemId: number): Observable<WishlistToggleResponse> {
    const payload: WishlistToggleRequest = {
      type,
      ...(type === 'room' ? { room_type_id: itemId } : { offer_id: itemId })
    };
    return this.http.post<WishlistToggleResponse>(`${this.apiUrl}/toggle`, payload);
  }

  // Add room to wishlist (deprecated - use toggleWishlist instead)
  addRoomToWishlist(room_type_id: number): Observable<WishlistItem> {
    return this.http.post<WishlistItem>(`${this.apiUrl}`, {
      room_type_id,
      item_type: 'room',
    });
  }

  // Add offer to wishlist (deprecated - use toggleWishlist instead)
  addOfferToWishlist(offer_id: number): Observable<WishlistItem> {
    return this.http.post<WishlistItem>(`${this.apiUrl}`, {
      offer_id,
      item_type: 'offer',
    });
  }

  // Remove from wishlist by wishlist_id
  removeFromWishlist(wishlist_id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${wishlist_id}`);
  }

  // Remove room from wishlist (deprecated - use toggleWishlist instead)
  removeRoomFromWishlist(room_type_id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${room_type_id}`);
  }

  // Remove offer from wishlist (deprecated - use toggleWishlist instead)
  removeOfferFromWishlist(offer_id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${offer_id}`);
  }

  // Check if item is in wishlist
  isInWishlist(room_type_id?: number, offer_id?: number): Observable<{ in_wishlist: boolean }> {
    let params = '';
    if (room_type_id) params += `room_type_id=${room_type_id}`;
    if (offer_id) params += `offer_id=${offer_id}`;
    const queryString = params ? `?${params}` : '';
    return this.http.get<{ in_wishlist: boolean }>(`${this.apiUrl}/check${queryString}`);
  }

  // Clear entire wishlist
  clearWishlist(): Observable<any> {
    return this.http.delete(`${this.apiUrl}`);
  }
}

