import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

/**
 * SharedOfferBookingService - Manages shared state across offer booking workflow
 * 
 * Flow:
 * offer-date-picker-modal → Details_Filling → Payments
 * All steps share the same offer booking state
 */

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
  providedIn: 'root'
})
export class SharedOfferBookingService {
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

  constructor() {}

  /**
   * Initialize offer booking session
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
}
