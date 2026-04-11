import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, interval, of, Subject } from 'rxjs';
import { map, switchMap, takeUntil } from 'rxjs/operators';
import { environment } from '../../environments/environment';

// ===================================================
// BOOKING STATE INTERFACES
// ===================================================
export interface BookingState {
  checkIn?: string;
  checkOut?: string;
  roomTypeId?: number;
  offerId?: number;
}

// ===================================================
// BOOKING SESSION & ROOM INTERFACES
// ===================================================
export interface Room {
  room_id: number;
  room_no: string;
  room_type_id: number;
  type_name: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  square_ft: number;
  description: string;
  room_status: string;
  availability_count?: number;
}

export interface RoomLock {
  lock_id: number;
  room_id: number;
  room_type_id: number;
  type_name: string;
  check_in: string;
  check_out: string;
  expires_at: string;
  room_no?: string;
  price_per_night: number;
  nights?: number;
  total_price?: number;
  max_adult_count?: number;
  max_child_count?: number;
  square_ft?: number;
  description?: string;
}

export interface BookingSession {
  session_id: string;
  user_id: number;
  check_in: string;
  check_out: string;
  expiry_time: string;
  remaining_minutes: number;
  created_at: string;
  status: string;
}

export interface BookingSummary {
  total_price: number;
  taxes: number;
  final_amount: number;
  room_count: number;
  lock_ids: number[];
  rooms?: RoomLock[];
}

// ===================================================
// BOOKING RETRIEVAL INTERFACES
// ===================================================
export interface BookingResponse {
  booking_id: number;
  user_id: number;
  room_count: number;
  check_in: string;
  check_in_time: string;
  check_out: string;
  check_out_time: string;
  booking_time?: string;
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

export interface PaginatedBookingResponse {
  data: BookingResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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
export class BookingService {
  private bookingApiUrl = `${environment.apiUrl}/v2/rooms`;
  private bookingMainApiUrl = `${environment.apiUrl}/bookings`;
  private imageApiUrl = `${environment.apiUrl}/room-management`;
  private profileApiUrl = `${environment.apiUrl}/profile`;

  // ===================================================
  // STATE MANAGEMENT
  // ===================================================
  
  // Booking State (from booking-state.service)
  private bookingState$ = new BehaviorSubject<BookingState | null>(null);
  public bookingState = this.bookingState$.asObservable();

  // Session Management (from booking.service)
  private bookingSession = new BehaviorSubject<BookingSession | null>(null);
  public bookingSession$ = this.bookingSession.asObservable();

  private selectedLocks = new BehaviorSubject<RoomLock[]>([]);
  public selectedLocks$ = this.selectedLocks.asObservable();

  private remainingTime = new BehaviorSubject<number>(900);
  public remainingTime$ = this.remainingTime.asObservable();

  private isSessionExpired = new BehaviorSubject<boolean>(false);
  public isSessionExpired$ = this.isSessionExpired.asObservable();

  private timerCleanup = new Subject<void>();

  constructor(private http: HttpClient) {}

  // ===================================================
  // API URL ACCESSORS
  // ===================================================
  getBookingApiUrl(): string {
    return this.bookingApiUrl;
  }

  getImageApiUrl(): string {
    return this.imageApiUrl;
  }

  // ===================================================
  // BOOKING STATE MANAGEMENT (from booking-state.service)
  // ===================================================
  setBookingState(state: BookingState): void {
    console.log('Setting booking state:', state);
    this.bookingState$.next(state);
  }

  getBookingState(): Observable<BookingState | null> {
    return this.bookingState$.asObservable();
  }


  

  
  /**
   * Clear booking state after use
   */
  clearBookingState(): void {
    console.log('Clearing booking state');
    this.bookingState$.next(null);
  }

  // ===================================================
  // USER PROFILE
  // ===================================================
  getUserProfile() {
    return this.http.get<any>(`${this.profileApiUrl}/`);
  }
  // ===================================================
  searchRooms(
    checkIn: string,
    checkOut: string,
    filters?: {
      room_type_id?: number;
      type_name?: string;
      price_per_night_min?: number;
      price_per_night_max?: number;
      max_adult_count?: number;
      max_child_count?: number;
      square_ft_min?: number;
      square_ft_max?: number;
    }
  ): Observable<Room[]> {
    let params = new HttpParams()
      .set('check_in', checkIn)
      .set('check_out', checkOut);

    if (filters) {
      // Add filters ONLY if they have actual values (not empty string, not 0, not undefined, not null)
      // Send room_type_id (number) to backend, not type_name (string)
      if (filters.room_type_id && filters.room_type_id > 0) 
        params = params.set('room_type_id', filters.room_type_id.toString());
      
      if (filters.price_per_night_min && filters.price_per_night_min > 0) 
        params = params.set('price_per_night_min', filters.price_per_night_min.toString());
      
      if (filters.price_per_night_max && filters.price_per_night_max > 0) 
        params = params.set('price_per_night_max', filters.price_per_night_max.toString());
      
      if (filters.max_adult_count && filters.max_adult_count > 0) 
        params = params.set('max_adult_count', filters.max_adult_count.toString());
      
      if (filters.max_child_count !== undefined && filters.max_child_count > 0) 
        params = params.set('max_child_count', filters.max_child_count.toString());
      
      if (filters.square_ft_min && filters.square_ft_min > 0) 
        params = params.set('square_ft_min', filters.square_ft_min.toString());
      
      if (filters.square_ft_max && filters.square_ft_max > 0) 
        params = params.set('square_ft_max', filters.square_ft_max.toString());
    }

    console.log('🔍 Search request with params:', params.keys().map(key => `${key}=${params.get(key)}`).join('&'));

    return this.http.get<any>(`${this.bookingApiUrl}/search`, { params }).pipe(
      map(response => response.results || [])
    );
  }

  // ===================================================
  // GET ALL ROOM TYPES (For dropdown/filter)
  // ===================================================
  getAllRoomTypes(): Observable<Room[]> {
    return this.http.get<any>(`${this.bookingApiUrl}/room-types`).pipe(
      map(response => response.results || response || [])
    );
  }

  getRoomTypes(): Observable<{ total: number; results: RoomTypeResponse[] }> {
    return this.http.get<{ total: number; results: RoomTypeResponse[] }>(
      `${environment.apiUrl}/v2/rooms/room-types`
    );
  }

  // ===================================================
  // BOOKING SESSION
  // ===================================================
  createBookingSession(checkIn: string, checkOut: string): Observable<BookingSession> {
    return this.http.post<BookingSession>(
      `${this.bookingApiUrl}/booking/session`,
      { check_in: checkIn, check_out: checkOut }
    ).pipe(
      map(session => {
        this.bookingSession.next(session);
        this.startSessionTimer(session);
        return session;
      })
    );
  }

  getBookingSession(sessionId: string): Observable<BookingSession> {
    return this.http.get<BookingSession>(
      `${this.bookingApiUrl}/booking/session/${sessionId}`
    );
  }

  private startSessionTimer(session: BookingSession): void {
    // IMPORTANT: Kill all previous timers when starting a new session
    this.timerCleanup.next();
    
    // Parse expiry time with validation
    const expiryTime = new Date(session.expiry_time).getTime();
    const now = new Date().getTime();
    
    // 🚨 CRITICAL VALIDATION: Check if expiry time is valid and in the future
    if (isNaN(expiryTime)) {
      console.error('❌ INVALID EXPIRY TIME FORMAT:', session.expiry_time);
      console.error('Unable to parse timestamp. Setting 15 minutes from now as fallback.');
      const fallbackExpiry = now + (15 * 60 * 1000);
      this.startSessionTimer({ ...session, expiry_time: new Date(fallbackExpiry).toISOString() });
      return;
    }

    const timeUntilExpiry = expiryTime - now;
    
    if (timeUntilExpiry < 0) {
      console.error('❌ BACKEND RETURNED EXPIRED TIMESTAMP!');
      console.error('Expiry Time:', new Date(expiryTime).toISOString());
      console.error('Current Time:', new Date(now).toISOString());
      console.error('Time Difference (ms):', timeUntilExpiry);
      console.warn('⚠️ Using fallback: 15 minutes from now');
      
      // Fallback: Use 15 minutes from now
      const fallbackExpiry = now + (15 * 60 * 1000);
      this.startSessionTimer({ ...session, expiry_time: new Date(fallbackExpiry).toISOString() });
      return;
    }

    console.log('✅ SESSION TIMER INITIALIZED:', {
      expiry_time: session.expiry_time,
      expiry_timestamp: expiryTime,
      now_timestamp: now,
      time_until_expiry_ms: timeUntilExpiry,
      time_until_expiry_seconds: Math.floor(timeUntilExpiry / 1000),
      expiry_date: new Date(expiryTime).toISOString(),
      current_date: new Date(now).toISOString()
    });
    
    // For NEW sessions, always calculate fresh remaining time from expiry time
    const initialRemaining = Math.max(0, Math.floor((expiryTime - now) / 1000));
    
    console.log('⏱️ INITIAL REMAINING TIME:', initialRemaining, 'seconds');
    this.remainingTime.next(initialRemaining);
    
    // Create a subject to handle this specific subscription cleanup
    const timerSubject = new Subject<void>();
    
    interval(1000)
      .pipe(
        takeUntil(timerSubject),
        takeUntil(this.timerCleanup) // Also stop if timerCleanup fires (for new session)
      )
      .subscribe(() => {
        const now = new Date().getTime();
        const remaining = Math.max(0, Math.floor((expiryTime - now) / 1000));
        
        this.remainingTime.next(remaining);
        
        if (remaining <= 0) {
          console.warn('⏰ SESSION EXPIRED - Triggering session expired handler');
          this.isSessionExpired.next(true);
          timerSubject.next();
          timerSubject.complete();
        }
      });
  }

  getSessionRemainingMinutes(): number {
    return Math.ceil(this.remainingTime.getValue() / 60);
  }

  isSessionValid(): boolean {
    return this.remainingTime.getValue() > 0;
  }

  // ===================================================
  // ROOM LOCKING
  // ===================================================
  lockRoom(
    roomTypeId: number,
    checkIn: string,
    checkOut: string,
    expiresAt: string
  ): Observable<RoomLock> {
    return this.http.post<RoomLock>(
      `${this.bookingApiUrl}/lock`,
      {
        room_type_id: roomTypeId,
        check_in: checkIn,
        check_out: checkOut,
        expires_at: expiresAt
      }
    ).pipe(
      map(lock => {
        const currentLocks = this.selectedLocks.getValue();
        this.selectedLocks.next([...currentLocks, lock]);
        return lock;
      })
    );
  }

  unlockRoom(lockId: number): Observable<any> {
    return this.http.post(
      `${this.bookingApiUrl}/unlock/${lockId}`,
      {}
    ).pipe(
      map(() => {
        const currentLocks = this.selectedLocks.getValue();
        this.selectedLocks.next(
          currentLocks.filter(lock => lock.lock_id !== lockId)
        );
        return { success: true };
      })
    );
  }

  // Release all locks for current user (used when dates change)
  releaseAllLocks(): Observable<any> {
    return this.http.post(`${this.bookingApiUrl}/release-all-locks`, {}).pipe(
      map((response) => {
        // Clear all local locks
        this.selectedLocks.next([]);
        return response;
      })
    );
  }

  getMyLocks(): Observable<RoomLock[]> {
    return this.http.get<RoomLock[]>(`${this.bookingApiUrl}/my-locks`).pipe(
      map(locks => {
        this.selectedLocks.next(locks);
        return locks;
      })
    );
  }

  getSelectedLocks(): RoomLock[] {
    return this.selectedLocks.getValue();
  }

  // ===================================================
  // BOOKING SUMMARY & CONFIRMATION
  // ===================================================
  getBookingSummary(lockIds: number[]): Observable<BookingSummary> {
    const params = new HttpParams().set('lock_ids', lockIds.join(','));
    return this.http.get<BookingSummary>(
      `${this.bookingApiUrl}/booking/summary`,
      { params }
    );
  }

  // ===================================================
  // BOOKING CONFIRMATION WITH GUEST DETAILS
  // ===================================================
  confirmBooking(
    paymentMethodId: number,
    roomsGuestDetails: any[],
    upiId?: string
  ): Observable<any> {
    const payload: any = {
      payment_method_id: paymentMethodId,
      rooms_guest_details: roomsGuestDetails
    };

    // Add UPI ID if provided
    if (upiId) {
      payload.upi_id = upiId;
    }

    return this.http.post<any>(
      `${this.bookingApiUrl}/booking/confirm`,
      payload
    ).pipe(
      map(response => {
        // Clear bookings after successful confirmation
        this.selectedLocks.next([]);
        return response;
      })
    );
  }

  // ===================================================
  // HELPERS
  // ===================================================
  formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  canAddMoreRooms(): boolean {
    return this.selectedLocks.getValue().length < 5;
  }

  resetBooking(): void {
    this.selectedLocks.next([]);
    this.bookingSession.next(null);
    this.remainingTime.next(900);
    this.isSessionExpired.next(false);
  }

  // ===================================================
  // CUSTOMER BOOKINGS
  // ===================================================
  getCustomerBookings(
    status?: string,
    limit: number = 20,
    offset: number = 0,
    minPrice?: number,
    maxPrice?: number,
    roomTypeId?: string,
    checkInDate?: string,
    checkOutDate?: string
  ): Observable<PaginatedBookingResponse> {
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

    return this.http.get<PaginatedBookingResponse>(`${this.bookingMainApiUrl}/customer`, { params });
  }

  getBookingDetails(bookingId: number): Observable<BookingResponse> {
    return this.http.get<BookingResponse>(`${this.bookingMainApiUrl}/customer/${bookingId}`);
  }

  // ===================================================
  // ADMIN BOOKINGS
  // ===================================================
  getAdminBookings(
    status?: string,
    limit: number = 20,
    offset: number = 0,
    minPrice?: number,
    maxPrice?: number,
    roomTypeId?: string,
    checkInDate?: string,
    checkOutDate?: string,
  ): Observable<PaginatedBookingResponse> {
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

    return this.http.get<PaginatedBookingResponse>(`${this.bookingMainApiUrl}/admin`, { params });
  }

  getAdminBookingDetails(bookingId: number): Observable<BookingResponse> {
    return this.http.get<BookingResponse>(`${this.bookingMainApiUrl}/admin/${bookingId}`);
  }

  // ===================================================
  // BOOKING OPERATIONS
  // ===================================================
  getBookingStatuses(): Observable<string[]> {
    return this.http.get<string[]>(`${this.bookingMainApiUrl}/statuses`);
  }

  cancelBooking(bookingId: number, reason?: string): Observable<any> {
    return this.http.post<any>(`${this.bookingMainApiUrl}/${bookingId}/cancel`, {});
  }

  // ===================================================
  // RELATED DATA
  // ===================================================
  getPaymentsByBooking(bookingId: number): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiUrl}/payments/booking/${bookingId}`);
  }

  getIssuesByBooking(bookingId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.bookingMainApiUrl}/${bookingId}/issues`);
  }

  getReviewsByBooking(bookingId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.bookingMainApiUrl}/${bookingId}/reviews`);
  }
}