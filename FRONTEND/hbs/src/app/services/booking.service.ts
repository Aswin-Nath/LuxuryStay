import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, interval, of } from 'rxjs';
import { map, switchMap, takeUntil } from 'rxjs/operators';

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
  private apiUrl = 'http://localhost:8000/api/v2/rooms';
  
  // State management
  private bookingSession = new BehaviorSubject<BookingSession | null>(null);
  public bookingSession$ = this.bookingSession.asObservable();

  private selectedLocks = new BehaviorSubject<RoomLock[]>([]);
  public selectedLocks$ = this.selectedLocks.asObservable();

  private remainingTime = new BehaviorSubject<number>(900); // 15 minutes in seconds
  public remainingTime$ = this.remainingTime.asObservable();

  private isSessionExpired = new BehaviorSubject<boolean>(false);
  public isSessionExpired$ = this.isSessionExpired.asObservable();

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
      if (filters.room_type_id) params = params.set('room_type_id', filters.room_type_id.toString());
      if (filters.type_name) params = params.set('type_name', filters.type_name);
      if (filters.price_per_night_min) params = params.set('price_per_night_min', filters.price_per_night_min.toString());
      if (filters.price_per_night_max) params = params.set('price_per_night_max', filters.price_per_night_max.toString());
      if (filters.max_adult_count) params = params.set('max_adult_count', filters.max_adult_count.toString());
      if (filters.max_child_count) params = params.set('max_child_count', filters.max_child_count.toString());
      if (filters.square_ft_min) params = params.set('square_ft_min', filters.square_ft_min.toString());
      if (filters.square_ft_max) params = params.set('square_ft_max', filters.square_ft_max.toString());
    }

    return this.http.get<any>(`${this.apiUrl}/search`, { params }).pipe(
      map(response => response.results || [])
    );
  }

  // ===================================================
  // BOOKING SESSION
  // ===================================================
  createBookingSession(checkIn: string, checkOut: string): Observable<BookingSession> {
    return this.http.post<BookingSession>(
      `${this.apiUrl}/booking/session`,
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
      `${this.apiUrl}/booking/session/${sessionId}`
    );
  }

  private startSessionTimer(session: BookingSession): void {
    const expiryTime = new Date(session.expiry_time).getTime();
    
    // Set initial remaining time immediately
    const now = new Date().getTime();
    const initialRemaining = Math.max(0, Math.floor((expiryTime - now) / 1000));
    this.remainingTime.next(initialRemaining);
    
    interval(1000)
      .pipe(
        switchMap(() => {
          const now = new Date().getTime();
          const remaining = Math.max(0, Math.floor((expiryTime - now) / 1000));
          
          this.remainingTime.next(remaining);
          
          if (remaining <= 0) {
            this.isSessionExpired.next(true);
          }
          
          return of(remaining);
        }),
        takeUntil(this.isSessionExpired$.pipe(
          switchMap(expired => expired ? of(true) : of(false))
        ))
      )
      .subscribe();
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
      `${this.apiUrl}/lock`,
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
      `${this.apiUrl}/unlock/${lockId}`,
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
    return this.http.post(`${this.apiUrl}/release-all-locks`, {}).pipe(
      map((response) => {
        // Clear all local locks
        this.selectedLocks.next([]);
        return response;
      })
    );
  }

  getMyLocks(): Observable<RoomLock[]> {
    return this.http.get<RoomLock[]>(`${this.apiUrl}/my-locks`).pipe(
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
      `${this.apiUrl}/booking/summary`,
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
