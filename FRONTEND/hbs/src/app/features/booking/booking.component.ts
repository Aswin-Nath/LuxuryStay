import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { BookingService, RoomLock, BookingSession, Room } from '../../services/booking.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

// Define booking phases type
type BookingPhase = 'dates' | 'search';

@Component({
  selector: 'app-booking',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './booking.component.html',
  styleUrls: ['./booking.component.css']
})
export class BookingComponent implements OnInit, OnDestroy {
  // Phases: dates | search
  currentPhase: 'dates' | 'search' = 'dates';
  
  // Template visibility flags - these trigger change detection
  showSummary: boolean = false;
  
  // Tab for summary view
  summaryTab: 'overview' | 'selected-rooms' | 'breakdown' = 'overview';

  // Booking details
  checkIn: string = '';
  checkOut: string = '';
  previousCheckIn: string = '';  // Track previous dates to detect changes
  previousCheckOut: string = '';
  bookingSession: BookingSession | null = null;
  selectedLocks: RoomLock[] = [];

  // Cart-like room selection
  roomCart: { [key: string]: { count: number; roomType: any; locks: RoomLock[] } } = {};
  availableRoomTypes: any[] = [];  // Room types with availability counts
  isLoadingRoomTypes = false;

  // Search state
  searchResults: Room[] = [];
  isSearching = false;
  searchError: string = '';

  // No payment information needed for room picker only

  // Search filters
  searchFilters: any = {
    type_name: '',
    price_per_night_min: undefined,
    price_per_night_max: undefined,
    max_adult_count: undefined,
    max_child_count: undefined,
    square_ft_min: undefined,
    square_ft_max: undefined
  };

  // Summary state
  bookingSummary: any = null;
  isSummaryLoading = false;

  // No payment state needed for room picker only

  // Timer state
  remainingMinutes: number = 0;
  remainingSeconds: number = 0;
  timerColor: string = 'text-green-500'; // green > yellow > red
  isTimerRunning: boolean = false;

  private destroy$ = new Subject<void>();
  private paymentPollInterval: any;

  constructor(
    public bookingService: BookingService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Subscribe to remaining time - THIS STARTS THE TIMER
    this.bookingService.remainingTime$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(seconds => {
      this.isTimerRunning = true;
      this.remainingSeconds = seconds;
      this.remainingMinutes = Math.floor(seconds / 60);
      
      // Update color based on remaining time
      if (seconds > 300) { // > 5 minutes
        this.timerColor = 'text-green-500';
      } else if (seconds > 120) { // > 2 minutes
        this.timerColor = 'text-yellow-500';
      } else {
        this.timerColor = 'text-red-500';
      }

      // Check if session expired
      if (seconds <= 0) {
        this.onSessionExpired();
      }
    });

    // Subscribe to selected locks (but don't overwrite during summary/payment phases)
    this.bookingService.selectedLocks$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(locks => {
      // Only update selectedLocks if we're in search phase to avoid conflicts
      if (this.currentPhase === 'search') {
        this.selectedLocks = locks;
      }
    });

    // Initialize date range (default: today to tomorrow)
    const today = new Date().toISOString().split('T')[0];
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    this.checkIn = today;
    this.checkOut = tomorrow;
    this.previousCheckIn = today;
    this.previousCheckOut = tomorrow;
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ===================================================
  // PHASE: DATES (Page 1 - Select dates)
  // ===================================================
  proceedWithDates(): void {
    if (!this.checkIn || !this.checkOut) {
      this.searchError = 'Please select check-in and check-out dates';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.searchError = 'Check-out date must be after check-in date';
      return;
    }

    // Store current dates as previous dates for change detection
    this.previousCheckIn = this.checkIn;
    this.previousCheckOut = this.checkOut;
    this.searchError = '';

    // Create booking session
    this.bookingService.createBookingSession(this.checkIn, this.checkOut)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (session) => {
          this.bookingSession = session;
          this.searchError = '';
          
          // Move to search phase and load room types
          this.currentPhase = 'search';
          this.loadAvailableRoomTypes();
        },
        error: (err) => {
          this.searchError = 'Failed to create booking session: ' + err.error?.detail;
        }
      });
  }

  // ===================================================
  // DETECT DATE CHANGES - Auto-unlock rooms if dates change
  // ===================================================
  onDateChange(): void {
    // If user changes dates while on search page, unlock all rooms and reset
    if (this.currentPhase === 'search' && (this.checkIn !== this.previousCheckIn || this.checkOut !== this.previousCheckOut)) {
      if (this.getTotalSelectedRooms() > 0) {
        this.releaseAllLocksOnDateChange();
      }
      // Update previous dates
      this.previousCheckIn = this.checkIn;
      this.previousCheckOut = this.checkOut;
    }
  }

  releaseAllLocksOnDateChange(): void {
    this.bookingService.releaseAllLocks()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('All locks released on date change:', response);
          // Clear local cart and locks
          this.roomCart = {};
          this.selectedLocks = [];
          // Reset search filters
          this.searchFilters = {
            type_name: '',
            price_per_night_min: undefined,
            price_per_night_max: undefined,
            max_adult_count: undefined,
            max_child_count: undefined,
            square_ft_min: undefined,
            square_ft_max: undefined
          };
          alert('Dates changed! All previously locked rooms have been unlocked. Please start fresh.');
        },
        error: (err) => {
          console.error('Failed to release locks:', err);
          alert('Error releasing rooms. Please try again.');
        }
      });

    alert('Dates changed! All previously locked rooms have been unlocked. Please start fresh.');
  }

  // ===================================================
  // CART-LIKE ROOM SELECTION SYSTEM
  // ===================================================
  
  // Increase room count for a specific room type
  increaseRoomCount(roomType: any): void {
    const typeKey = roomType.type_name;
    
    // Check if we can add more rooms
    if (!this.roomCart[typeKey]) {
      this.roomCart[typeKey] = { count: 0, roomType: roomType, locks: [] };
    }
    
    const currentCount = this.roomCart[typeKey].count;
    const availableCount = roomType.free_rooms - currentCount;
    const totalSelectedRooms = this.getTotalSelectedRooms();
    
    // Validation: Can't exceed available rooms or total limit of 5
    if (availableCount <= 0) {
      alert(`No more ${roomType.type_name} rooms available!`);
      return;
    }
    
    if (totalSelectedRooms >= 5) {
      alert('Maximum 5 rooms allowed per booking!');
      return;
    }
    
    // Lock a room of this type
    this.lockRoomOfType(roomType)
      .then((lock) => {
        if (lock) {
          this.roomCart[typeKey].count++;
          this.roomCart[typeKey].locks.push(lock);
          this.updateSelectedLocks();
        }
      })
      .catch((error) => {
        console.error('Failed to lock room:', error);
        alert('Failed to lock room. Please try again.');
      });
  }
  
  // Decrease room count for a specific room type
  decreaseRoomCount(roomType: any): void {
    const typeKey = roomType.type_name;
    
    if (!this.roomCart[typeKey] || this.roomCart[typeKey].count <= 0) {
      return; // Nothing to decrease
    }
    
    // Get the last locked room of this type
    const locks = this.roomCart[typeKey].locks;
    const lastLock = locks.pop();
    
    if (lastLock) {
      // Unlock the room
      this.bookingService.unlockRoom(lastLock.lock_id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.roomCart[typeKey].count--;
            
            // Remove from cart if count reaches 0
            if (this.roomCart[typeKey].count === 0) {
              delete this.roomCart[typeKey];
            }
            
            this.updateSelectedLocks();
          },
          error: (err) => {
            console.error('Failed to unlock room:', err);
            // Re-add the lock back to the array if unlock failed
            this.roomCart[typeKey].locks.push(lastLock);
          }
        });
    }
  }
  
  // Lock a specific room of given type
  private lockRoomOfType(roomType: any): Promise<RoomLock | null> {
    return new Promise((resolve, reject) => {
      if (!this.bookingSession) {
        reject('Booking session not initialized');
        return;
      }
      
      // Calculate expiry (15 minutes from now)
      const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString();
      
      this.bookingService.lockRoom(
        roomType.room_type_id,
        this.checkIn,
        this.checkOut,
        expiresAt
      ).pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (lock) => {
            resolve(lock);
          },
          error: (err) => {
            reject(err);
          }
        });
    });
  }
  
  // Update the selectedLocks array from cart data
  private updateSelectedLocks(): void {
    this.selectedLocks = [];
    Object.values(this.roomCart).forEach(cartItem => {
      this.selectedLocks.push(...cartItem.locks);
    });
  }
  
  // Get total count of selected rooms across all types
  getTotalSelectedRooms(): number {
    return Object.values(this.roomCart).reduce((total, item) => total + item.count, 0);
  }
  
  // Get count for specific room type
  getRoomTypeCount(roomTypeName: string): number {
    return this.roomCart[roomTypeName]?.count || 0;
  }
  
  // Get available count for specific room type (considering current selections)
  getAvailableCount(roomType: any): number {
    const currentCount = this.getRoomTypeCount(roomType.type_name);
    return roomType.free_rooms - currentCount;
  }
  
  // Clear all selections using API
  clearAllSelections(): void {
    if (this.getTotalSelectedRooms() > 0) {
      this.bookingService.releaseAllLocks()
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (response) => {
            console.log('All selections cleared:', response);
            // Clear local cart and locks
            this.roomCart = {};
            this.selectedLocks = [];
          },
          error: (err) => {
            console.error('Failed to clear selections:', err)
            // Fallback: clear locally anyway
            this.roomCart = {};
            this.selectedLocks = [];
          }
        });
    }
  }
  
  // Get total price for all selected rooms
  getTotalPrice(): number {
    return Object.values(this.roomCart).reduce((total, item) => {
      return total + (item.count * item.roomType.price_per_night);
    }, 0);
  }

  // ===================================================
  // BOOKING COMPLETION (Simplified)
  // ===================================================
  
  completeRoomSelection(): void {
    if (this.getTotalSelectedRooms() === 0) {
      alert('Please select at least one room');
      return;
    }
    
    // For now, just show success message
    alert(`Successfully selected ${this.getTotalSelectedRooms()} room(s) for ${this.calculateNumberOfNights()} night(s)!\nTotal: ₹${this.getTotalPrice() * this.calculateNumberOfNights()}`);
  }

  startNewBooking(): void {
    // Reset all data
    this.currentPhase = 'dates';
    this.showSummary = false;
    this.checkIn = '';
    this.checkOut = '';
    this.roomCart = {};
    this.selectedLocks = [];
    this.cdr.markForCheck();
    this.cdr.detectChanges();
  }

  // Helper method for phase checking - REMOVED TO FIX RENDERING ISSUE
  // Use direct currentPhase === 'phase' comparison in templates instead

  // ===================================================
  // PHASE: SEARCH (Page 2 - Select rooms)
  // ===================================================
  loadAvailableRoomTypes(): void {
    // Load room types with availability for search page display
    this.isLoadingRoomTypes = true;
    this.bookingService.searchRooms(this.checkIn, this.checkOut, {})
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (rooms) => {
          this.availableRoomTypes = rooms;
          this.isLoadingRoomTypes = false;
        },
        error: (err) => {
          console.error('Failed to load room types:', err);
          this.isLoadingRoomTypes = false;
        }
      });
  }

  // ===================================================
  // PHASE: SEARCH - Continue with booking
  // ===================================================
  startBooking(): void {
    if (!this.checkIn || !this.checkOut) {
      this.searchError = 'Please select check-in and check-out dates';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.searchError = 'Check-out date must be after check-in date';
      return;
    }

    // Create booking session
    this.bookingService.createBookingSession(this.checkIn, this.checkOut)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (session) => {
          this.bookingSession = session;
          this.searchError = '';
          this.performSearch();
        },
        error: (err) => {
          this.searchError = 'Failed to create booking session: ' + err.error?.detail;
        }
      });
  }

  performSearch(): void {
    if (!this.checkIn || !this.checkOut) return;

    this.isSearching = true;
    this.searchError = '';

    this.bookingService.searchRooms(this.checkIn, this.checkOut, this.searchFilters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (rooms) => {
          this.searchResults = rooms;
          this.availableRoomTypes = rooms;  // Update room types list too
          this.isSearching = false;
        },
        error: (err) => {
          this.searchError = 'Failed to search rooms: ' + err.error?.detail;
          this.isSearching = false;
        }
      });
  }

  // ===================================================
  // PHASE: SELECTION (Lock rooms)
  // ===================================================
  addRoomToBooking(room: Room): void {
    if (!this.bookingService.canAddMoreRooms()) {
      alert('Maximum 5 rooms allowed per booking');
      return;
    }

    if (!this.bookingSession) {
      alert('Booking session not initialized');
      return;
    }

    // Calculate expiry (15 minutes from now)
    const expiresAt = new Date(Date.now() + 15 * 60 * 1000).toISOString();

    this.bookingService.lockRoom(
      room.room_type_id,
      this.checkIn,
      this.checkOut,
      expiresAt
    ).pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (lock) => {
          // Successfully locked - stay on search phase, room added to sidebar
        },
        error: (err) => {
          alert('Failed to lock room: ' + err.error?.detail);
        }
      });
  }

  removeRoom(lockId: number): void {
    this.bookingService.unlockRoom(lockId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.updateSummary();
        },
        error: (err) => {
          alert('Failed to remove room: ' + err.error?.detail);
        }
      });
  }

  // COMMENTED OUT: proceedToSummary() - now going directly to payment
  // proceedToSummary(): void {
  //   console.log('🚀 proceedToSummary called');
  //   console.log('Total selected rooms:', this.getTotalSelectedRooms());
  //   
  //   if (this.getTotalSelectedRooms() === 0) {
  //     alert('Please select at least one room');
  //     return;
  //   }

  //   console.log('✅ Cart has rooms, proceeding...');
  //   
  //   // Update selectedLocks from shopping cart before calling updateSummary
  //   this.updateSelectedLocks();
  //   console.log('Updated selectedLocks, count:', this.selectedLocks.length);
  //   
  //   // Move to summary phase
  //   console.log('Setting currentPhase to summary');
  //   this.currentPhase = 'summary';
  //   this.showSummary = true;
  //   this.showPayment = false;
  //   this.showConfirmation = false;
  //   console.log('✅ currentPhase is now:', this.currentPhase, 'showSummary:', this.showSummary);
  //   
  //   // Mark component for check and trigger change detection
  //   this.cdr.markForCheck();
  //   this.cdr.detectChanges();
  //   console.log('✅ Change detection triggered');
  //   
  //   // Load the summary data
  //   this.updateSummary();
  //   console.log('✅ updateSummary called');
  // }

  // ===================================================
  // PHASE: SUMMARY
  // ===================================================
  updateSummary(): void {
    if (this.selectedLocks.length === 0) return;

    this.isSummaryLoading = true;
    const lockIds = this.selectedLocks.map(lock => lock.lock_id);

    this.bookingService.getBookingSummary(lockIds)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (summary) => {
          this.bookingSummary = summary;
          this.isSummaryLoading = false;
        },
        error: (err) => {
          alert('Failed to calculate summary: ' + err.error?.detail);
          this.isSummaryLoading = false;
        }
      });
  }

  // ===================================================
  // PHASE NAVIGATION
  // ===================================================

  // Payment polling and booking confirmation removed - keeping only room selection

  // ===================================================
  // ERROR HANDLING
  // ===================================================
  private onSessionExpired(): void {
    alert('❌ Your booking session has expired. Please start over.');
    this.resetBooking();
    this.router.navigate(['/dashboard']);
  }

  private resetBooking(): void {
    this.bookingService.resetBooking();
    this.currentPhase = 'search';
    this.bookingSession = null;
    this.selectedLocks = [];
    this.bookingSummary = null;
  }

  goBack(): void {
    if (this.currentPhase === 'dates') {
      this.router.navigate(['/dashboard']);
    } else if (this.currentPhase === 'search') {
      this.currentPhase = 'dates';
      this.showSummary = false;
    }
    this.cdr.markForCheck();
    this.cdr.detectChanges();
  }

  formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  getRoomDetails(lock: RoomLock): string {
    return `${lock.type_name} - Room ${lock.room_no} (₹${lock.price_per_night}/night)`;
  }

  calculateNumberOfNights(): number {
    if (!this.checkIn || !this.checkOut) return 1;
    const start = new Date(this.checkIn);
    const end = new Date(this.checkOut);
    return Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
  }

  getRoomTotalPrice(lock: RoomLock): number {
    // Use pre-calculated total_price if available, otherwise calculate
    return lock.total_price || ((lock.price_per_night || 0) * this.calculateNumberOfNights());
  }

  getTotalRoomCharges(): number {
    return this.selectedLocks.reduce((sum, lock) => sum + this.getRoomTotalPrice(lock), 0);
  }

  calculateTaxes(): number {
    return this.getTotalRoomCharges() * 0.18; // 18% GST
  }

  getTotalAmount(): number {
    return this.getTotalRoomCharges() + this.calculateTaxes();
  }

  getTimerDisplay(): string {
    const mins = this.remainingMinutes.toString().padStart(2, '0');
    const secs = (this.remainingSeconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  }

  goToDashboard(): void {
    this.resetBooking();
    this.router.navigate(['/dashboard']);
  }
}
