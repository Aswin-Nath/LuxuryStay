import { Component, ElementRef, ViewChild, AfterViewInit, Inject } from '@angular/core';
import { CommonModule, DOCUMENT } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { SignupService } from "../../core/services/signup/signup.service"
@Component({
  selector: 'app-signup',
  templateUrl: './signup.html',
  styleUrls: ['./signup.css'],
  imports: [CommonModule, RouterLink, RouterLinkActive, FormsModule],
  standalone: true
})
export class Signup implements AfterViewInit {
  @ViewChild('toast') toast!: ElementRef<HTMLDivElement>;
  loading = false; // fullscreen loader toggle
  name = '';
  gender = '';
  dob = '';
  email = '';
  phone = '';
  password = '';
  showPassword = false;

  emailPhoneEnabled = false;
  passwordEnabled = false;

  maxDob = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  nameError = '';
  genderError = '';
  dobError = '';
  emailError = '';
  phoneError = '';
  passwordError = '';

  private emailRegex = /^[^\s@]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  private phoneRegex = /^\+?\d{10,15}$/;
  private passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;


  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onPersonalInfoChange() {
    if (this.name.trim()) {
      this.nameError = '';
    }
    if (this.gender) {
      this.genderError = '';
    }
    if (this.dob) {
      this.dobError = this.dob > this.maxDob ? 'Date of birth must be in the past.' : '';
    }
    const ready = Boolean(this.name.trim() && this.gender && this.dob && this.dob <= this.maxDob);
    this.emailPhoneEnabled = ready;
    if (!ready) {
      this.email = '';
      this.phone = '';
      // do not clear the password on minor input changes or validation errors
      this.passwordEnabled = false;
      this.emailError = '';
      this.phoneError = '';
      this.passwordError = '';
    }
    this.updatePasswordEnabled();
  }

  onContactInfoChange() {
    this.updateEmailFormatError();
    this.updatePhoneFormatError();
    this.updatePasswordEnabled();
  }

  onSubmit() {
    const personalValid = this.validatePersonalInfo();
    const contactValid = this.validateContactInfo();
    const passwordValid = this.validatePassword();
    if (!personalValid || !contactValid || !passwordValid) {
      // show center red message on any validation failure (better for mobile spacing)
      this.showToast('This is required field', 'error', 'center');
      this.focusFirstInvalid();
      return;
    }

    const payload = this.getSignupPayload();
    if (!payload) return;
    console.log(payload, "this is payload");

    // Enable the full screen loading UX
    this.loading = true;
    this.sendSignupRequest(payload);
  }

  onReset() {
    this.name = '';
    this.gender = '';
    this.dob = '';
    this.email = '';
    this.phone = '';
    this.password = '';
    this.emailPhoneEnabled = false;
    this.passwordEnabled = false;
    this.nameError = '';
    this.genderError = '';
    this.dobError = '';
    this.emailError = '';
    this.phoneError = '';
    this.passwordError = '';
    this.showToast('Form has been reset', 'info', 'top-right');
  }

  private updateEmailFormatError() {
    const value = this.email.trim();
    // If no value, do not clear existing errors (eg. 'Email is required.') so highlight remains.
    if (!value) return;
    this.emailError = this.emailRegex.test(value) ? '' : 'Invalid email format.';
  }

  private updatePhoneFormatError() {
    const value = this.phone.trim();
    // If no value, do not clear existing errors (eg. 'Phone number is required.') so highlight remains.
    if (!value) return;
    this.phoneError = this.phoneRegex.test(value) ? '' : 'Invalid phone number.';
  }

  private validatePersonalInfo() {
    let valid = true;
    if (!this.name.trim()) {
      this.nameError = 'Name is required.';
      valid = false;
    }
    if (!this.gender) {
      this.genderError = 'Please select your gender.';
      valid = false;
    }
    if (!this.dob) {
      this.dobError = 'Date of birth is required.';
      valid = false;
    } else if (this.dob > this.maxDob) {
      this.dobError = 'Date of birth must be in the past.';
      valid = false;
    }
    this.onPersonalInfoChange();
    return valid;
  }

  private validateContactInfo() {
    let valid = true;
    if (!this.email.trim()) {
      this.emailError = 'Email is required.';
      valid = false;
    } else if (!this.emailRegex.test(this.email.trim())) {
      this.emailError = 'Please enter a valid email.';
      valid = false;
    }
    if (!this.phone.trim()) {
      this.phoneError = 'Phone number is required.';
      valid = false;
    } else if (!this.phoneRegex.test(this.phone.trim())) {
      this.phoneError = 'Please enter a valid phone number.';
      valid = false;
    }
    this.onContactInfoChange();
    return valid;
  }

  public validatePassword() {
    if (!this.password) {
      this.passwordError = 'Password is required.';
      return false;
    }
    if (!this.passwordRegex.test(this.password)) {
      this.passwordError =
        'Password must be at least 8 characters, include upper and lower case letters, a number, and a special character.';
      return false;
    }
    this.passwordError = '';
    return true;
  }

  private updatePasswordEnabled() {
    const ready =
      this.emailPhoneEnabled &&
      Boolean(this.email.trim() && this.phone.trim()) &&
      !this.emailError &&
      !this.phoneError;
    this.passwordEnabled = ready;
    if (!ready) {
      // keep the password value so users don't lose what they typed accidentally
      this.passwordError = '';
    }
  }


  private getSignupPayload(): SignupRequest | null {
    if (!this.passwordEnabled) return null;
    return {
      full_name: this.name.trim(),
      gender: this.gender,
      dob: this.dob,
      email: this.email.trim(),
      phone_number: this.phone.trim(),
      password: this.password
    };
  }
  constructor(private signupService: SignupService, private router: Router, @Inject(DOCUMENT) private document: Document) {}

  ngAfterViewInit() {
    this.hideToast();
  }

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

  private focusFirstInvalid() {
    try {
      const el = this.document.querySelector('.border-red-500') as HTMLElement | null;
      if (el) {
        if (typeof (el as any).focus === 'function') {
          (el as any).focus();
        }
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } catch (e) {
      // no-op
    }
  }

  private sendSignupRequest(payload: SignupRequest) {
    this.signupService.signup(payload).subscribe({
      next: (res) => {
        console.log('Signup success:', res);
        if (res?.access_token) {
          localStorage.setItem('access_token', res.access_token);
        }
        if (res?.role_id !== undefined) {
          localStorage.setItem('auth_role_id', String(res.role_id));
        }
        // show success toast
        this.showToast('Signup successful!', 'success', 'top-right');

        // Fade-out page then redirect
        setTimeout(() => document.body.classList.add('fade-page'), 300);
        setTimeout(() => {
          this.loading = false;
          this.router.navigate(['/home_page']);
        }, 900);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Signup failed:', err);
        this.loading = false;
        this.handleSignupError(err);
      }
    });
  }

  private handleSignupError(err: HttpErrorResponse) {
    const detail = err.error?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.error ?? err.error?.message ?? err.message ?? 'Signup failed. Please try again.';

    this.emailError = '';
    this.phoneError = '';
    this.passwordError = '';

    const normalized = message.toLowerCase();
    if (normalized.includes('email')) {
      this.emailError = message;
      return;
    }
    if (normalized.includes('phone')) {
      this.phoneError = message;
      return;
    }

    this.passwordError = message;
  }
}

interface SignupRequest {
  full_name: string;
  gender: string;
  dob: string;
  email: string;
  phone_number: string;
  password: string;
}
