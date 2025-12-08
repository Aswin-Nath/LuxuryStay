import { Component, ElementRef, ViewChild, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthenticationService } from '../../../../../shared/services/authentication.service';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [FormsModule, CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './forgot-password-form.html',
  styleUrls: ['./forgot-password-form.css']
})
export class ForgotPassword implements OnDestroy {

  @ViewChild('toast') toast!: ElementRef<HTMLDivElement>;
  @ViewChild('otpInput') otpInput!: ElementRef<HTMLInputElement>;

  email = '';
  otp = '';
  newPassword = '';
  showOtpFields = false;

  emailError = '';
  otpError = '';
  passwordError = '';
  formError = '';

  loadingSend = false;
  loadingReset = false;

  resendCooldownSeconds = 0;
  private resendTimerId: number | null = null;

  private passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {}

  validateEmail() {
    if (!this.email.trim()) {
      this.emailError = 'Email is required.';
      return false;
    }
    this.emailError = '';
    return true;
  }

  private startResendCooldown(seconds: number) {
    if (this.resendTimerId) clearInterval(this.resendTimerId);

    this.resendCooldownSeconds = seconds;

    this.resendTimerId = window.setInterval(() => {
      this.resendCooldownSeconds -= 1;

      if (this.resendCooldownSeconds <= 0) {
        clearInterval(this.resendTimerId!);
        this.resendCooldownSeconds = 0;
      }
    }, 1000);
  }

  ngOnDestroy() {
    if (this.resendTimerId) clearInterval(this.resendTimerId);
  }

  onEmailInput() {
    this.emailError = '';
    this.formError = '';
  }

  onOtpInput() {
    this.otpError = '';
    this.formError = '';
  }

  onNewPasswordInput() {
    this.passwordError = '';
    this.formError = '';
  }

  sendResetLink() {
    if (!this.validateEmail()) return;

    if (this.resendCooldownSeconds > 0) {
      this.formError = `Please wait ${this.resendCooldownSeconds}s before requesting again.`;
      return;
    }

    this.loadingSend = true;
    this.otp = '';
    this.otpError = '';
    this.formError = '';

    this.authService.requestOtp(this.email, 'PASSWORD_RESET').subscribe({
      next: (res) => {
        this.loadingSend = false;
        this.showOtpFields = true;

        if (res?.otp) this.otp = String(res.otp);

        this.showToast(res?.message ?? 'OTP sent', 'success');
        this.startResendCooldown(20);

        setTimeout(() => this.otpInput?.nativeElement?.focus(), 80);
      },
      error: (err: HttpErrorResponse) => {
        this.loadingSend = false;
        this.handleHttpError(err, 'send');
      }
    });
  }

  verifyOtpAndReset() {
    if (!this.otp.trim()) {
      this.otpError = 'OTP is required.';
      return;
    }

    if (!/^[0-9]{4,8}$/.test(this.otp.trim())) {
      this.otpError = 'OTP must be 4–8 digits.';
      return;
    }

    if (!this.newPassword.trim()) {
      this.passwordError = 'New password is required.';
      return;
    }

    if (!this.passwordRegex.test(this.newPassword)) {
      this.passwordError = 'Password must contain uppercase, lowercase, digit & special character.';
      return;
    }

    this.loadingReset = true;

    this.authService.verifyOtp(
      this.email,
      this.otp,
      'PASSWORD_RESET',
      this.newPassword
    ).subscribe({
      next: () => {
        this.showToast('Password reset successful', 'success');

        // Fade-out
        setTimeout(() => document.body.classList.add('fade-page'), 300);

        // navigate after fade
        setTimeout(() => this.router.navigate(['/login']), 900);
      },
      error: (err: HttpErrorResponse) => {
        this.loadingReset = false;
        this.handleHttpError(err, 'verify');
      }
    });
  }

  private handleHttpError(err: HttpErrorResponse, stage: 'send' | 'verify') {
    this.emailError = '';
    this.otpError = '';
    this.passwordError = '';

    const detail = err?.error?.detail;
    const detailMsg = typeof detail === 'object' && detail?.error ? detail.error : detail;

    let msg = detailMsg ?? err.error?.message ?? err.message;

    if (err.status === 404) {
      if (stage === 'send') {
        this.emailError = msg;
      }
      this.formError = msg;
      return;
    }

    if (err.status === 429) {
      const m = err.error?.message ?? 'Too many requests. Please try again later.';
      this.formError = m;
      return;
    }

    if (err.status === 400) {
      const m = msg.toLowerCase();

      if (m.includes('otp')) {
        this.otpError = 'Invalid or expired OTP.';
        return;
      }

      if (m.includes('password')) {
        this.passwordError = msg;
        return;
      }
    }

    this.formError = msg;
  }

  private showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
    const toast = this.toast.nativeElement;

    const msgEl = toast.querySelector('#toastMessage') as HTMLElement;
    const iconEl = toast.querySelector('#toastIcon') as HTMLElement;

    msgEl.textContent = message;

    let bg = type === 'success'
      ? 'bg-green-600'
      : type === 'error'
      ? 'bg-red-600'
      : 'bg-blue-600';

    iconEl.textContent =
      type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info';

    toast.className = `toast show fixed top-6 right-6 ${bg}`;

    setTimeout(() => {
      toast.classList.remove('show');
      toast.classList.add('hide');
    }, 3000);
  }
}
