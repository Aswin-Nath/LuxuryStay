import { Component, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink,CommonModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css'] // optional if you want extra styles
})
export class Login implements AfterViewInit {
  @ViewChild('toast') toast!: ElementRef<HTMLDivElement>;
  togglePassword() {
    this.showPassword = !this.showPassword;
  }
  enablePassword = false;
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

  // Hardcoded credentials (same as your JS)
  private readonly STORED_CUSTOMER_EMAIL = 'aswinnathte125@gmail.com';
  private readonly STORED_ADMIN_EMAIL = 'admin@gmail.com';
  private readonly STORED_PHONE = '8610476491';
  private readonly STORED_PASSWORD = 'Aswinnath@123';

  ngAfterViewInit() {
    // Initialize toast hidden
    this.hideToast();
  }

  togglePasswordVisibility() {
    this.showPassword = !this.showPassword;
  }

  validateUser() {
    const value = this.userInput.trim();

    if (!value) {
      this.userError = 'Email or phone number is required.';
      this.passwordDisabled = true;
      return false;
    }

    const isValidEmail = this.emailRegex.test(value);
    const isValidPhone = this.phoneRegex.test(value.replace(/\s/g, ''));
    const isKnownUser =
      value === this.STORED_CUSTOMER_EMAIL ||
      value === this.STORED_ADMIN_EMAIL ||
      value === this.STORED_PHONE ||
      value === `+91${this.STORED_PHONE}` ||
      value === this.STORED_PHONE.replace(/^0+/, '');

    if (!isValidEmail && !isValidPhone) {
      this.userError = 'Please enter a valid email or phone number.';
      this.passwordDisabled = true;
      return false;
    }

    if (!isKnownUser) {
      this.userError = 'User not found. Please check your credentials.';
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
    const userValid = this.validateUser();
    const passValid = this.validatePassword();

    if (!userValid || !passValid) return;

    const input = this.userInput.trim();
    const pwd = this.password;

    // Customer Login
    if (
      (input === this.STORED_CUSTOMER_EMAIL ||
       input === this.STORED_PHONE ||
       input === `+91${this.STORED_PHONE}`) &&
      pwd === this.STORED_PASSWORD
    ) {
      localStorage.setItem('is_customer_logged_in', 'true');
      localStorage.setItem('is_admin_logged_in', 'false');
      this.showToast('Customer login successful!', 'success');
      setTimeout(() => {
        window.location.href = '/Features/LandingPages/Customer/index.html';
      }, 800);
      return;
    }

    // Admin Login
    if (input === this.STORED_ADMIN_EMAIL && pwd === this.STORED_PASSWORD) {
      localStorage.setItem('is_admin_logged_in', 'true');
      localStorage.setItem('is_customer_logged_in', 'false');
      this.showToast('Welcome Admin!', 'success');
      setTimeout(() => {
        window.location.href = '/Features/Dashboard/Admin/index.html';
      }, 800);
      return;
    }

    // Invalid credentials
    this.passwordError = 'Invalid credentials. Please try again.';
    this.showToast('Login failed. Wrong email/phone or password.', 'error');
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
}