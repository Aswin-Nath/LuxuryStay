import { Component, ElementRef, ViewChild, AfterViewInit, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule, DOCUMENT, NgIf } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthenticationService, TokenResponse } from '../../core/services/authentication/authentication.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink, CommonModule, RouterLinkActive, NgIf],
  templateUrl: './login.html',
  styleUrls: ['./login.css'] // optional if you want extra styles
})
export class Login implements AfterViewInit {
  @ViewChild('toast') toast!: ElementRef<HTMLDivElement>;
  loading = false; // full screen loader toggle
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
    if (!this.validateIdentifierFormatOnInput()) {
      // Show a center red message when required fields are missing
      this.showToast('This is required field', 'error', 'center');
      return;
    }
    if (!this.validatePassword()) {
      this.showToast('This is required field', 'error', 'center');
      return;
    }

    const payload = this.getLoginPayload();
    if (!payload) return;

    // start loading UX
    this.loading = true;
    this.sendLoginRequest(payload);
  }

  onReset() {
    this.userInput = '';
    this.password = '';
    this.userError = '';
    this.passwordError = '';
    this.passwordDisabled = true;
    this.showToast('Form has been reset', 'info', 'top-right');
  }

  // Toast Helpers
  private showToast(message: string, type: 'success' | 'error' | 'info', position: 'top-right' | 'top-left' | 'center' = 'center') {
    const toastEl = this.toast.nativeElement;
    const msgEl = toastEl.querySelector('#toastMessage') as HTMLElement;
    const iconEl = toastEl.querySelector('#toastIcon') as HTMLElement;

    msgEl.textContent = message;

    // Reset position and set left/right/center depending on param
    let baseClass = `fixed top-4 px-6 py-3 rounded-lg shadow-lg transform transition-all duration-300 z-50 flex items-center gap-2 pointer-events-none`;
    if (position === 'top-left') {
      toastEl.style.left = '';
      toastEl.style.right = '';
      toastEl.style.transform = '';
      toastEl.className = `${baseClass} left-4`;
    } else if (position === 'top-right') {
      toastEl.style.left = '';
      toastEl.style.right = '';
      toastEl.style.transform = '';
      toastEl.className = `${baseClass} right-4`;
    } else {
      // center
      toastEl.style.left = '50%';
      toastEl.style.right = '';
      // ensure transform includes translateX(-50%) for centering
      toastEl.style.transform = 'translateX(-50%)';
      toastEl.className = `${baseClass}`;
    }
    // Keep track of position for hide animation
    toastEl.setAttribute('data-position', position);

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
    const toastEl = this.toast.nativeElement;
    const pos = toastEl.getAttribute('data-position') as 'top-left' | 'top-right' | 'center' | null;
    if (pos === 'top-left') {
      toastEl.classList.add('translate-x-neg-full', 'opacity-0');
    } else if (pos === 'top-right') {
      toastEl.classList.add('translate-x-full', 'opacity-0');
    } else {
      // center - fade out with opacity to not disrupt layout on mobile
      toastEl.classList.add('opacity-0');
    }
  }



  private sendLoginRequest(payload: LoginRequest) {
    this.authService.login(payload.identifier, payload.password).subscribe({
      next: (res) => this.handleLoginSuccess(res),
      error: (err: HttpErrorResponse) => {
        this.loading = false;
        this.handleLoginError(err);
      },
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
  // Store expiry duration if available
  if (response.expires_in !== undefined) {
    const ttl = Math.max(0, Number(response.expires_in));
    localStorage.setItem('expires_in', String(ttl));
  }
  // Store role in localStorage (optional)
  localStorage.setItem('auth_role_id', String(response.role_id));
  this.passwordError = '';
  this.showToast('Login successful!', 'success', 'top-right');
  // fade out page for a smoother redirect
  setTimeout(() => document.body.classList.add('fade-page'), 300);
  setTimeout(() => {
    this.loading = false;
    if(response.role_id==1){
      this.router.navigate(['/dashboard']);
    }
    else{
      this.router.navigate(['admin/dashboard']);

    }
  }, 900);
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