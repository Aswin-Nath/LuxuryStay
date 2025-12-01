import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, interval, of, Subject } from 'rxjs';
import { map, switchMap, takeUntil } from 'rxjs/operators';
import { environment } from '../../environments/environment';

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

// Payment interfaces removed - keeping only room selection functionality

@Injectable({
  providedIn: 'root'
})
export class BookingService {
  private bookingApiUrl = `${environment.apiUrl}/v2/rooms`;
  private imageApiUrl = `${environment.apiUrl}/room-management`;
  
  // Expose booking API URL for room booking operations
  getBookingApiUrl(): string {
    return this.bookingApiUrl;
  }
  
  // Expose image API URL for room images
  getImageApiUrl(): string {
    return this.imageApiUrl;
  }
  
  // State management
  private bookingSession = new BehaviorSubject<BookingSession | null>(null);
  public bookingSession$ = this.bookingSession.asObservable();

  private selectedLocks = new BehaviorSubject<RoomLock[]>([]);
  public selectedLocks$ = this.selectedLocks.asObservable();

  private remainingTime = new BehaviorSubject<number>(900); // 15 minutes in seconds
  public remainingTime$ = this.remainingTime.asObservable();

  private isSessionExpired = new BehaviorSubject<boolean>(false);
  public isSessionExpired$ = this.isSessionExpired.asObservable();

  // Timer cleanup subject - allows us to stop previous timers
  private timerCleanup = new Subject<void>();

  constructor(private http: HttpClient) {}

  // ===================================================
  // ROOM SEARCH
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
    const expiryTime = new Date(session.expiry_time).getTime();
    
    // Get the current remaining time (from old session if exists)
    const currentRemaining = this.remainingTime.getValue();
    
    // If there's already a running timer, just update the expiry time and let it continue
    // This preserves the countdown instead of resetting to 15 minutes
    // Otherwise, calculate the initial remaining time from the session expiry
    let initialRemaining = currentRemaining;
    if (initialRemaining <= 0 || initialRemaining > 900) {
      // Only reset if no timer is running or timer is invalid
      const now = new Date().getTime();
      initialRemaining = Math.max(0, Math.floor((expiryTime - now) / 1000));
    }
    
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

  // Booking confirmation removed - keeping only room selection functionality

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
}
