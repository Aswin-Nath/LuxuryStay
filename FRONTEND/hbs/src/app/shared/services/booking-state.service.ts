import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface BookingState {
  checkIn?: string;
  checkOut?: string;
  roomTypeId?: number;
  offerId?: number;
}

@Injectable({
  providedIn: 'root'
})
export class BookingStateService {
  private bookingState$ = new BehaviorSubject<BookingState | null>(null);
  
  constructor() {}

  /**
   * Set booking state when user selects dates and initiates booking
   */
  setBookingState(state: BookingState): void {
    console.log('Setting booking state:', state);
    this.bookingState$.next(state);
  }

  /**
   * Get booking state as observable
   */
  getBookingState(): Observable<BookingState | null> {
    return this.bookingState$.asObservable();
  }

  /**
   * Get booking state value directly
   */
  getBookingStateValue(): BookingState | null {
    return this.bookingState$.value;
  }

  /**
   * Clear booking state after use
   */
  clearBookingState(): void {
    console.log('Clearing booking state');
    this.bookingState$.next(null);
  }

  /**
   * Update only dates in booking state
   */
  setDates(checkIn: string, checkOut: string): void {
    const current = this.bookingState$.value || {};
    this.bookingState$.next({
      ...current,
      checkIn,
      checkOut
    });
  }

  /**
   * Update room type filter
   */
  setRoomTypeFilter(roomTypeId: number): void {
    const current = this.bookingState$.value || {};
    this.bookingState$.next({
      ...current,
      roomTypeId
    });
  }

  /**
   * Update offer filter
   */
  setOfferFilter(offerId: number): void {
    const current = this.bookingState$.value || {};
    this.bookingState$.next({
      ...current,
      offerId
    });
  }
}
