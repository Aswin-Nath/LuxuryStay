import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// Booking Response Interface
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
  edit_suggested_rooms?: any;
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
}
