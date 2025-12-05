import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number; // milliseconds, 0 = permanent
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toasts$ = new BehaviorSubject<Toast[]>([]);
  private toastId = 0;

  getToasts(): Observable<Toast[]> {
    return this.toasts$.asObservable();
  }

  show(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info', duration = 4000): string {
    const id = `toast-${++this.toastId}`;
    const toast: Toast = { id, message, type, duration };
    
    const currentToasts = this.toasts$.value;
    this.toasts$.next([...currentToasts, toast]);

    if (duration > 0) {
      setTimeout(() => this.dismiss(id), duration);
    }

    return id;
  }

  success(message: string, duration = 4000): string {
    return this.show(message, 'success', duration);
  }

  error(message: string, duration = 5000): string {
    return this.show(message, 'error', duration);
  }

  warning(message: string, duration = 4000): string {
    return this.show(message, 'warning', duration);
  }

  info(message: string, duration = 4000): string {
    return this.show(message, 'info', duration);
  }

  dismiss(id: string): void {
    const toasts = this.toasts$.value.filter(t => t.id !== id);
    this.toasts$.next(toasts);
  }

  dismissAll(): void {
    this.toasts$.next([]);
  }
}
