import { Component, Input, Output, EventEmitter, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OfferBookingService } from '../../../services/offer-booking.service';
import { SharedOfferBookingService } from '../../../shared/services/shared-offer-booking.service';
import { ToastService } from '../../../services/toast.service';

/**
 * OfferDatePickerModal Component
 * 
 * Flow:
 * 1. User selects check-in/check-out dates and clicks "Check Availability"
 * 2. Component calls check_availability API
 * 3. If available, shows "Lock and Proceed" button
 * 4. User clicks "Lock and Proceed" → calls lock_offer API → navigates to Details_Filling
 */

@Component({
  selector: 'app-offer-date-picker-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './offer-date-picker-modal.component.html',
  styleUrls: ['./offer-date-picker-modal.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OfferDatePickerModalComponent implements OnInit {
  @Input() offerId!: number;
  @Input() offerName!: string;
  @Input() isVisible = false;

  @Output() closed = new EventEmitter<void>();
  @Output() proceedToDetails = new EventEmitter<any>();

  checkIn: string = '';
  checkOut: string = '';
  minDate: string = '';

  // Availability check
  isCheckingAvailability = false;
  availabilityChecked = false;
  isAvailable = false;
  availabilityDetails: any = null;
  availabilityError: string = '';

  // Locking rooms
  isLocking = false;
  lockingError: string = '';

  constructor(
    private offerBookingService: OfferBookingService,
    private sharedOfferBookingService: SharedOfferBookingService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.setMinDate();
    this.setDefaultDates();
  }

  /**
   * Set minimum date to today
   */
  private setMinDate(): void {
    const today = new Date();
    this.minDate = today.toISOString().split('T')[0];
  }

  /**
   * Set default dates: today and tomorrow
   */
  private setDefaultDates(): void {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    this.checkIn = today.toISOString().split('T')[0];
    this.checkOut = tomorrow.toISOString().split('T')[0];
  }

  /**
   * Validate date inputs
   */
  private validateDates(): boolean {
    if (!this.checkIn || !this.checkOut) {
      this.availabilityError = 'Please select both check-in and check-out dates';
      return false;
    }

    if (new Date(this.checkIn) >= new Date(this.checkOut)) {
      this.availabilityError = 'Check-out date must be after check-in date';
      return false;
    }

    if (new Date(this.checkIn) < new Date(this.minDate)) {
      this.availabilityError = 'Check-in date must be today or later';
      return false;
    }

    return true;
  }

  /**
   * 1️⃣ CHECK AVAILABILITY
   * Calls API to check if rooms are available for the selected dates
   */
  onCheckAvailability(): void {
    if (!this.validateDates()) {
      this.cdr.markForCheck();
      return;
    }

    this.isCheckingAvailability = true;
    this.availabilityError = '';
    this.availabilityChecked = false;
    this.cdr.markForCheck();

    this.offerBookingService.checkOfferAvailability(
      this.offerId,
      this.checkIn,
      this.checkOut
    ).subscribe({
      next: (response) => {
        this.isCheckingAvailability = false;
        this.availabilityChecked = true;
        this.isAvailable = response.overall_available;
        this.availabilityDetails = response;

        if (this.isAvailable) {
          this.toastService.success(`✅ Rooms available for the selected dates!`);
        } else {
          this.toastService.warning(`⚠️ Some room types are not available`);
        }

        this.cdr.markForCheck();
      },
      error: (err) => {
        this.isCheckingAvailability = false;
        this.availabilityError = err.error?.detail || 'Failed to check availability';
        this.toastService.error(this.availabilityError);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * 2️⃣ LOCK AND PROCEED
   * Calls API to lock all rooms for the offer, then navigates to Details_Filling
   */
  onLockAndProceed(): void {
    if (!this.isAvailable) {
      this.toastService.warning('Please check availability first');
      return;
    }

    this.isLocking = true;
    this.lockingError = '';
    this.cdr.markForCheck();

    this.offerBookingService.lockOfferRooms(
      this.offerId,
      this.checkIn,
      this.checkOut
    ).subscribe({
      next: (response) => {
        this.isLocking = false;
        this.toastService.success(`🔒 ${response.total_locked} rooms locked for 15 minutes!`);

        // Get locked room details with pricing
        this.offerBookingService.getLockedRoomsByOfferId(this.offerId).subscribe({
          next: (roomsResponse) => {
            // Initialize shared offer booking session
            this.sharedOfferBookingService.initializeOfferBooking({
              offer_id: this.offerId,
              check_in: this.checkIn,
              check_out: this.checkOut,
              locked_rooms: roomsResponse.rooms,
              total_amount: roomsResponse.total_amount_after_discount,
              expires_at: response.expires_at
            });

            // Emit event to proceed to Details_Filling
            this.proceedToDetails.emit({
              offer_id: this.offerId,
              check_in: this.checkIn,
              check_out: this.checkOut,
              locked_rooms: roomsResponse.rooms,
              expires_at: response.expires_at
            });

            // Close modal
            this.onCancel();
            this.cdr.markForCheck();
          },
          error: (err) => {
            this.lockingError = 'Failed to retrieve locked rooms';
            this.toastService.error(this.lockingError);
            this.cdr.markForCheck();
          }
        });
      },
      error: (err) => {
        this.isLocking = false;
        this.lockingError = err.error?.detail || 'Failed to lock rooms';
        this.toastService.error(this.lockingError);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Cancel modal
   */
  onCancel(): void {
    this.resetForm();
    this.closed.emit();
  }

  /**
   * Reset form
   */
  private resetForm(): void {
    this.checkIn = '';
    this.checkOut = '';
    this.availabilityChecked = false;
    this.isAvailable = false;
    this.availabilityDetails = null;
    this.availabilityError = '';
    this.lockingError = '';
  }

  /**
   * Get availability status color class
   */
  getAvailabilityStatusClass(): string {
    if (!this.availabilityChecked) return '';
    return this.isAvailable ? 'text-green-600' : 'text-red-600';
  }

  /**
   * Check if room type is available
   */
  isRoomTypeAvailable(roomType: any): boolean {
    return roomType.is_available;
  }
}
