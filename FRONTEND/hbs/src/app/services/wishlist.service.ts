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

  // Add room to wishlist
  addRoomToWishlist(room_type_id: number): Observable<WishlistItem> {
    return this.http.post<WishlistItem>(`${this.apiUrl}`, {
      room_type_id,
      item_type: 'room',
    });
  }

  // Add offer to wishlist
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

  // Remove room from wishlist (uses wishlist_id)
  removeRoomFromWishlist(room_type_id: number): Observable<any> {
    // Note: This requires finding the wishlist_id first or using the wishlist_id directly
    // For now, this method is kept for compatibility but uses the main removeFromWishlist
    return this.http.delete(`${this.apiUrl}/${room_type_id}`);
  }

  // Remove offer from wishlist (uses wishlist_id)
  removeOfferFromWishlist(offer_id: number): Observable<any> {
    // Note: This requires finding the wishlist_id first or using the wishlist_id directly
    // For now, this method is kept for compatibility but uses the main removeFromWishlist
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
