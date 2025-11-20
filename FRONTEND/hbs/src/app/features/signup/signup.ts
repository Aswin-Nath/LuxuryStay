import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
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
export class Signup {
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
      this.password = '';
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
    if (!personalValid || !contactValid || !passwordValid) return;

    const payload = this.getSignupPayload();
    if (!payload) return;
    console.log(payload,"this is payload")
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
  }

  private updateEmailFormatError() {
    const value = this.email.trim();
    if (!value) {
      this.emailError = '';
      return;
    }
    this.emailError = this.emailRegex.test(value) ? '' : 'Invalid email format.';
  }

  private updatePhoneFormatError() {
    const value = this.phone.trim();
    if (!value) {
      this.phoneError = '';
      return;
    }
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

  private validatePassword() {
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
      this.password = '';
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
  constructor(private signupService: SignupService, private router: Router) {}

  private sendSignupRequest(payload: SignupRequest) {
    this.signupService.signup(payload).subscribe({
      next: (res) => {
        console.log('Signup success:', res);
        setTimeout(() => this.router.navigate(['/home_page']), 800);
      },
      error: (err: HttpErrorResponse) => {
        console.error('Signup failed:', err);
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
