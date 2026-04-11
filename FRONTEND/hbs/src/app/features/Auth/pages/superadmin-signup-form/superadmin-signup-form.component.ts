import { Component, ElementRef, ViewChild, AfterViewInit, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule, DOCUMENT, NgIf } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthenticationService, TokenResponse } from '../../../../services/authentication.service';

@Component({
  selector: 'app-superadmin-signup',
  standalone: true,
  imports: [FormsModule, RouterLink, CommonModule, RouterLinkActive, NgIf],
  templateUrl: './superadmin-signup-form.html',
  styleUrls: ['./superadmin-signup-form.css']
})
export class SuperAdminSignup implements AfterViewInit {
  @ViewChild('toast') toast!: ElementRef<HTMLDivElement>;
  loading = false;
  
  email: string = '';
  password: string = '';
  confirmPassword: string = '';
  showPassword = false;
  showConfirmPassword = false;

  // Validation states
  emailError = '';
  passwordError = '';
  confirmPasswordError = '';
  passwordDisabled = true;

  // Password strength tracking
  passwordRequirements = {
    length: false,
    uppercase: false,
    lowercase: false,
    digit: false,
    special: false
  };

  // Regex
  private emailRegex = /^[^\s@]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  constructor(
    private authService: AuthenticationService,
    private router: Router,
    @Inject(DOCUMENT) private document: Document
  ) {}

  ngAfterViewInit() {
    this.hideToast();
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  toggleConfirmPassword() {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  validateEmailFormatOnInput() {
    const value = this.email.trim();

    if (!value) {
      this.emailError = 'Email is required.';
      this.passwordDisabled = true;
      return false;
    }

    const isValidEmail = this.emailRegex.test(value);

    if (!isValidEmail) {
      this.emailError = 'Please enter a valid email address.';
      this.passwordDisabled = true;
      return false;
    }

    this.emailError = '';
    this.passwordDisabled = false;
    return true;
  }

  validatePasswordOnInput() {
    const password = this.password;

    // Update requirements
    this.passwordRequirements.length = password.length >= 8;
    this.passwordRequirements.uppercase = /[A-Z]/.test(password);
    this.passwordRequirements.lowercase = /[a-z]/.test(password);
    this.passwordRequirements.digit = /\d/.test(password);
    this.passwordRequirements.special = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

    // Check if all requirements are met
    const allMet = Object.values(this.passwordRequirements).every(req => req);
    
    if (!password.trim()) {
      this.passwordError = 'Password is required.';
      return false;
    }

    if (!allMet) {
      this.passwordError = 'Password does not meet all requirements.';
      return false;
    }

    this.passwordError = '';
    return true;
  }

  validateConfirmPassword() {
    if (!this.confirmPassword.trim()) {
      this.confirmPasswordError = 'Please confirm your password.';
      return false;
    }

    if (this.password !== this.confirmPassword) {
      this.confirmPasswordError = 'Passwords do not match.';
      return false;
    }

    this.confirmPasswordError = '';
    return true;
  }

  onSubmit() {
    if (!this.validateEmailFormatOnInput()) {
      this.showToast('Email is required and must be valid', 'error', 'center');
      return;
    }
    if (!this.validatePasswordOnInput()) {
      this.showToast('Password does not meet requirements', 'error', 'center');
      return;
    }
    if (!this.validateConfirmPassword()) {
      this.showToast('Passwords do not match', 'error', 'center');
      return;
    }

    this.loading = true;
    this.sendSignupRequest();
  }

  onReset() {
    this.email = '';
    this.password = '';
    this.confirmPassword = '';
    this.emailError = '';
    this.passwordError = '';
    this.confirmPasswordError = '';
    this.passwordDisabled = true;
    this.passwordRequirements = {
      length: false,
      uppercase: false,
      lowercase: false,
      digit: false,
      special: false
    };
    this.showToast('Form has been reset', 'info', 'top-right');
  }

  private sendSignupRequest() {
    const payload = {
      email: this.email,
      password: this.password
    };

    this.authService.superAdminSignup(payload).subscribe({
      next: (response: any) => {
        this.loading = false;
        this.showToast(`Super Admin account created! User ID: ${response.user_id}`, 'success', 'center');
        setTimeout(() => {
          this.router.navigate(['/superadmin/login']);
        }, 2000);
      },
      error: (error: HttpErrorResponse) => {
        this.loading = false;
        let errorMessage = 'Signup failed. Please try again.';
        if (error.status === 409) {
          errorMessage = 'Email already registered.';
        } else if (error.status === 400) {
          errorMessage = error.error?.detail || 'Invalid email or password.';
        } else if (error.error?.detail) {
          errorMessage = error.error.detail;
        }
        this.showToast(errorMessage, 'error', 'center');
      }
    });
  }

  // Toast Helpers
  private showToast(
    message: string,
    type: 'success' | 'error' | 'info',
    position: 'top-right' | 'top-left' | 'center' = 'center'
  ) {
    const toastEl = this.toast.nativeElement;
    const msgEl = toastEl.querySelector('#toastMessage') as HTMLElement;
    const iconEl = toastEl.querySelector('#toastIcon') as HTMLElement;

    msgEl.textContent = message;

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
      toastEl.style.left = '50%';
      toastEl.style.right = '';
      toastEl.style.transform = 'translateX(-50%)';
      toastEl.className = `${baseClass}`;
    }
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
    const toastEl = this.toast?.nativeElement;
    if (!toastEl) return;
    const position = toastEl.getAttribute('data-position') || 'center';
    toastEl.classList.remove('bg-green-500', 'bg-red-500', 'bg-blue-500', 'text-white');
    if (position === 'center') {
      toastEl.style.transform = 'translateX(-50%) translateY(-150%)';
    } else {
      toastEl.style.transform = 'translateX(calc(100vw + 20px))';
    }
    toastEl.style.opacity = '0';
  }
}
