import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, interval, Subject } from 'rxjs';
import { map, switchMap, takeUntil, startWith, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

/**
 * OfferBookingService - Orchestrates offer-based room booking flow
 * Handles:
 * 1. Check availability for offers
 * 2. Lock rooms for offers
 * 3. Retrieve locked rooms by offer_id
 * 4. Confirm offer booking with guest details
 */

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

@Injectable({
  providedIn: 'root'
})
export class OfferBookingService {
  private apiUrl = `${environment.apiUrl}/v2/rooms/offer`;
  private readonly destroy$ = new Subject<void>();

  // 🎯 GLOBAL SESSION TIMER - Same pattern as BookingService
  // Emits remaining seconds every second (0-900 for 15-minute sessions)
  private remainingTimeSubject$ = new BehaviorSubject<number>(0);
  public remainingTime$ = this.remainingTimeSubject$.asObservable();

  // Timer state
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

  /**
   * 1️⃣ Check availability for offer
   */
  checkOfferAvailability(
    offerId: number,
    checkIn: string,
    checkOut: string
  ): Observable<OfferAvailabilityCheck> {
    return this.http.post<OfferAvailabilityCheck>(
      `${this.apiUrl}/check-availability`,
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
      `${this.apiUrl}/lock`,
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
      `${this.apiUrl}/${offerId}/locked-rooms`
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
      `${this.apiUrl}/${offerId}/booking/confirm`,
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
      `${this.apiUrl}/${offerId}/release`,
      {}
    );
  }

  /**
   * ⏱️ TIMER MANAGEMENT
   */

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
        // ✅ Emit to remainingTime$ observable (same as BookingService)
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

  /**
   * 📊 OFFER SESSION MANAGEMENT
   */

  /**
   * Initialize offer booking session
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
   * Cleanup
   */
  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
