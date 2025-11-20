import { Component, ElementRef, ViewChild, AfterViewInit, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule, DOCUMENT } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthenticationService, TokenResponse } from '../../core/services/authentication/authentication.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink,CommonModule,RouterLinkActive],
  templateUrl: './login.html',
  styleUrls: ['./login.css'] // optional if you want extra styles
})
export class Login implements AfterViewInit {
  @ViewChild('toast') toast!: ElementRef<HTMLDivElement>;
  togglePassword() {
    this.showPassword = !this.showPassword;
  }
  userInput: string = '';
  password: string = '';
  showPassword = false;

  // Validation states
  userError = '';
  passwordError = '';
  passwordDisabled = true;

  // Regex
  private emailRegex = /^[^\s@]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  private phoneRegex = /^\+?\d{10,15}$/;

  constructor(
    private authService: AuthenticationService,
    private router: Router,
    @Inject(DOCUMENT) private document: Document
  ) {}

  ngAfterViewInit() {
    // Initialize toast hidden
    this.hideToast();
  }

  validateIdentifierFormatOnInput() {
    const value = this.userInput.trim();

    if (!value) {
      this.userError = 'Email or phone number is required.';
      this.passwordDisabled = true;
      return false;
    }

    const isValidEmail = this.emailRegex.test(value);
    const isValidPhone = this.phoneRegex.test(value.replace(/\s/g, ''));

    if (!isValidEmail && !isValidPhone) {
      this.userError = 'Please enter a valid email or phone number.';
      this.passwordDisabled = true;
      return false;
    }

    this.userError = '';
    this.passwordDisabled = false;
    return true;
  }

  validatePassword() {
    if (!this.password.trim()) {
      this.passwordError = 'Password is required.';
      return false;
    }
    this.passwordError = '';
    return true;
  }

  onSubmit() {
    if (!this.validateIdentifierFormatOnInput()) return;
    if (!this.validatePassword()) return;

    const payload = this.getLoginPayload();
    if (!payload) return;

    this.sendLoginRequest(payload);
  }

  onReset() {
    this.userInput = '';
    this.password = '';
    this.userError = '';
    this.passwordError = '';
    this.passwordDisabled = true;
    this.showToast('Form has been reset', 'info');
  }

  // Toast Helpers
  private showToast(message: string, type: 'success' | 'error' | 'info') {
    const toastEl = this.toast.nativeElement;
    const msgEl = toastEl.querySelector('#toastMessage') as HTMLElement;
    const iconEl = toastEl.querySelector('#toastIcon') as HTMLElement;

    msgEl.textContent = message;

    toastEl.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 z-50 flex items-center gap-2`;

    if (type === 'success') {
      toastEl.classList.add('bg-green-500', 'text-white');
      iconEl.textContent = 'check_circle';
    } else if (type === 'error') {
      toastEl.classList.add('bg-red-500', 'text-white');
      iconEl.textContent = 'error';
    } else {
      toastEl.classList.add('bg-blue-500', 'text-white');
      iconEl.textContent = 'info';
    }
    toastEl.classList.remove('translate-x-full', 'opacity-0');
    setTimeout(() => this.hideToast(), 3000);
  }

  private hideToast() {
    this.toast.nativeElement.classList.add('translate-x-full', 'opacity-0');
  }



  private sendLoginRequest(payload: LoginRequest) {
    this.authService.login(payload.identifier, payload.password).subscribe({
      next: (res) => this.handleLoginSuccess(res),
      error: (err: HttpErrorResponse) => this.handleLoginError(err),
    });
  }

  private getLoginPayload(): LoginRequest | null {
    if (!this.userInput.trim() || !this.password) return null;
    return {
      identifier: this.userInput.trim(),
      password: this.password
    };
  }

private handleLoginSuccess(response: TokenResponse) {
  // Store access token in localStorage
  localStorage.setItem('access_token', response.access_token);
  // Store role in localStorage (optional)
  localStorage.setItem('auth_role_id', String(response.role_id));
  this.passwordError = '';
  this.showToast('Login successful!', 'success');
  setTimeout(() => this.router.navigate(['/home_page']), 800);
}


  private handleLoginError(err: HttpErrorResponse) {
    const message = err.error?.detail?.error ?? err.error?.message ?? 'Invalid credentials. Please try again.';
    this.passwordError = message;
    this.showToast('Login failed. Wrong email/phone or password.', 'error');
  }

}

interface LoginRequest {
  identifier: string;
  password: string;
}