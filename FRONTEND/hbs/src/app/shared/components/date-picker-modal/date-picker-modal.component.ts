import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, SimpleChanges, OnChanges, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-date-picker-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './date-picker-modal.component.html',
  styleUrl: './date-picker-modal.component.css',
  changeDetection: ChangeDetectionStrategy.Default
})
export class DatePickerModalComponent implements OnChanges, OnInit {
  @Input() isOpen: boolean = false;
  @Input() checkIn: string = '';
  @Input() checkOut: string = '';
  @Input() error: string = '';
  @Input() roomTypeId?: number; // Optional: room_type_id for room display
  @Input() offerId?: number; // Optional: offer_id for offer display

  @Output() close = new EventEmitter<void>();
  @Output() proceed = new EventEmitter<{ checkIn: string; checkOut: string; roomTypeId?: number; offerId?: number }>();

  checkInLocal: string = '';
  checkOutLocal: string = '';
  errorLocal: string = '';

  ngOnInit(): void {
    this.syncData();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['isOpen'] && this.isOpen) {
      this.syncData();
    }
  }

  private syncData(): void {
    this.checkInLocal = this.checkIn;
    this.checkOutLocal = this.checkOut;
    this.errorLocal = this.error;
  }

  closeModal(): void {
    this.close.emit();
  }

  calculateNumberOfNights(): number {
    if (!this.checkInLocal || !this.checkOutLocal) return 0;
    const checkInDate = new Date(this.checkInLocal);
    const checkOutDate = new Date(this.checkOutLocal);
    const diffTime = checkOutDate.getTime() - checkInDate.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  proceedWithBooking(): void {
    this.errorLocal = '';

    if (!this.checkInLocal) {
      this.errorLocal = 'Please select a check-in date';
      return;
    }

    if (!this.checkOutLocal) {
      this.errorLocal = 'Please select a check-out date';
      return;
    }

    const checkInDate = new Date(this.checkInLocal);
    const checkOutDate = new Date(this.checkOutLocal);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (checkInDate < today) {
      this.errorLocal = 'Check-in date cannot be in the past';
      return;
    }

    if (checkOutDate <= checkInDate) {
      this.errorLocal = 'Check-out date must be after check-in date';
      return;
    }

    // Emit proceed with all relevant data
    this.proceed.emit({
      checkIn: this.checkInLocal,
      checkOut: this.checkOutLocal,
      roomTypeId: this.roomTypeId,
      offerId: this.offerId
    });
  }

  private formatDateForInput(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  setDefaultDates(): void {
    if (!this.checkInLocal) {
      const today = new Date();
      this.checkInLocal = this.formatDateForInput(today);
    }

    if (!this.checkOutLocal) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      this.checkOutLocal = this.formatDateForInput(tomorrow);
    }
  }
}
