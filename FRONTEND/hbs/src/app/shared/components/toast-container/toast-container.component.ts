import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService,Toast } from '../../services/toast.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="fixed top-6 right-6 z-50 space-y-3 pointer-events-none">
      <div 
        *ngFor="let toast of toasts"
        [ngClass]="{
          'bg-green-50 border-l-4 border-green-500 text-green-700': toast.type === 'success',
          'bg-red-50 border-l-4 border-red-500 text-red-700': toast.type === 'error',
          'bg-yellow-50 border-l-4 border-yellow-500 text-yellow-700': toast.type === 'warning',
          'bg-blue-50 border-l-4 border-blue-500 text-blue-700': toast.type === 'info'
        }"
        class="pointer-events-auto shadow-lg rounded-lg p-4 max-w-sm animate-slideIn">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-start gap-3">
            <span [ngSwitch]="toast.type" class="text-xl mt-0.5">
              <span *ngSwitchCase="'success'">✅</span>
              <span *ngSwitchCase="'error'">❌</span>
              <span *ngSwitchCase="'warning'">⚠️</span>
              <span *ngSwitchCase="'info'">ℹ️</span>
            </span>
            <p class="font-medium">{{ toast.message }}</p>
          </div>
          <button
            (click)="dismiss(toast.id)"
            class="text-xl font-bold opacity-50 hover:opacity-100 transition"
            title="Dismiss">
            ✕
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    @keyframes slideIn {
      from {
        transform: translateX(400px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    
    .animate-slideIn {
      animation: slideIn 0.3s ease-out;
    }
  `]
})
export class ToastContainerComponent implements OnInit, OnDestroy {
  toasts: Toast[] = [];
  private destroy$ = new Subject<void>();

  constructor(private toastService: ToastService) {}

  ngOnInit(): void {
    this.toastService.getToasts()
      .pipe(takeUntil(this.destroy$))
      .subscribe(toasts => {
        this.toasts = toasts;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  dismiss(id: string): void {
    this.toastService.dismiss(id);
  }
}
