import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BehaviorSubject, Observable, interval, Subject } from 'rxjs';
import { map, startWith, tap, takeUntil } from 'rxjs/operators';
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

// ===================================================
// OFFER BOOKING API INTERFACES
// ===================================================
export interface OfferAvailabilityRoom {
  room_type_id: number;
  type_name: string;
  required_count: number;
  available_count: number;
  is_available: boolean;
}

export interface OfferAvailabilityCheck {
  offer_id: number;
  offer_name: string;
  check_in: string;
  check_out: string;
  overall_available: boolean;
  room_types: OfferAvailabilityRoom[];
  message: string;
}

export interface OfferLockedRoom {
  lock_id: number;
  room_id: number;
  room_no: string;
  room_type_id: number;
  offer_id: number;
  check_in: string;
  check_out: string;
  expires_at: string;
}

export interface OfferLockResponse {
  offer_id: number;
  offer_name: string;
  locked_rooms: OfferLockedRoom[];
  total_locked: number;
  expires_at: string;
  remaining_minutes: number;
  message: string;
}

export interface OfferRoomDetail {
  lock_id: number;
  room_id: number;
  room_no: string;
  room_type_id: number;
  type_name: string;
  check_in: string;
  check_out: string;
  nights: number;
  original_price_per_night: number;
  original_total: number;
  discount_percent: number;
  discount_amount: number;
  final_price: number;
  max_adult_count: number;
  max_child_count: number;
  square_ft: number;
  description: string;
  expires_at: string;
}

export interface OfferLockedRoomsResponse {
  offer_id: number;
  offer_name: string;
  total_rooms: number;
  rooms: OfferRoomDetail[];
  total_discount: number;
  total_amount_after_discount: number;
}

export interface OfferTimerState {
  remaining_minutes: number;
  remaining_seconds: number;
  expires_at: string;
  is_expired: boolean;
  percentage: number;
}

// ===================================================
// STATE MANAGEMENT INTERFACES
// ===================================================
export interface OfferBookingState {
  offer_id: number;
  check_in: string;
  check_out: string;
  locked_rooms: any[];
  guest_details: any[];
  payment_method_id: number | null;
  total_amount: number;
  gst_amount: number;
  final_amount: number;
  expires_at: string;
  is_confirmed: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class OfferService {
  private apiUrl = `${environment.apiUrl}/offers`;
  private bookingApiUrl = `${environment.apiUrl}/v2/rooms/offer`;
  private readonly destroy$ = new Subject<void>();

  // ===================================================
  // STATE MANAGEMENT
  // ===================================================
  private readonly initialState: OfferBookingState = {
    offer_id: 0,
    check_in: '',
    check_out: '',
    locked_rooms: [],
    guest_details: [],
    payment_method_id: null,
    total_amount: 0,
    gst_amount: 0,
    final_amount: 0,
    expires_at: '',
    is_confirmed: false
  };

  private offerBookingState$ = new BehaviorSubject<OfferBookingState>(this.initialState);

  // ===================================================
  // TIMER MANAGEMENT
  // ===================================================
  private remainingTimeSubject$ = new BehaviorSubject<number>(0);
  public remainingTime$ = this.remainingTimeSubject$.asObservable();

  private timerState$ = new BehaviorSubject<OfferTimerState>({
    remaining_minutes: 15,
    remaining_seconds: 900,
    expires_at: '',
    is_expired: false,
    percentage: 100
  });

  private timerSubscription$ = new Subject<void>();
  private expiryTimestamp: number = 0;

  // Offer session state
  private offerSession$ = new BehaviorSubject<{
    offer_id: number;
    check_in: string;
    check_out: string;
    locked_rooms: OfferRoomDetail[];
  } | null>(null);

  constructor(private http: HttpClient) {}

  // ===================================================
  // OFFER BOOKING API METHODS
  // ===================================================

  /**
   * 1️⃣ Check availability for offer
   */
  checkOfferAvailability(
    offerId: number,
    checkIn: string,
    checkOut: string
  ): Observable<OfferAvailabilityCheck> {
    return this.http.post<OfferAvailabilityCheck>(
      `${this.bookingApiUrl}/check-availability`,
      { offer_id: offerId, check_in: checkIn, check_out: checkOut }
    );
  }

  /**
   * 2️⃣ Lock all rooms for offer
   */
  lockOfferRooms(
    offerId: number,
    checkIn: string,
    checkOut: string
  ): Observable<OfferLockResponse> {
    return this.http.post<OfferLockResponse>(
      `${this.bookingApiUrl}/lock`,
      { offer_id: offerId, check_in: checkIn, check_out: checkOut }
    ).pipe(
      tap(response => {
        // Start 15-minute timer
        this.startOfferTimer(response.expires_at);
      })
    );
  }

  /**
   * 3️⃣ Get locked rooms by offer_id
   */
  getLockedRoomsByOfferId(offerId: number): Observable<OfferLockedRoomsResponse> {
    return this.http.get<OfferLockedRoomsResponse>(
      `${this.bookingApiUrl}/${offerId}/locked-rooms`
    );
  }

  /**
   * 4️⃣ Confirm offer booking
   */
  confirmOfferBooking(
    offerId: number,
    paymentMethodId: number,
    roomsGuestDetails: any[]
  ): Observable<any> {
    return this.http.post<any>(
      `${this.bookingApiUrl}/${offerId}/booking/confirm`,
      {
        payment_method_id: paymentMethodId,
        rooms_guest_details: roomsGuestDetails
      }
    );
  }

  /**
   * 5️⃣ Release offer locks (Cancel booking)
   */
  releaseOfferLocks(offerId: number): Observable<any> {
    return this.http.post<any>(
      `${this.bookingApiUrl}/${offerId}/release`,
      {}
    );
  }

  // ===================================================
  // TIMER MANAGEMENT METHODS
  // ===================================================

  /**
   * Start 15-minute timer for offer booking
   * Emits remaining seconds to remainingTime$ observable every second
   */
  private startOfferTimer(expiresAt: string): void {
    // Stop any existing timer
    this.timerSubscription$.next();

    // Parse expiry timestamp with validation
    const expiryTimestamp = new Date(expiresAt).getTime();
    const now = Date.now();

    // 🚨 CRITICAL VALIDATION: Check if expiry time is valid and in the future
    if (isNaN(expiryTimestamp)) {
      console.error('❌ INVALID OFFER EXPIRY TIME FORMAT:', expiresAt);
      console.error('Unable to parse timestamp. Setting 15 minutes from now as fallback.');
      const fallbackExpiry = new Date(now + 15 * 60 * 1000).toISOString();
      this.startOfferTimer(fallbackExpiry);
      return;
    }

    const timeUntilExpiry = expiryTimestamp - now;

    if (timeUntilExpiry < 0) {
      console.error('❌ BACKEND RETURNED EXPIRED OFFER TIMESTAMP!');
      console.error('Expiry Time:', new Date(expiryTimestamp).toISOString());
      console.error('Current Time:', new Date(now).toISOString());
      console.error('Time Difference (ms):', timeUntilExpiry);
      console.warn('⚠️ Using fallback: 15 minutes from now');

      // Fallback: Use 15 minutes from now
      const fallbackExpiry = new Date(now + 15 * 60 * 1000).toISOString();
      this.startOfferTimer(fallbackExpiry);
      return;
    }

    console.log('✅ OFFER SESSION TIMER INITIALIZED:', {
      expiry_time: expiresAt,
      expiry_timestamp: expiryTimestamp,
      now_timestamp: now,
      time_until_expiry_ms: timeUntilExpiry,
      time_until_expiry_seconds: Math.floor(timeUntilExpiry / 1000),
      expiry_date: new Date(expiryTimestamp).toISOString(),
      current_date: new Date(now).toISOString()
    });

    this.expiryTimestamp = expiryTimestamp;

    // Poll every second to update timer
    interval(1000)
      .pipe(
        startWith(0),
        map(() => {
          const now = Date.now();
          const diffMs = this.expiryTimestamp - now;
          const remainingSeconds = Math.max(0, Math.floor(diffMs / 1000));
          const remainingMinutes = Math.floor(remainingSeconds / 60);
          const percentage = (remainingSeconds / 900) * 100; // 900 seconds = 15 minutes

          return {
            remainingSeconds,
            remaining_minutes: remainingMinutes,
            remaining_seconds: remainingSeconds,
            expires_at: expiresAt,
            is_expired: remainingSeconds <= 0,
            percentage: Math.max(0, percentage)
          };
        }),
        takeUntil(this.timerSubscription$)
      )
      .subscribe(state => {
        // ✅ Emit to remainingTime$ observable
        this.remainingTimeSubject$.next(state.remainingSeconds);

        // Also update the detailed timerState$ for backward compatibility
        this.timerState$.next({
          remaining_minutes: state.remaining_minutes,
          remaining_seconds: state.remaining_seconds,
          expires_at: state.expires_at,
          is_expired: state.is_expired,
          percentage: state.percentage
        });

        // Auto-cleanup when expired
        if (state.is_expired) {
          console.warn('⏰ OFFER SESSION EXPIRED - Triggering expiry handler');
          this.onOfferTimerExpired();
        }
      });
  }

  /**
   * Get current timer state
   */
  getTimerState$(): Observable<OfferTimerState> {
    return this.timerState$.asObservable();
  }

  /**
   * Initialize timer with existing expiration time (called when loading from saved state)
   */
  initializeTimerWithExpiration(expiresAt: string): void {
    this.startOfferTimer(expiresAt);
  }

  /**
   * Get remaining time in readable format
   */
  getFormattedRemainingTime(): string {
    const state = this.timerState$.value;
    const mins = state.remaining_minutes;
    const secs = state.remaining_seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Called when offer booking timer expires
   */
  private onOfferTimerExpired(): void {
    console.warn('⏰ Offer booking timer expired - releasing locks');
    // Frontend should handle this by releasing locks and redirecting
  }

  // ===================================================
  // OFFER SESSION MANAGEMENT
  // ===================================================

  /**
   * Initialize offer session
   */
  initializeOfferSession(
    offerId: number,
    checkIn: string,
    checkOut: string,
    lockedRooms: OfferRoomDetail[]
  ): void {
    this.offerSession$.next({
      offer_id: offerId,
      check_in: checkIn,
      check_out: checkOut,
      locked_rooms: lockedRooms
    });
  }

  /**
   * Get offer session state
   */
  getOfferSession$(): Observable<any> {
    return this.offerSession$.asObservable();
  }

  /**
   * Clear offer session
   */
  clearOfferSession(): void {
    this.offerSession$.next(null);
  }

  /**
   * Get current offer session
   */
  getCurrentOfferSession(): any {
    return this.offerSession$.value;
  }

  /**
   * Booking state management - Initialize offer booking session
   * Called from offer-date-picker-modal after lock_offer API
   */
  initializeOfferBooking(state: Partial<OfferBookingState>): void {
    const updated = { ...this.offerBookingState$.value, ...state };
    this.offerBookingState$.next(updated);
  }

  /**
   * Update guest details
   * Called from Details_Filling component
   */
  updateGuestDetails(guestDetails: any[]): void {
    const state = this.offerBookingState$.value;
    this.offerBookingState$.next({
      ...state,
      guest_details: guestDetails
    });
  }

  /**
   * Update payment method
   * Called from Payments component
   */
  updatePaymentMethod(paymentMethodId: number): void {
    const state = this.offerBookingState$.value;
    this.offerBookingState$.next({
      ...state,
      payment_method_id: paymentMethodId
    });
  }

  /**
   * Update pricing
   * Called from Payments component to recalculate totals
   */
  updatePricing(subtotal: number, gstAmount: number): void {
    const state = this.offerBookingState$.value;
    this.offerBookingState$.next({
      ...state,
      total_amount: subtotal,
      gst_amount: gstAmount,
      final_amount: subtotal + gstAmount
    });
  }

  /**
   * Mark booking as confirmed
   * Called from Payments component after successful payment
   */
  markConfirmed(): void {
    const state = this.offerBookingState$.value;
    this.offerBookingState$.next({
      ...state,
      is_confirmed: true
    });
  }

  /**
   * Get full booking state
   */
  getOfferBookingState$(): Observable<OfferBookingState> {
    return this.offerBookingState$.asObservable();
  }

  /**
   * Get current state value
   */
  getCurrentState(): OfferBookingState {
    return this.offerBookingState$.value;
  }

  /**
   * Get specific offer_id
   */
  getOfferId(): number {
    return this.offerBookingState$.value.offer_id;
  }

  /**
   * Get locked rooms
   */
  getLockedRooms(): any[] {
    return this.offerBookingState$.value.locked_rooms;
  }

  /**
   * Get guest details
   */
  getGuestDetails(): any[] {
    return this.offerBookingState$.value.guest_details;
  }

  /**
   * Reset offer booking session
   */
  resetOfferBooking(): void {
    this.offerBookingState$.next(this.initialState);
  }

  /**
   * Check if all required fields are filled
   */
  isReadyForConfirmation(): boolean {
    const state = this.offerBookingState$.value;
    return !!(
      state.offer_id > 0 &&
      state.check_in &&
      state.check_out &&
      state.guest_details.length === state.locked_rooms.length &&
      state.payment_method_id !== null
    );
  }

  /**
   * Get booking summary for review
   */
  getBookingSummary(): any {
    const state = this.offerBookingState$.value;
    return {
      offer_id: state.offer_id,
      check_in: state.check_in,
      check_out: state.check_out,
      total_rooms: state.locked_rooms.length,
      subtotal: state.total_amount,
      gst_18_percent: state.gst_amount,
      total_amount: state.final_amount,
      expires_at: state.expires_at
    };
  }

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

  /**
   * Cleanup on destroy
   */
  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
