import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { BookingService, RoomLock, BookingSession, Room } from '../../services/booking.service';
import { BookingStateService } from '../../services/booking-state.service';
import { ToastService } from '../../services/toast.service';
import { RoomCardComponent } from './room-card/room-card.component';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

// Define booking phases - numeric for simplicity
type Phase = 0 | 1 | 2 | 3;

// Phase constants
const PHASES = {
  DATES: 0,
  SEARCH_AND_DETAILS: 1,
  PAYMENT: 2,
  CONFIRMATION: 3
} as const;

// Guest details per room
export interface RoomGuestDetails {
  lockId: number;
  adultName: string;
  adultAge: number;
  specialRequests: string;
  adultCount: number;  // Number of adults staying
  childCount: number;  // Number of children staying
}

@Component({
  selector: 'app-booking',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, RoomCardComponent],
  templateUrl: './booking.component.html',
  styleUrls: ['./booking.component.css']
})
export class BookingComponent implements OnInit, OnDestroy {
  // Make PHASES available to template with explicit typing
  readonly PHASES: typeof PHASES = PHASES;
  
  // Clean getter-based phase checkers (safe for templates, no method calls)
  get isDatesPhase(): boolean {
    return this.currentPhase === PHASES.DATES;
  }

  get isSearchPhase(): boolean {
    return this.currentPhase === PHASES.SEARCH_AND_DETAILS;
  }

  get isPaymentPhase(): boolean {
    const result = this.currentPhase === PHASES.PAYMENT;
    if (result) {
      console.log('🎯 isPaymentPhase getter TRUE - rendering payment phase');
    }
    return result;
  }
  
  // Phases: dates | search-and-details | payment
  currentPhase: Phase = PHASES.DATES;
  
  // Track if booking is started (to show date modal or full page)
  bookingStarted: boolean = false;
  
  // Modal-specific flag for date picker
  showDatePickerModal: boolean = false;
  
  // Template visibility flags
  showSummary: boolean = false;
  
  // Track if booking was started from navbar (no dates provided)
  private fromNavbar: boolean = false;
  
  // Tab for summary view
  summaryTab: 'overview' | 'selected-rooms' | 'breakdown' = 'overview';

  // Booking details
  checkIn: string = '';
  checkOut: string = '';
  previousCheckIn: string = '';
  previousCheckOut: string = '';
  lastChangedDate: string = ''; // Track when dates were last changed for Search
  bookingSession: BookingSession | null = null;
  selectedLocks: RoomLock[] = [];
  
  // Track if dates have been selected (to decide whether to show date picker on return)
  datesSelected: boolean = false;
  
  // Booking start time - used for lock expiry calculation
  bookingStartTime: Date | null = null;
  
  // Previous session ID - for cleanup when dates change
  previousSessionId: string | null = null;

  // Cart-like room selection
  roomCart: { [key: string]: { count: number; roomType: any; locks: RoomLock[] } } = {};
  availableRoomTypes: any[] = [];  // For displaying search results
  allRoomTypesForDropdown: any[] = [];  // ALL room types from DB - for dropdown filter
  isLoadingRoomTypes = false;

  // Search state
  searchResults: Room[] = [];
  isSearching = false;
  searchError: string = '';

  // Search filters
  searchFilters: any = {
    room_type_id: null,  // Changed from type_name to room_type_id (send ID to backend, not name)
    price_per_night_min: undefined,
    price_per_night_max: undefined,
    max_adult_count: undefined,
    max_child_count: undefined,
    square_ft_min: undefined,
    square_ft_max: undefined
  };

  // Tracking parameters from query params (room_type_id or offer_id)
  selectedRoomTypeIdFromQuery: number | null = null;
  selectedOfferIdFromQuery: number | null = null;
  
  // Track which room is being booked (for spinner)
  bookingRoomType: string | null = null;
  isBookingRoom: boolean = false;
  bookingError: string = '';
  bookingSuccess: string = '';
  
  // Payment method selection
  selectedPaymentMethod: 'card' | 'upi' | 'netbanking' | null = null;
  isProcessingPayment: boolean = false;
  upiId: string = '';  // Store UPI ID for UPI payments
  
  // Modal for changing dates in search phase
  showChangeDatesModal: boolean = false;

  // Guest Details per room (stored locally, NOT sent to backend yet)
  roomGuestDetails: { [lockId: number]: RoomGuestDetails } = {};

  // Primary user details (for option to use in one room)
  userDetails: {
    name: string | null;
    age: number | null;
    hasDob: boolean;
    usedInRoom: number | null;  // Track which room is using user details (null = none, only one room can use it)
  } = {
    name: null,
    age: null,
    hasDob: false,
    usedInRoom: null
  };

  // Summary state
  bookingSummary: any = null;
  isSummaryLoading = false;

  // Timer state
  remainingMinutes: number = 0;
  remainingSeconds: number = 0;
  timerColor: string = 'text-green-500';

  // Confirmation phase state
  confirmationData: any = null;
  bookingId: number | null = null;
  isTimerRunning: boolean = false;
  
  // Lock expiry tracking
  lockExpiryTimes: { [lockId: number]: { seconds: number; color: string } } = {};

  private destroy$ = new Subject<void>();
  private paymentPollInterval: any;
  
  // Protection flags for date change logic
  private isInitialLoad = true;
  private isProcessingDateChange = false;
  
  // Track previous page for cancel navigation
  previousPage = '/';

  constructor(
    public bookingService: BookingService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private bookingStateService: BookingStateService,
    private toastService: ToastService
  ) {
    // Get previousPage from router state
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras?.state?.['from']) {
      this.previousPage = navigation.extras.state['from'];
    }
  }

  ngOnInit(): void {
    // Load user profile details for optional use in booking
    this.loadUserDetails();

    // Load ALL room types from database (for dropdown - ALWAYS show all types)
    this.bookingService.getAllRoomTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (roomTypes) => {
          console.log('📋 Loaded all room types for dropdown:', roomTypes);
          this.allRoomTypesForDropdown = roomTypes;  // Store in separate array
        },
        error: (err) => {
          console.error('Failed to load room types:', err);
        }
      });

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

      // Trigger change detection for timer display
      this.cdr.markForCheck();
    });

    // Subscribe to selected locks (but don't overwrite during payment phase)
    this.bookingService.selectedLocks$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(locks => {
      // Update selectedLocks in both search-and-details and payment phases
      if (this.currentPhase === PHASES.SEARCH_AND_DETAILS || this.currentPhase === PHASES.PAYMENT) {
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

   // Subscribe to booking state service (replaces query params)
    this.bookingStateService.getBookingState()
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        if (!state) return;

        const checkIn = state.checkIn;
        const checkOut = state.checkOut;
        const roomTypeId = state.roomTypeId;
        const offerId = state.offerId;

        console.log('Booking state received:', { checkIn, checkOut, roomTypeId, offerId, phase: this.currentPhase });

    // Only act if we have valid dates (ALWAYS accept new dates, even if datesSelected was true from previous booking)
        if (checkIn && checkOut) {
          console.log('Valid dates found in state → applying and proceeding');
          this.checkIn = checkIn;
          this.checkOut = checkOut;
          this.previousCheckIn = checkIn;
          this.previousCheckOut = checkOut;
          this.datesSelected = true;

          // If roomTypeId is provided, store it for auto-lock but DON'T filter search
          if (roomTypeId) {
            this.selectedRoomTypeIdFromQuery = roomTypeId;
            console.log('Room type ID stored for auto-lock:', roomTypeId);
          }

          // If offerId is provided, store it for later use
          if (offerId) {
            this.selectedOfferIdFromQuery = offerId;
            console.log('Offer ID received:', offerId);
          }

          // Clear state from service after using it
          this.bookingStateService.clearBookingState();

          // Only proceed if we're still in DATES phase
          if (this.currentPhase === PHASES.DATES) {
            this.proceedFromDateModal();
          }
          return; // Exit early
        }

        // Only show modal if:
        // - No dates in state
        // - We are in DATES phase
        // - We haven't already selected dates
        // - This is likely a fresh visit
        if (!checkIn && !checkOut && this.currentPhase === PHASES.DATES && !this.datesSelected) {
          console.log('No dates in state → showing modal (fresh visit)');
          this.openDatePickerModal();
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ===================================================
  // DATE PICKER MODAL METHODS
  // ===================================================
  openDatePickerModal(): void {
    this.showDatePickerModal = true;
    this.bookingStarted = true;
  }

  closeeDatePickerModal(): void {
    this.showDatePickerModal = false;
    // Navigate to previous page or home if from navbar
    if (this.fromNavbar) {
      this.router.navigate([this.previousPage]);
    }
  }

  proceedFromDateModal(): void {
    if (!this.checkIn || !this.checkOut) {
      this.searchError = 'Please select check-in and check-out dates';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.searchError = 'Check-out date must be after check-in date';
      return;
    }

    // Store current dates as previous dates
    this.previousCheckIn = this.checkIn;
    this.previousCheckOut = this.checkOut;
    this.searchError = '';
    this.datesSelected = true;

    // Create booking session and go directly to search phase
    this.bookingService.createBookingSession(this.checkIn, this.checkOut)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (session) => {
          this.bookingSession = session;
          this.searchError = '';
          this.showDatePickerModal = false;
          
          // Move to search-and-details phase
          this.currentPhase = PHASES.SEARCH_AND_DETAILS;
          // This will load room types and auto-lock if needed
          this.loadAvailableRoomTypesWithFilters();
        },
        error: (err) => {
          this.searchError = 'Failed to create booking session: ' + err.error?.detail;
        }
      });
  }

  // Attempt to auto-lock a specific room type if provided
  private attemptAutoLockRoomType(): void {
    if (!this.selectedRoomTypeIdFromQuery || !this.availableRoomTypes.length) {
      return;
    }

    const requestedRoomType = this.availableRoomTypes.find(
      rt => rt.room_type_id === this.selectedRoomTypeIdFromQuery
    );

    if (!requestedRoomType) {
      this.toastService.error(`Requested room type is not available for your selected dates`);
      this.searchError = `Requested room type is not available for your selected dates. Here are other rooms you can book:`;
      this.selectedRoomTypeIdFromQuery = null;
      this.searchFilters.room_type_id = null;
      return;
    }

    // Check if room type has available rooms
    if (!requestedRoomType.free_rooms || requestedRoomType.free_rooms <= 0) {
      this.toastService.error(`No ${requestedRoomType.type_name} rooms available for your selected dates`);
      this.searchError = `No ${requestedRoomType.type_name} rooms available for your selected dates. Here are other rooms you can book:`;
      this.selectedRoomTypeIdFromQuery = null;
      this.searchFilters.room_type_id = null;
      return;
    }

    // Auto-lock the room
    this.bookingRoomType = requestedRoomType.type_name;
    this.isBookingRoom = true;
    this.lockRoomOfType(requestedRoomType)
      .then((lock) => {
        if (lock) {
          // Successfully locked - update cart with consistent key format
          const cartKey = `room_${requestedRoomType.room_type_id}`;
          if (!this.roomCart[cartKey]) {
            this.roomCart[cartKey] = { count: 0, roomType: requestedRoomType, locks: [] };
          }
          this.roomCart[cartKey].count += 1;
          this.roomCart[cartKey].locks.push(lock);
          
          // CRITICAL: Initialize guest details for auto-locked room
          this.initializeGuestDetailsForRoom(lock);
          
          // Update selected locks
          this.updateSelectedLocks();
          this.searchError = '';
          this.isBookingRoom = false;
          this.bookingRoomType = null;
          this.toastService.success(`✅ ${requestedRoomType.type_name} room locked successfully!`);
          console.log(`✅ Auto-locked 1x ${requestedRoomType.type_name}`);
          this.cdr.markForCheck();
        }
      })
      .catch((err) => {
        this.toastService.error(`Unable to lock ${requestedRoomType.type_name}`);
        this.searchError = `Unable to lock ${requestedRoomType.type_name}. ${err}`;
        this.isBookingRoom = false;
        this.bookingRoomType = null;
      });
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
    this.datesSelected = true; // Mark dates as selected

    // Create booking session
    this.bookingService.createBookingSession(this.checkIn, this.checkOut)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (session) => {
          this.bookingSession = session;
          this.searchError = '';
          
          // Move to search-and-details phase and load room types
          this.currentPhase = PHASES.SEARCH_AND_DETAILS;
          this.loadAvailableRoomTypesWithFilters();
        },
        error: (err) => {
          this.searchError = 'Failed to create booking session: ' + err.error?.detail;
        }
      });
  }

  // ===================================================
  // NAVIGATE TO SEARCH WITHOUT CHANGING DATES
  // ===================================================
  goToSearchFromDates(): void {
    if (!this.checkIn || !this.checkOut) {
      this.searchError = 'Please select check-in and check-out dates first';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.searchError = 'Check-out date must be after check-in date';
      return;
    }

    // Store current dates as previous dates for this navigation (no date change triggered)
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
          
          // Move to search-and-details phase and load room types
          this.currentPhase = PHASES.SEARCH_AND_DETAILS;
          this.loadAvailableRoomTypes();
        },
        error: (err) => {
          this.searchError = 'Failed to create booking session: ' + err.error?.detail;
        }
      });
  }

  // ===================================================
  // SEARCH AVAILABLE ROOMS - WITH FILTERS AND DATE CHANGE DETECTION
  // ===================================================
  searchAvailableRooms(): void {
    // Check if dates have changed since last search
    const datesChanged = this.checkIn !== this.previousCheckIn || this.checkOut !== this.previousCheckOut;
    
    // If dates changed and we have locked rooms, release them first
    if (datesChanged && this.getTotalSelectedRooms() > 0) {
      console.log('Dates changed from:', this.previousCheckIn, this.previousCheckOut, 'to:', this.checkIn, this.checkOut);
      console.log('Total selected rooms:', this.getTotalSelectedRooms());
      console.log('Releasing rooms before new search...');
      this.releaseAllLocksOnDateChange();
    } else {
      // No date change, just load rooms with filters
      this.loadAvailableRoomTypesWithFilters();
    }
  }

  // ===================================================
  // OPEN/CLOSE CHANGE DATES MODAL
  // ===================================================
  openChangeDatesModal(): void {
    this.showChangeDatesModal = true;
  }

  closeChangeDatesModal(): void {
    this.showChangeDatesModal = false;
  }

  // ===================================================
  // CONFIRM DATE CHANGE FROM MODAL
  // ===================================================
  confirmDateChange(): void {
    if (!this.checkIn || !this.checkOut) {
      this.searchError = 'Please select check-in and check-out dates';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.searchError = 'Check-out date must be after check-in date';
      return;
    }

    // Check if dates actually changed
    const datesChanged = this.checkIn !== this.previousCheckIn || this.checkOut !== this.previousCheckOut;
    const hasLockedRooms = this.getTotalSelectedRooms() > 0;

    // Show lock expiry info if changing dates with locked rooms
    if (datesChanged && hasLockedRooms) {
      // Calculate expiry times for all locked rooms
      const lockExpiryInfo = this.selectedLocks.map(lock => 
        `- ${lock.type_name}: ${this.getLockExpiryDisplay(lock)} remaining`
      ).join('\n');
      
      const confirmed = confirm(
        `⚠️ Changing dates will release your ${this.getTotalSelectedRooms()} locked room(s):\n\n${lockExpiryInfo}\n\nYour lock timer continues running - NO RESTART.\n\nAre you sure?`
      );
      
      if (!confirmed) {
        // Revert dates to previous values
        this.checkIn = this.previousCheckIn;
        this.checkOut = this.previousCheckOut;
        this.closeChangeDatesModal();
        return;
      }
    }

    // Close modal
    this.showChangeDatesModal = false;

    if (datesChanged && hasLockedRooms) {
      // ⚠️ User is changing dates with locked rooms
      // Release the booked rooms BUT keep the timer running (same session)
      this.releaseLocksButKeepTimer();
    } else {
      // No date change, just update the dates and reload
      this.previousCheckIn = this.checkIn;
      this.previousCheckOut = this.checkOut;
      this.loadAvailableRoomTypesWithFilters();
    }
  }

  // ===================================================
  // DETECT DATE CHANGES - Only for tracking on dates page
  // ===================================================
  onDateChange(): void {
    // Skip first render/initialization
    if (this.isInitialLoad) {
      this.isInitialLoad = false;
      return;
    }

    // Track the latest date change
    this.lastChangedDate = new Date().toISOString();
    console.log('Dates changed at:', this.lastChangedDate, 'New dates:', this.checkIn, this.checkOut);
  }

  releaseLocksButKeepTimer(): void {
    // Release locked rooms BUT keep the same session (timer keeps running)
    // Prevent race conditions
    if (this.isProcessingDateChange) return;
    this.isProcessingDateChange = true;

    this.bookingService.releaseAllLocks()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('All locks released (timer still running):', response);
          
          // Clear all local state atomically
          this.roomCart = {};
          this.selectedLocks = [];
          this.roomGuestDetails = {}; // Clear guest details
          
          // Reset search filters
          this.searchFilters = {
            room_type_id: null,
            price_per_night_min: undefined,
            price_per_night_max: undefined,
            max_adult_count: undefined,
            max_child_count: undefined,
            square_ft_min: undefined,
            square_ft_max: undefined
          };
          
          // Update previous dates
          this.previousCheckIn = this.checkIn;
          this.previousCheckOut = this.checkOut;
          
          console.log('Locks released. Session KEPT. Timer still running with dates:', this.checkIn, this.checkOut);
          
          // Load available room types with NEW dates (but SAME session/timer)
          this.loadAvailableRoomTypesWithFilters();
          
          // Release lock
          this.isProcessingDateChange = false;
        },
        error: (err) => {
          console.error('Failed to release locks:', err);
          alert('Error releasing rooms. Please try again.');
          this.isProcessingDateChange = false;
        }
      });
  }

  releaseAllLocksOnDateChange(): void {
    // Prevent race conditions - only process one date change at a time
    if (this.isProcessingDateChange) return;
    this.isProcessingDateChange = true;

    this.bookingService.releaseAllLocks()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('All locks released on date change:', response);
          
          // Clear all local state atomically
          this.roomCart = {};
          this.selectedLocks = [];
          this.roomGuestDetails = {}; // CRITICAL: Reset guest entries on new session
          
          // Reset search filters
          this.searchFilters = {
            room_type_id: null,  // Changed from type_name to room_type_id
            price_per_night_min: undefined,
            price_per_night_max: undefined,
            max_adult_count: undefined,
            max_child_count: undefined,
            square_ft_min: undefined,
            square_ft_max: undefined
          };
          
          // Update previous dates to match current dates (after release, they're now the baseline)
          this.previousCheckIn = this.checkIn;
          this.previousCheckOut = this.checkOut;
          
          // Create new booking session with updated dates
          this.createNewBookingSessionForChangedDates();
          
          console.log('Date change complete. New session created with dates:', this.checkIn, this.checkOut);
          
          // Load available room types with new dates
          this.loadAvailableRoomTypes();
          
          // Release lock
          this.isProcessingDateChange = false;
        },
        error: (err) => {
          console.error('Failed to release locks:', err);
          alert('Error releasing rooms. Please try again.');
          this.isProcessingDateChange = false;
        }
      });
  }

  private createNewBookingSessionForChangedDates(): void {
    // Store the old session ID
    this.previousSessionId = this.bookingSession?.session_id || null;
    
    console.log('Creating new booking session with dates:', this.checkIn, this.checkOut);
    console.log('Old session ID:', this.previousSessionId);
    
    // Create new booking session with new dates
    this.bookingService.createBookingSession(this.checkIn, this.checkOut)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (session) => {
          this.bookingSession = session;
          console.log('New booking session created:', session.session_id);
          
          // Update previous dates to current dates
          this.previousCheckIn = this.checkIn;
          this.previousCheckOut = this.checkOut;
          
          // Show success message to user
          this.bookingSuccess = '✅ Dates updated! Rooms released and new 15-minute timer started.';
          setTimeout(() => {
            this.bookingSuccess = '';
          }, 5000);
          
          // Load room types for new dates
          this.loadAvailableRoomTypes();
        },
        error: (err) => {
          console.error('Failed to create new booking session:', err);
          alert('Error creating booking session. Please try again.');
        }
      });
  }

  // ===================================================
  // GUEST DETAILS PER ROOM MANAGEMENT
  // ===================================================
  
  // Initialize guest details for a newly locked room
  initializeGuestDetailsForRoom(lock: RoomLock): void {
    if (!this.roomGuestDetails[lock.lock_id]) {
      this.roomGuestDetails[lock.lock_id] = {
        lockId: lock.lock_id,
        adultName: '',
        adultAge: 0,
        specialRequests: '',
        adultCount: 1,  // At least 1 adult must stay
        childCount: 0   // Can be 0
      };
    }
  }
  
  // Get guest details for specific room
  getGuestDetailsForRoom(lockId: number): RoomGuestDetails | undefined {
    return this.roomGuestDetails[lockId];
  }
  
  // Update guest details for specific room
  updateGuestDetails(lockId: number, details: Partial<RoomGuestDetails>): void {
    if (this.roomGuestDetails[lockId]) {
      this.roomGuestDetails[lockId] = {
        ...this.roomGuestDetails[lockId],
        ...details
      };
      // Validate guest counts after update
      this.validateAndCorrectGuestCounts(lockId);
    }
  }

  // Apply user's own details to a room (name and age from DOB)
  applyUserDetailsToRoom(lockId: number): void {
    // Can only use user details if DOB exists
    if (!this.userDetails.hasDob || !this.userDetails.name || !this.userDetails.age) {
      alert('❌ User details incomplete. DOB is required to use your profile details.');
      return;
    }

    // Remove from previous room if it was used elsewhere
    if (this.userDetails.usedInRoom !== null && this.userDetails.usedInRoom !== lockId) {
      const previousRoom = this.roomGuestDetails[this.userDetails.usedInRoom];
      if (previousRoom) {
        previousRoom.adultName = '';
        previousRoom.adultAge = 0;
      }
    }

    // Apply user details to this room
    this.updateGuestDetails(lockId, {
      adultName: this.userDetails.name,
      adultAge: this.userDetails.age
    });

    // Mark this room as using user details
    this.userDetails.usedInRoom = lockId;
    
    // Trigger change detection to update completion counter
    this.cdr.markForCheck();
    
    console.log(`✅ User details applied to room ${lockId}: ${this.userDetails.name}, Age ${this.userDetails.age}`);
    console.log(`📊 Rooms completed: ${this.getCompletedRoomsCount()} / ${this.selectedLocks.length}`);
  }

  // Clear user details from a room
  clearUserDetailsFromRoom(lockId: number): void {
    if (this.userDetails.usedInRoom === lockId) {
      this.updateGuestDetails(lockId, {
        adultName: '',
        adultAge: 0
      });
      this.userDetails.usedInRoom = null;
      
      // Trigger change detection to update completion counter
      this.cdr.markForCheck();
      
      console.log(`✅ User details cleared from room ${lockId}`);
      console.log(`📊 Rooms completed: ${this.getCompletedRoomsCount()} / ${this.selectedLocks.length}`);
    }
  }

  // Check if a room is using user details
  isRoomUsingUserDetails(lockId: number): boolean {
    return this.userDetails.usedInRoom === lockId;
  }

  // Validate and correct guest counts against room capacity
  validateAndCorrectGuestCounts(lockId: number): void {
    const roomDetails = this.roomGuestDetails[lockId];
    if (!roomDetails) return;

    // Find the corresponding lock to get room capacity
    const lock = this.selectedLocks.find(l => l.lock_id === lockId);
    if (!lock || !lock.max_adult_count || !lock.max_child_count) return;

    const maxAdults = lock.max_adult_count;
    const maxChildren = lock.max_child_count;

    // If adults exceed capacity, auto-correct and warn
    if (roomDetails.adultCount > maxAdults) {
      console.warn(
        `⚠️  Warning: Room ${lock.type_name} only has capacity for ${maxAdults} adults. ` +
        `You entered ${roomDetails.adultCount}. Limiting to ${maxAdults}.`
      );
      roomDetails.adultCount = maxAdults;
      this.showCapacityWarning(lock.type_name, 'adults', roomDetails.adultCount, maxAdults);
    }

    // If children exceed capacity, auto-correct and warn
    if (roomDetails.childCount > maxChildren) {
      console.warn(
        `⚠️  Warning: Room ${lock.type_name} only has capacity for ${maxChildren} children. ` +
        `You entered ${roomDetails.childCount}. Limiting to ${maxChildren}.`
      );
      roomDetails.childCount = maxChildren;
      this.showCapacityWarning(lock.type_name, 'children', roomDetails.childCount, maxChildren);
    }

    // Ensure at least 1 adult stays
    if (roomDetails.adultCount < 1) {
      roomDetails.adultCount = 1;
    }

    // Ensure children count doesn't go negative
    if (roomDetails.childCount < 0) {
      roomDetails.childCount = 0;
    }

    this.cdr.markForCheck();
  }

  // Show capacity warning alert
  private showCapacityWarning(roomType: string, guestType: 'adults' | 'children', correctedCount: number, maxCapacity: number): void {
    const message = `⚠️  Room Capacity Alert:\n\n${roomType} can only accommodate ${maxCapacity} ${guestType}.\n` +
      `Your entry has been auto-corrected to ${correctedCount} ${guestType}.\n\n` +
      `At payment, only ${correctedCount} ${guestType} will be allowed to check in.`;
    alert(message);
  }

  // Get room capacity details
  getRoomCapacity(lockId: number): { maxAdults: number; maxChildren: number } | null {
    const lock = this.selectedLocks.find(l => l.lock_id === lockId);
    if (lock && lock.max_adult_count && lock.max_child_count) {
      return {
        maxAdults: lock.max_adult_count,
        maxChildren: lock.max_child_count
      };
    }
    return null;
  }
  
  // Check if all guest details are filled
  areAllGuestDetailsFilled(): boolean {
    // Check if all required fields are filled: name, age (>=18), and at least 1 adult
    return this.selectedLocks.every(lock => {
      const details = this.roomGuestDetails[lock.lock_id];
      return details && 
             details.adultName.trim() !== '' && 
             details.adultAge >= 18 &&  // MUST be at least 18
             details.adultCount >= 1;
    });
  }

  // Count how many rooms have complete guest details
  getCompletedRoomsCount(): number {
    return this.selectedLocks.filter(lock => {
      const details = this.roomGuestDetails[lock.lock_id];
      return details && 
             details.adultName.trim() !== '' && 
             details.adultAge >= 18 &&  // MUST be at least 18
             details.adultCount >= 1;
    }).length;
  }
  
  // Get all guest details for submission
  getAllGuestDetails(): { [key: number]: RoomGuestDetails } {
    return this.roomGuestDetails;
  }

  // ===================================================
  // LOCK EXPIRY TIME CALCULATION
  // ===================================================
  
  /**
   * Calculate remaining seconds until a specific lock expires
   * Returns the number of seconds remaining
   */
  getLockRemainingSeconds(lock: RoomLock): number {
    if (!lock.expires_at) {
      return 0;
    }
    
    const expiryTime = new Date(lock.expires_at).getTime();
    const nowTime = Date.now();
    const remainingMs = expiryTime - nowTime;
    const remainingSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
    
    return remainingSeconds;
  }

  /**
   * Get formatted string of remaining time for a lock
   * Format: "MM:SS remaining"
   */
  getLockExpiryDisplay(lock: RoomLock): string {
    const seconds = this.getLockRemainingSeconds(lock);
    
    if (seconds <= 0) {
      return 'Expired';
    }
    
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Get color class for lock expiry based on remaining time
   */
  getLockExpiryColor(lock: RoomLock): string {
    const seconds = this.getLockRemainingSeconds(lock);
    
    if (seconds <= 0) {
      return 'text-red-600 font-bold';
    } else if (seconds <= 60) { // <= 1 minute
      return 'text-red-500 font-bold';
    } else if (seconds <= 300) { // <= 5 minutes
      return 'text-orange-500 font-semibold';
    } else {
      return 'text-green-600 font-semibold';
    }
  }

  // ===================================================
  // LOCK EXPIRY TIME CALCULATION (REMOVED)
  // Now using server session expiry via bookingService
  // ===================================================

  // ===================================================
  // CART OPERATIONS - Update to initialize guest details
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
          this.initializeGuestDetailsForRoom(lock);  // Initialize guest details for new room
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
            
            // Remove guest details for this room
            delete this.roomGuestDetails[lastLock.lock_id];
            
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
  
  // ===================================================
  // ROOM CARD EVENT HANDLERS
  // ===================================================
  
  /**
   * Handle when a room is successfully locked from room card
   */
  onRoomLocked(lock: RoomLock, roomType: any): void {
    const typeKey = `room_${roomType.room_type_id}`;
    
    // Initialize cart item if not exists
    if (!this.roomCart[typeKey]) {
      this.roomCart[typeKey] = {
        count: 0,
        roomType: roomType,
        locks: []
      };
    }
    
    // Increment count and add lock
    this.roomCart[typeKey].count++;
    this.roomCart[typeKey].locks.push(lock);
    
    // Initialize guest details for this room
    this.initializeGuestDetailsForRoom(lock);
    
    // Update selected locks
    this.updateSelectedLocks();
    
    console.log(`✅ Room locked successfully: ${roomType.type_name}`);
    this.cdr.markForCheck();
  }

  /**
   * Handle room lock error from room card
   */
  onRoomLockError(errorMsg: string, roomType: any): void {
    console.error(`❌ Failed to lock room: ${roomType.type_name}`, errorMsg);
    this.cdr.markForCheck();
  }

  /**
   * Handle room lock success notification from room card
   */
  onRoomLockSuccess(roomType: any): void {
    console.log(`🎉 Room booking initialized for: ${roomType.type_name}`);
    this.cdr.markForCheck();
  }
  
  // ===================================================
  // BOOK ROOM - With backend availability check
  // ===================================================
  bookRoom(roomType: any): void {
    if (this.isBookingRoom) return; // Prevent double-click
    
    this.isBookingRoom = true;
    this.bookingRoomType = roomType.type_name;
    this.bookingError = '';
    this.bookingSuccess = '';

    // Lock room (this checks availability on backend)
    this.lockRoomOfType(roomType)
      .then((lock) => {
        if (lock) {
          // Room was successfully booked
          const typeKey = roomType.type_name;
          
          // Initialize cart item if not exists
          if (!this.roomCart[typeKey]) {
            this.roomCart[typeKey] = {
              count: 0,
              roomType: roomType,
              locks: []
            };
          }
          
          // Increment count and add lock
          this.roomCart[typeKey].count++;
          this.roomCart[typeKey].locks.push(lock);
          this.initializeGuestDetailsForRoom(lock);
          this.updateSelectedLocks();
          
          // Show success message
          this.bookingSuccess = `✅ ${roomType.type_name} room booked successfully!`;
          
          // Clear success message after 5 seconds
          setTimeout(() => {
            if (this.bookingRoomType === roomType.type_name) {
              this.bookingSuccess = '';
            }
          }, 5000);
        } else {
          // Room not available - lock failed
          this.bookingError = `❌ No ${roomType.type_name} rooms available for your selected dates. This room type is fully booked.`;
        }
        
        this.isBookingRoom = false;
        this.bookingRoomType = null;
      })
      .catch((error) => {
        console.error('Failed to book room:', error);
        // Extract meaningful error message from backend
        let errorMsg = 'Failed to book room. Please try again.';
        
        // Check for specific HTTP status codes
        if (error?.status === 404) {
          errorMsg = `❌ No ${this.bookingRoomType} rooms available for your selected dates. This room type is fully booked or unavailable.`;
        } else if (error?.error?.detail) {
          errorMsg = error.error.detail;
        } else if (error?.message) {
          errorMsg = error.message;
        } else if (typeof error === 'string') {
          errorMsg = error;
        }
        
        this.bookingError = `${errorMsg}`;
        this.isBookingRoom = false;
        this.bookingRoomType = null;
        this.cdr.markForCheck();
      });
  }
  
  // Lock a specific room of given type
  private lockRoomOfType(roomType: any): Promise<RoomLock | null> {
    return new Promise((resolve, reject) => {
      if (!this.bookingSession) {
        reject('Booking session not initialized');
        return;
      }
      
      // Use booking session's expiry time from server (more accurate)
      const expiresAt = this.bookingSession.expiry_time || 
                       new Date(Date.now() + 15 * 60 * 1000).toISOString();
      
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
    // Use 'free_rooms' from API response (real count) or 'availability_count' if available
    const availableRooms = roomType.free_rooms || roomType.availability_count || 0;
    return availableRooms - currentCount;
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
            this.roomGuestDetails = {};
          },
          error: (err) => {
            console.error('Failed to clear selections:', err)
            // Fallback: clear locally anyway
            this.roomCart = {};
            this.selectedLocks = [];
            this.roomGuestDetails = {};
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
  // BOOKING COMPLETION - Move to Payment
  // ===================================================
  
  completeRoomSelection(): void {
    console.log('🔴 completeRoomSelection called');
    console.log('Total selected rooms:', this.getTotalSelectedRooms());
    console.log('Guest details filled:', this.areAllGuestDetailsFilled());
    
    if (this.getTotalSelectedRooms() === 0) {
      alert('Please select at least one room');
      return;
    }
    
    // Check if all guest details are filled
    if (!this.areAllGuestDetailsFilled()) {
      alert('Please fill in guest details for all selected rooms');
      return;
    }
    
    console.log('🟡 About to switch phase');
    console.log('Current phase before:', this.currentPhase, 'PHASES.PAYMENT value:', PHASES.PAYMENT);
    
    // Move to payment phase - let RX streams continue naturally
    // Change detection will pick up the phase change automatically
    this.currentPhase = PHASES.PAYMENT;
    
    console.log('🟢 Phase switched to:', this.currentPhase);
    console.log('isPaymentPhase getter returns:', this.isPaymentPhase);
    
    // Scroll to top so user sees payment phase
    setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 100);
    
    this.cdr.markForCheck();
    this.cdr.detectChanges();
    
    console.log('✅ Change detection triggered');
  }

  startNewBooking(): void {
    // Reset all data
    this.currentPhase = PHASES.DATES;
    this.showSummary = false;
    this.checkIn = '';
    this.checkOut = '';
    this.previousCheckIn = '';
    this.previousCheckOut = '';
    this.lastChangedDate = '';
    this.datesSelected = false;
    this.roomCart = {};
    this.selectedLocks = [];
    this.roomGuestDetails = {};
    this.bookingSession = null;
    this.previousSessionId = null;
    this.bookingStartTime = null;
    this.isInitialLoad = true; // Reset flag for next booking
    this.isProcessingDateChange = false;
    this.confirmationData = null; // Clear confirmation data
    this.bookingId = null; // Clear booking ID
    this.cdr.markForCheck();
    this.cdr.detectChanges();
  }

  goToDashboard(): void {
    // Reset booking state and navigate to dashboard
    this.selectedPaymentMethod = null;
    this.upiId = '';
    this.roomGuestDetails = {};
    this.selectedLocks = [];
    this.bookingSummary = null;
    this.confirmationData = null;
    this.bookingId = null;
    this.currentPhase = PHASES.DATES;
    this.router.navigate(['/dashboard/bookings']);
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
  // PHASE: SEARCH - WITH FILTERS CONNECTED TO BACKEND
  // ===================================================
  loadAvailableRoomTypesWithFilters(): void {
    // Load room types with filters applied
    this.isLoadingRoomTypes = true;
    
    // Build filter object - only include defined values
    const filters: any = {};
    
    // INCLUDE room_type_id if selected (user chose a specific room type)
    if (this.searchFilters.room_type_id && this.searchFilters.room_type_id > 0) 
      filters.room_type_id = this.searchFilters.room_type_id;
    
    // Apply other filters: price, capacity, and size
    if (this.searchFilters.price_per_night_min !== undefined && this.searchFilters.price_per_night_min > 0) 
      filters.price_per_night_min = this.searchFilters.price_per_night_min;
    if (this.searchFilters.price_per_night_max !== undefined && this.searchFilters.price_per_night_max > 0) 
      filters.price_per_night_max = this.searchFilters.price_per_night_max;
    if (this.searchFilters.max_adult_count !== undefined && this.searchFilters.max_adult_count > 0) 
      filters.max_adult_count = this.searchFilters.max_adult_count;
    if (this.searchFilters.max_child_count !== undefined && this.searchFilters.max_child_count > 0) 
      filters.max_child_count = this.searchFilters.max_child_count;
    if (this.searchFilters.square_ft_min !== undefined && this.searchFilters.square_ft_min > 0) 
      filters.square_ft_min = this.searchFilters.square_ft_min;
    if (this.searchFilters.square_ft_max !== undefined && this.searchFilters.square_ft_max > 0) 
      filters.square_ft_max = this.searchFilters.square_ft_max;
    
    console.log('🔍 Searching with filters:', filters);
    
    this.bookingService.searchRooms(this.checkIn, this.checkOut, filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (rooms) => {
          console.log('✅ Rooms found with filters:', rooms);
          this.availableRoomTypes = rooms;
          this.isLoadingRoomTypes = false;
          
          // After rooms are loaded, attempt to auto-lock if room_type_id was provided
          if (this.selectedRoomTypeIdFromQuery) {
            this.attemptAutoLockRoomType();
          }
        },
        error: (err) => {
          console.error('❌ Failed to load filtered room types:', err);
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

    // Use booking session's expiry time from server (more accurate)
    const expiresAt = this.bookingSession.expiry_time || 
                     new Date(Date.now() + 15 * 60 * 1000).toISOString();

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
          // Remove from local selectedLocks array
          this.selectedLocks = this.selectedLocks.filter(lock => lock.lock_id !== lockId);
          
          // Remove from local roomCart
          Object.keys(this.roomCart).forEach(typeKey => {
            this.roomCart[typeKey].locks = this.roomCart[typeKey].locks.filter(lock => lock.lock_id !== lockId);
            this.roomCart[typeKey].count = this.roomCart[typeKey].locks.length;
            
            // Remove the type key if no locks remain
            if (this.roomCart[typeKey].count === 0) {
              delete this.roomCart[typeKey];
            }
          });
          
          // Remove guest details for this room
          delete this.roomGuestDetails[lockId];
          
          // Update UI
          this.updateSummary();
          this.cdr.markForCheck();
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
  // PAYMENT PHASE - Finalize booking
  // ===================================================
  
  proceedToPayment(): void {
    if (!this.areAllGuestDetailsFilled()) {
      alert('Please fill in guest details for all selected rooms');
      return;
    }
    console.log('Proceeding to payment with guest details:', this.roomGuestDetails);
    // Payment logic will be implemented here
    // For now, we're just storing guest details locally
  }
  
  // ===================================================
  // PAYMENT HANDLING
  // ===================================================

  // Validate UPI ID format (example@bankname)
  isValidUPI(upi: string): boolean {
    const upiRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$/;
    return upiRegex.test(upi);
  }

  // Check if payment can be processed (all conditions met)
  canProcessPayment(): boolean {
    // Must have selected a payment method
    if (!this.selectedPaymentMethod) return false;

    // Must have all guest details filled with age >= 18
    if (!this.areAllGuestDetailsFilled()) return false;

    // If UPI selected, UPI ID must be valid
    if (this.selectedPaymentMethod === 'upi') {
      return this.upiId.trim() !== '' && this.isValidUPI(this.upiId);
    }

    // For card and netbanking, just need payment method selected
    return true;
  }

  // Get disabled reason for tooltip
  getPaymentButtonDisabledReason(): string {
    if (!this.areAllGuestDetailsFilled()) {
      return 'Please fill all guest details with valid age (18+)';
    }
    if (!this.selectedPaymentMethod) {
      return 'Please select a payment method';
    }
    if (this.selectedPaymentMethod === 'upi' && (!this.upiId || !this.isValidUPI(this.upiId))) {
      return 'Please enter a valid UPI ID (e.g., user@okhdfcbank)';
    }
    return '';
  }

  // Select payment method
  selectPaymentMethod(method: 'card' | 'upi' | 'netbanking'): void {
    this.selectedPaymentMethod = method;
    // Clear UPI ID if switching away from UPI
    if (method !== 'upi') {
      this.upiId = '';
    }
    console.log(`💳 Payment method selected: ${method.toUpperCase()}`);
  }

  // Clear booking error message
  clearBookingError(): void {
    this.bookingError = '';
    this.cdr.markForCheck();
  }

  // Process payment based on selected method
  completePayment(): void {
    if (!this.canProcessPayment()) {
      alert('❌ ' + this.getPaymentButtonDisabledReason());
      return;
    }

    this.isProcessingPayment = true;
    this.bookingError = '';

    // Map payment method to backend ID
    const paymentMethodMap: { [key: string]: number } = {
      card: 1,
      upi: 2,
      netbanking: 3
    };

    const paymentMethodId = paymentMethodMap[this.selectedPaymentMethod!];

    // Build guest details array from roomGuestDetails
    const roomsGuestDetails = this.selectedLocks.map(lock => ({
      lock_id: lock.lock_id,
      guest_name: this.roomGuestDetails[lock.lock_id]?.adultName || '',
      guest_age: this.roomGuestDetails[lock.lock_id]?.adultAge || 0,
      adult_count: this.roomGuestDetails[lock.lock_id]?.adultCount || 1,
      child_count: this.roomGuestDetails[lock.lock_id]?.childCount || 0,
      special_requests: this.roomGuestDetails[lock.lock_id]?.specialRequests || ''
    }));

    console.log('💰 Sending booking confirmation:', {
      paymentMethodId,
      roomsGuestDetails
    });

    // Call backend API to confirm booking and process payment
    this.bookingService.confirmBooking(
      paymentMethodId,
      roomsGuestDetails,
      this.selectedPaymentMethod === 'upi' ? this.upiId : undefined
    )
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('✅ Booking confirmed successfully:', response);
          this.isProcessingPayment = false;

          // Store confirmation data
          this.confirmationData = response;
          this.bookingId = response.booking_id;

          // Move to confirmation phase
          this.currentPhase = PHASES.CONFIRMATION;
        },
        error: (err) => {
          this.isProcessingPayment = false;
          const errorMessage = err.error?.detail || 'Payment processing failed. Please try again.';
          this.bookingError = '❌ ' + errorMessage;
          console.error('Payment failed:', err);
          alert('❌ ' + errorMessage);
        }
      });
  }

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
    this.currentPhase = PHASES.SEARCH_AND_DETAILS;
    this.bookingSession = null;
    this.previousSessionId = null;
    this.selectedLocks = [];
    this.bookingSummary = null;
    this.roomGuestDetails = {};
  }

  // Stop booking and go back to previous page
  stopBooking(): void {
    // If no rooms selected, just navigate back
    if (this.getTotalSelectedRooms() === 0) {
      this.router.navigate([this.previousPage]);
      return;
    }

    // If rooms are selected, confirm with alert
    const confirmStop = confirm('⚠️ You have ' + this.getTotalSelectedRooms() + ' room(s) locked. Are you sure you want to stop booking?');
    
    if (confirmStop) {
      // Release all locks before leaving
      this.bookingService.releaseAllLocks().subscribe({
        next: () => {
          console.log('✅ All locks released');
          this.resetBooking();
          this.router.navigate([this.previousPage]);
        },
        error: (err) => {
          console.error('Error releasing locks:', err);
          // Still navigate even if lock release fails
          this.resetBooking();
          this.router.navigate([this.previousPage]);
        }
      });
    }
  }

  goBack(): void {
    if (this.currentPhase === PHASES.DATES) {
      this.router.navigate(['/']);
    } else if (this.currentPhase === PHASES.SEARCH_AND_DETAILS) {
      // Go back to date picker modal
      this.showDatePickerModal = true;
      this.showSummary = false;
    } else if (this.currentPhase === PHASES.PAYMENT) {
      // Go back to search-and-details from payment
      this.currentPhase = PHASES.SEARCH_AND_DETAILS;
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
    // remainingSeconds already contains total seconds
    const totalSeconds = Math.max(0, this.remainingSeconds); // Ensure no negative values
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

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
}
