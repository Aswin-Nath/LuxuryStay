import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface BookingResponse {
  booking_id: number;
  user_id: number;
  room_count: number;
  check_in: string; // date
  check_in_time: string; // time
  check_out: string; // date
  check_out_time: string; // time
  booking_time?: string; // timestamp when booking was created
  total_price: number;
  status: string;
  is_deleted: boolean;
  created_at?: string;
  updated_at?: string;
  primary_customer_name?: string;
  primary_customer_phone_number?: string;
  primary_customer_dob?: string;
  rooms?: BookingRoomMapResponse[];
  taxes?: BookingTaxMapResponse[];
  payments?: any[];
  issues?: any[];
}

export interface BookingRoomMapResponse {
  booking_id: number;
  room_id: number;
  room_type_id: number;
  adults: number;
  children?: number;
  is_pre_edited_room?: boolean;
  is_post_edited_room?: boolean;
  is_room_active?: boolean;
  rating_given?: number;
  guest_name?: string;
  guest_age?: number;
  special_requests?: string;
  edit_suggested_rooms?: any;
  price_per_night?: number;
}

export interface RoomTypeResponse {
  room_type_id: number;
  type_name: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  description?: string;
  square_ft?: number;
}

export interface BookingTaxMapResponse {
  booking_id: number;
  tax_id: number;
  tax_amount: number;
  created_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class BookingsService {
  private bookingApiUrl = `${environment.apiUrl}/bookings`; // Normal API for GET operations (getters)

  constructor(private http: HttpClient) {}

  // Get all bookings for current customer with advanced filtering
  // API: GET /bookings/customer (from booking.py - NORMAL endpoint)
  getCustomerBookings(
    status?: string,
    limit: number = 20,
    offset: number = 0,
    minPrice?: number,
    maxPrice?: number,
    roomTypeId?: string, // Comma-separated room type IDs
    checkInDate?: string, // YYYY-MM-DD format
    checkOutDate?: string // YYYY-MM-DD format
  ): Observable<BookingResponse[]> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    if (status) {
      params = params.set('status', status);
    }

    if (minPrice !== undefined && minPrice !== null) {
      params = params.set('min_price', minPrice.toString());
    }

    if (maxPrice !== undefined && maxPrice !== null) {
      params = params.set('max_price', maxPrice.toString());
    }

    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId);
    }

    if (checkInDate) {
      params = params.set('check_in_date', checkInDate);
    }

    if (checkOutDate) {
      params = params.set('check_out_date', checkOutDate);
    }

    return this.http.get<BookingResponse[]>(`${this.bookingApiUrl}/customer`, { params });
  }

  // Get individual booking details
  // API: GET /bookings/customer/{booking_id} (from booking.py - NORMAL endpoint)
  getBookingDetails(bookingId: number): Observable<BookingResponse> {
    return this.http.get<BookingResponse>(`${this.bookingApiUrl}/customer/${bookingId}`);
  }

  // Get all distinct booking statuses from database
  // API: GET /bookings/statuses
  getBookingStatuses(): Observable<string[]> {
    return this.http.get<string[]>(`${this.bookingApiUrl}/statuses`);
  }

  // Get room types
  // API: GET /v2/rooms/room-types
  getRoomTypes(): Observable<{ total: number; results: RoomTypeResponse[] }> {
    return this.http.get<{ total: number; results: RoomTypeResponse[] }>(
      `${environment.apiUrl}/v2/rooms/room-types`
    );
  }

  // Get payments by booking ID (from payments.py)
  // API: GET /payments/booking/{booking_id}
  getPaymentsByBooking(bookingId: number): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/payments/booking/${bookingId}`);
  }

  // Get issues by booking ID
  // API: GET /bookings/{booking_id}/issues
  getIssuesByBooking(bookingId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.bookingApiUrl}/${bookingId}/issues`);
  }

  // Get reviews by booking ID
  // API: GET /bookings/{booking_id}/reviews
  getReviewsByBooking(bookingId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.bookingApiUrl}/${bookingId}/reviews`);
  }

  // Submit a review for a booking
  // API: POST /bookings/{booking_id}/reviews
  submitReview(bookingId: number, rating: number, reviewText: string): Observable<any> {
    return this.http.post<any>(`${this.bookingApiUrl}/${bookingId}/reviews`, {
      rating,
      review_text: reviewText
    });
  }

  // Submit an issue for a booking
  // API: POST /bookings/{booking_id}/issues
  submitIssue(bookingId: number, title: string, description: string, images?: File[]): Observable<any> {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    
    if (images && images.length > 0) {
      images.forEach((image) => {
        formData.append('images', image);
      });
    }

    return this.http.post<any>(`${this.bookingApiUrl}/${bookingId}/issues`, formData);
  }

  // Cancel a booking and create refund
  // API: POST /bookings/{booking_id}/cancel
  cancelBooking(bookingId: number, reason?: string): Observable<any> {
    return this.http.post<any>(`${this.bookingApiUrl}/${bookingId}/cancel`, {});
  }

  // Get all bookings for admin (including all users)
  // API: GET /bookings/admin/list (new admin endpoint)
  getAdminBookings(
    status?: string,
    limit: number = 20,
    offset: number = 0,
    minPrice?: number,
    maxPrice?: number,
    roomTypeId?: string,
    checkInDate?: string,
    checkOutDate?: string,
  ): Observable<any> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    if (status) {
      params = params.set('status', status);
    }

    if (minPrice !== undefined && minPrice !== null) {
      params = params.set('min_price', minPrice.toString());
    }

    if (maxPrice !== undefined && maxPrice !== null) {
      params = params.set('max_price', maxPrice.toString());
    }

    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId);
    }

    if (checkInDate) {
      params = params.set('check_in_date', checkInDate);
    }

    if (checkOutDate) {
      params = params.set('check_out_date', checkOutDate);
    }


    return this.http.get<any>(`${this.bookingApiUrl}/admin`, { params });
  }

  // Get admin booking details with full information
  // API: GET /bookings/admin/{booking_id}
  getAdminBookingDetails(bookingId: number): Observable<BookingResponse> {
    return this.http.get<BookingResponse>(`${this.bookingApiUrl}/admin/${bookingId}`);
  }
}
