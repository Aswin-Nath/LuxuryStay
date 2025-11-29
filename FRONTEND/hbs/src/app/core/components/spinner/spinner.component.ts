import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-spinner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="isLoading" class="spinner-overlay">
      <div class="spinner-container">
        <div class="spinner">
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
        </div>
        <p *ngIf="message" class="spinner-message">{{ message }}</p>
      </div>
    </div>
  `,
  styles: [`
    .spinner-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 9999;
    }

    .spinner-container {
      text-align: center;
      background: white;
      padding: 40px;
      border-radius: 10px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .spinner {
      position: relative;
      width: 80px;
      height: 80px;
      margin: 0 auto 20px;
    }

    .spinner-ring {
      position: absolute;
      width: 100%;
      height: 100%;
      border: 4px solid transparent;
      border-radius: 50%;
      animation: spin 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
    }

    .spinner-ring:nth-child(1) {
      border-top-color: #f97316;
      border-right-color: #f97316;
      animation-delay: -0.45s;
    }

    .spinner-ring:nth-child(2) {
      border-top-color: #fb923c;
      border-right-color: #fb923c;
      animation-delay: -0.3s;
    }

    .spinner-ring:nth-child(3) {
      border-top-color: #fdba74;
      border-right-color: #fdba74;
      animation-delay: -0.15s;
    }

    .spinner-ring:nth-child(4) {
      border-top-color: #fed7aa;
      border-right-color: #fed7aa;
    }

    @keyframes spin {
      0% {
        transform: rotate(0deg);
      }
      100% {
        transform: rotate(360deg);
      }
    }

    .spinner-message {
      color: #333;
      font-size: 14px;
      margin: 0;
      font-weight: 500;
    }
  `]
})
export class SpinnerComponent {
  @Input() isLoading: boolean = false;
  @Input() message: string = 'Loading...';
}
