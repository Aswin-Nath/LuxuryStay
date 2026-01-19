import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { OfferRoomDetail, OfferService, OfferBookingState } from '../../../../services/offer.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { BookingService } from '../../../../services/room-booking.service';

/**
 * OfferBookingComponent
 * 
 * Simplified offer booking flow (Date picker modal done in parent pages):
 * 1. Details Filling (Collect guest details)
 * 2. Payments (Process payment)
 * 3. Confirmation
 * 
 * Locked rooms data is passed via router state from offer-display/customer-offer-detail pages
 */

@Component({
  selector: 'app-offer-booking',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule
  ],
  templateUrl: './offer_booking.html',
  styleUrls: ['./offer_booking.css']
})
export class OfferBookingComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Offer details
  offerId!: number;
  offerName: string = '';

  // Booking flow phase
  currentPhase: 'details-filling' | 'payments' | 'confirmation' = 'details-filling';

  // Offer session state
  offerSession: OfferBookingState | null = null;

  // Timer state - EXACTLY SAME as T-component
  remainingMinutes: number = 0;
  remainingSeconds: number = 0;
  timerColor: string = 'text-green-600';

  // Confirmation state
  confirmationData: any = null;
  bookingId: number | null = null;

  // Guest details
  guestDetailsPerRoom: Map<number, any> = new Map();

  // Payment
  selectedPaymentMethod: number | null = null;
  isProcessingPayment = false;
  paymentError: string = '';

  // User details for "Use My Details" feature
  userDetails = {
    hasDob: false,
    name: '',
    age: 0 as number | null,
    usedInRoom: null as number | null
  };
  roomsUsingUserDetails: Set<number> = new Set();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private offerService: OfferService,
    private toastService: ToastService,
    private bookingService: BookingService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Load user profile details for optional use in booking
    this.loadUserDetails();

    // Get offer_id from route params
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe(params => {
      this.offerId = params['offerId'];
      this.offerName = params['offerName'] || 'Special Offer';
      this.cdr.markForCheck();
    });

    // Get locked rooms data from router state (passed from parent page)
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras?.state?.['lockedRoomsData']) {
      const lockedData = navigation.extras.state['lockedRoomsData'];
      this.offerService.initializeOfferBooking(lockedData);
      
      // Initialize timer with the locked data's expiration time
      if (lockedData.expires_at) {
        this.offerService.initializeTimerWithExpiration(lockedData.expires_at);
      }
    }

    // 🎯 SUBSCRIBE TO REMAINING TIME - EXACTLY SAME AS T-COMPONENT
    this.offerService.remainingTime$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(seconds => {
      // Update timer display properties
      this.remainingSeconds = seconds;
      this.remainingMinutes = Math.floor(seconds / 60);
      
      // Update color based on remaining time - SAME LOGIC AS T-COMPONENT
      if (seconds > 300) { // > 5 minutes
        this.timerColor = 'text-green-600';
      } else if (seconds > 120) { // > 2 minutes
        this.timerColor = 'text-yellow-600';
      } else {
        this.timerColor = 'text-red-600';
      }

      // Check if session expired
      if (seconds <= 0) {
        this.onSessionExpired();
      }

      // Trigger change detection for timer display
      this.cdr.markForCheck();
    });

    // Subscribe to shared booking state
    this.offerService.getOfferBookingState$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        this.offerSession = state;
        
        // Initialize guest details if locked rooms are available
        if (state?.locked_rooms && this.guestDetailsPerRoom.size === 0) {
          this.initializeGuestDetailsForm();
        }
        
        this.cdr.markForCheck();
      });
  }

  /**
   * Initialize guest details form for locked rooms
   */
  private initializeGuestDetailsForm(): void {
    if (this.offerSession?.locked_rooms) {
      this.offerSession.locked_rooms.forEach((room: OfferRoomDetail) => {
        if (!this.guestDetailsPerRoom.has(room.lock_id)) {
          this.guestDetailsPerRoom.set(room.lock_id, {
            lock_id: room.lock_id,
            adultName: '',
            adultAge: null,
            adultCount: 1,
            childCount: 0,
            specialRequests: ''
          });
        }
      });
    }
  }

  /**
   * ========== PHASE 1: GUEST DETAILS FILLING ==========
   */

  /**
   * Get guest details for a specific room
   */
  getGuestDetailsForRoom(lockId: number): any {
    if (!this.guestDetailsPerRoom.has(lockId)) {
      this.guestDetailsPerRoom.set(lockId, {
        lock_id: lockId,
        adultName: '',
        adultAge: null,
        adultCount: 1,
        childCount: 0,
        specialRequests: ''
      });
    }
    return this.guestDetailsPerRoom.get(lockId);
  }

  /**
   * Validate guest details for a room
   */
  private validateGuestDetails(room: any): { valid: boolean; errors: string[] } {
    const errors: string[] = [];
    const details = this.getGuestDetailsForRoom(room.lock_id);

    if (!details.adultName || details.adultName.trim().length < 2) {
      errors.push(`Room ${room.room_no}: Guest name is required (min 2 chars)`);
    }

    if (!details.adultAge || details.adultAge < 18 || details.adultAge > 120) {
      errors.push(`Room ${room.room_no}: Guest age must be between 18-120`);
    }

    if (!details.adultCount || details.adultCount < 1 || details.adultCount > room.max_adult_count) {
      errors.push(`Room ${room.room_no}: Adult count must be 1-${room.max_adult_count}`);
    }

    if (details.childCount < 0 || details.childCount > room.max_child_count) {
      errors.push(`Room ${room.room_no}: Child count must be 0-${room.max_child_count}`);
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Validate all guest details
   */
  private validateAllGuestDetails(): { valid: boolean; errors: string[] } {
    const allErrors: string[] = [];

    if (this.offerSession?.locked_rooms) {
      for (const room of this.offerSession.locked_rooms) {
        const validation = this.validateGuestDetails(room);
        allErrors.push(...validation.errors);
      }
    }

    return { valid: allErrors.length === 0, errors: allErrors };
  }

  /**
   * Proceed to payments phase
   */
  onProceedToPayments(): void {
    const validation = this.validateAllGuestDetails();

    if (!validation.valid) {
      validation.errors.forEach(err => this.toastService.error(err));
      this.cdr.markForCheck();
      return;
    }

    // Update shared state with guest details
    const guestDetails = Array.from(this.guestDetailsPerRoom.values());
    this.offerService.updateGuestDetails(guestDetails);

    this.currentPhase = 'payments';
    this.toastService.success('✅ Guest details saved!');
    this.cdr.markForCheck();
  }

  /**
   * ========== PHASE 3: PAYMENTS ==========
   */

  /**
   * Select payment method
   */
  selectPaymentMethod(methodId: number): void {
    this.selectedPaymentMethod = methodId;
    this.offerService.updatePaymentMethod(methodId);
    this.cdr.markForCheck();
  }

  /**
   * Process payment and confirm booking
   */
  onConfirmBooking(): void {
    if (!this.selectedPaymentMethod) {
      this.toastService.warning('Please select a payment method');
      return;
    }

    if (!this.offerService.isReadyForConfirmation()) {
      this.toastService.error('Booking is not ready. Please fill all required fields.');
      return;
    }

    this.isProcessingPayment = true;
    this.paymentError = '';
    this.cdr.markForCheck();

    const state = this.offerService.getCurrentState();
    const guestDetails = state.guest_details.map((detail: any) => ({
      lock_id: detail.lock_id,
      guest_name: detail.adultName,
      guest_age: detail.adultAge,
      adult_count: detail.adultCount,
      child_count: detail.childCount,
      special_requests: detail.specialRequests
    }));

    this.offerService.confirmOfferBooking(
      state.offer_id,
      this.selectedPaymentMethod!,
      guestDetails
    ).subscribe({
      next: (response) => {
        this.isProcessingPayment = false;
        this.toastService.success('🎉 Booking confirmed successfully!');

        // Store confirmation data
        this.confirmationData = response;
        this.bookingId = response.booking_id;

        // Move to confirmation phase
        this.currentPhase = 'confirmation';

        // Store confirmation details
        this.offerService.markConfirmed();

        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isProcessingPayment = false;
        this.paymentError = err.error?.detail || 'Payment processing failed';
        this.toastService.error(`❌ ${this.paymentError}`);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * ========== HELPER METHODS ==========
   */

  /**
   * Get total locked rooms
   */
  getTotalLockedRooms(): number {
    return this.offerSession?.locked_rooms.length || 0;
  }

  /**
   * Get total selected rooms
   */
  getTotalSelectedRooms(): number {
    return this.offerSession?.locked_rooms?.length || 0;
  }

  /**
   * Get remaining nights between check-in and check-out
   */
  getRemainingNights(): number {
    if (!this.offerSession?.check_in || !this.offerSession?.check_out) return 1;
    const checkIn = new Date(this.offerSession.check_in);
    const checkOut = new Date(this.offerSession.check_out);
    const nights = Math.ceil((checkOut.getTime() - checkIn.getTime()) / (1000 * 60 * 60 * 24));
    return Math.max(1, nights);
  }

  /**
   * Get remaining lock time for a room
   */
  getRemainingLockTime(expiresAt: string): string {
    const expiry = new Date(expiresAt).getTime();
    const now = new Date().getTime();
    const diff = Math.max(0, expiry - now);
    const minutes = Math.floor(diff / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  /**
   * Get total room charges
   */
  getTotalRoomCharges(): number {
    if (!this.offerSession?.locked_rooms) return 0;
    return this.offerSession.locked_rooms.reduce((total, room: any) => total + (room.final_price || 0), 0);
  }

  /**
   * Calculate GST (18%)
   */
  calculateGST(): number {
    return this.getTotalRoomCharges() * 0.18;
  }

  /**
   * Calculate total amount with GST
   */
  calculateTotalAmount(): number {
    return this.getTotalRoomCharges() + this.calculateGST();
  }

  /**
   * Check if all guest details are filled for all rooms
   */
  areAllGuestDetailsFilled(): boolean {
    if (!this.offerSession?.locked_rooms || this.offerSession.locked_rooms.length === 0) {
      return false;
    }

    for (const room of this.offerSession.locked_rooms) {
      const details = this.getGuestDetailsForRoom(room.lock_id);
      if (!details.adultName || !details.adultName.trim() ||
          !details.adultAge || details.adultAge < 18 ||
          !details.adultCount || details.adultCount < 1) {
        return false;
      }
    }
    return true;
  }

  /**
   * Get completed rooms count
   */
  getCompletedRoomsCount(): number {
    if (!this.offerSession?.locked_rooms) return 0;
    let completed = 0;
    for (const room of this.offerSession.locked_rooms) {
      const details = this.getGuestDetailsForRoom(room.lock_id);
      if (details.adultName && details.adultAge >= 18 && details.adultCount >= 1) {
        completed++;
      }
    }
    return completed;
  }

  /**
   * UPI ID validation
   */
  upiId: string = '';

  isValidUPI(upi: string): boolean {
    const upiRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z]{2,}$/;
    return upiRegex.test(upi);
  }

  /**
   * Check if payment can be processed
   */
  canProcessPayment(): boolean {
    return this.areAllGuestDetailsFilled() && (this.selectedPaymentMethod === 1 || this.selectedPaymentMethod === 3 || (this.selectedPaymentMethod === 2 && this.isValidUPI(this.upiId)));
  }

  /**
   * Get payment button disabled reason
   */
  getPaymentButtonDisabledReason(): string {
    if (!this.areAllGuestDetailsFilled()) {
      return 'Fill all guest details first';
    }
    if (!this.selectedPaymentMethod) {
      return 'Select a payment method';
    }
    if (this.selectedPaymentMethod === 2 && !this.isValidUPI(this.upiId)) {
      return 'Enter a valid UPI ID';
    }
    return '';
  }

  /**
   * Stop booking and return to offers
   */
  stopBooking(): void {
    if (confirm('Are you sure you want to cancel this booking? Your room locks will be released.')) {
      // Release locks on backend
      this.offerService.releaseOfferLocks(this.offerId).subscribe({
        next: () => {
          this.toastService.success('✅ Booking cancelled and rooms released');
          this.offerService.resetOfferBooking();
          this.guestDetailsPerRoom.clear();
          this.router.navigate(['/offers']);
        },
        error: (err) => {
          console.error('Error releasing locks:', err);
          this.toastService.error('❌ Error cancelling booking');
        }
      });
    }
  }

  /**
   * Go back to previous phase
   */
  goBack(): void {
    if (this.currentPhase === 'details-filling') {
      this.router.navigate(['/offers']);
    } else if (this.currentPhase === 'payments') {
      this.currentPhase = 'details-filling';
    }
    this.cdr.markForCheck();
  }

  // ===================================================
  // TIMER HELPER METHODS
  // ===================================================

  /**
  /**
   * Get timer display in MM:SS format - IDENTICAL TO T-COMPONENT
   */
  getTimerDisplay(): string {
    const totalSeconds = Math.max(0, this.remainingSeconds); // Ensure no negative values
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Session expired handler - IDENTICAL TO T-COMPONENT
   * Releases locks and redirects to offers page
   */
  private onSessionExpired(): void {
    alert('❌ Your offer booking session has expired. Please start over.');
    this.offerService.releaseOfferLocks(this.offerId).subscribe({
      next: () => {
        console.log('🔓 Locks released due to session expiry');
        this.router.navigate(['/offers']);
      },
      error: (err) => {
        console.error('Error releasing locks:', err);
        this.router.navigate(['/offers']);
      }
    });
  }

  /**
   * Handle timer expiration (legacy method - kept for compatibility)
   */
  private handleTimerExpiration(): void {
    this.onSessionExpired();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ===================================================
  // USER DETAILS MANAGEMENT ("Use My Details" Feature)
  // ===================================================

  // Load user profile details for optional use in one room
  loadUserDetails(): void {
    try {
      // Fetch user profile from API
      this.bookingService.getUserProfile()
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (userData) => {
            // Extract name - try multiple field names
            this.userDetails.name = userData.first_name || userData.full_name || userData.name || null;
            
            // Calculate age from DOB if available
            if (userData.dob) {
              try {
                const dob = new Date(userData.dob);
                const today = new Date();
                let age = today.getFullYear() - dob.getFullYear();
                const monthDiff = today.getMonth() - dob.getMonth();
                
                // Adjust if birthday hasn't occurred this year
                if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
                  age--;
                }
                
                this.userDetails.age = age >= 18 ? age : null;  // Only valid if 18+
                this.userDetails.hasDob = true;
                
                console.log(`👤 User details loaded: ${this.userDetails.name}, Age ${this.userDetails.age}`);
              } catch (error) {
                console.error('Error parsing DOB:', error);
                this.userDetails.hasDob = false;
              }
            } else {
              this.userDetails.hasDob = false;
              console.log('⚠️ User DOB not available - cannot use user details in booking');
            }
          },
          error: (error) => {
            console.error('Error loading user profile:', error);
          }
        });
    } catch (error) {
      console.error('Error in loadUserDetails:', error);
    }
  }

  // Apply user's own details to a room (name and age from DOB)
  applyUserDetailsToRoom(lockId: number): void {
    // Can only use user details if DOB exists
    if (!this.userDetails.hasDob || !this.userDetails.name || !this.userDetails.age) {
      alert('❌ User details incomplete. DOB is required to use your profile details.');
      return;
    }

    // Initialize guest details if not exists
    if (!this.guestDetailsPerRoom.has(lockId)) {
      this.guestDetailsPerRoom.set(lockId, {
        adultName: '',
        adultAge: 0,
        adultCount: 1,
        childCount: 0,
        specialRequests: ''
      });
    }

    const roomDetails = this.guestDetailsPerRoom.get(lockId);
    
    // Remove from previous room if it was used elsewhere
    if (this.userDetails.usedInRoom !== null && this.userDetails.usedInRoom !== lockId) {
      const previousRoom = this.guestDetailsPerRoom.get(this.userDetails.usedInRoom);
      if (previousRoom) {
        previousRoom.adultName = '';
        previousRoom.adultAge = 0;
      }
    }

    // Apply user details to this room
    if (roomDetails) {
      roomDetails.adultName = this.userDetails.name;
      roomDetails.adultAge = this.userDetails.age;
    }

    // Mark this room as using user details
    this.roomsUsingUserDetails.add(lockId);
    this.userDetails.usedInRoom = lockId;
    
    // Trigger change detection to update completion counter
    this.cdr.markForCheck();
    
    console.log(`✅ User details applied to room ${lockId}: ${this.userDetails.name}, Age ${this.userDetails.age}`);
  }

  // Clear user details from a room
  clearUserDetailsFromRoom(lockId: number): void {
    if (this.roomsUsingUserDetails.has(lockId)) {
      const roomDetails = this.guestDetailsPerRoom.get(lockId);
      if (roomDetails) {
        roomDetails.adultName = '';
        roomDetails.adultAge = 0;
      }
      this.roomsUsingUserDetails.delete(lockId);
      if (this.userDetails.usedInRoom === lockId) {
        this.userDetails.usedInRoom = null;
      }
      
      // Trigger change detection to update completion counter
      this.cdr.markForCheck();
      
      console.log(`✅ User details cleared from room ${lockId}`);
    }
  }

  // Check if a room is using user details
  isRoomUsingUserDetails(lockId: number): boolean {
    return this.roomsUsingUserDetails.has(lockId);
  }

  // ===================================================
  // CONFIRMATION NAVIGATION
  // ===================================================

  /**
   * Navigate to bookings from confirmation
   */
  goToMyBookings(): void {
    this.router.navigate(['/dashboard/bookings']);
  }

  /**
   * Start new offer booking
   */
  startNewOfferBooking(): void {
    this.router.navigate(['/offers']);
  }
}
