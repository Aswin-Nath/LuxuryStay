import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ProfileService,ProfileResponse,ProfileUpdate,ChangePasswordRequest } from '../../../../services/profile.service';
import { CustomerNavbarComponent } from '../../../../layout/Customer/customer-navbar/customer-navbar.component';
import { CustomerSidebarComponent } from '../../../../layout/Customer/customer-sidebar/customer-sidebar.component';
@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomerNavbarComponent, CustomerSidebarComponent],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css'],
  providers: [ProfileService],
})
export class ProfileComponent implements OnInit {
  private readonly profileService: ProfileService = inject(ProfileService);
  private readonly router: Router = inject(Router);
  profileData: ProfileResponse | null = null;
  profileImage: string = 'https://via.placeholder.com/150';
  isLoading: boolean = true;
  errorMessage: string = '';
  successMessage: string = '';
  currentPage: string = 'profile';

  // Date picker modal properties
  showDatePickerModal: boolean = false;
  checkIn: string = '';
  checkOut: string = '';
  datePickerError: string = '';

  // Edit mode flags
  editingFields: { [key: string]: boolean } = {
    name: false,
    gender: false,
    email: false,
    phone: false,
    dob: false,
    password: false,
  };

  // Error/Success message timeout
  private errorTimeout: any = null;
  private successTimeout: any = null;

  // Form data
  formData: ProfileUpdate = {
    full_name: '',
    gender: '',
    phone_number: '',
    dob: '',
  };

  // Password change data
  passwordData: ChangePasswordRequest & { confirm_password?: string } = {
    current_password: '',
    new_password: '',
    confirm_password: '',
  };

  constructor() {}

  ngOnInit(): void {
    this.loadProfile();
  }

  /**
   * Load user profile data from API
   */
  loadProfile(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.profileService.getProfile().subscribe({
      next: (data: ProfileResponse) => {
        this.profileData = data;
        this.profileImage = data.profile_image_url || 'https://via.placeholder.com/150';
        this.formData = {
          full_name: data.full_name,
          phone_number: data.phone_number || '',
          gender: data.gender || '',
          dob: data.dob || '',
        };
        this.isLoading = false;
      },
      error: (err: any) => {
        console.error('Error loading profile:', err);
        
        let errorMsg = 'Failed to load profile. Please try again.';
        if (err?.error?.detail) {
          errorMsg = err.error.detail;
        } else if (typeof err?.error === 'string') {
          errorMsg = err.error;
        }
        
        this.errorMessage = errorMsg;
        this.isLoading = false;
      },
    });
  }

  /**
   * Open date picker modal for booking
   */


  /**
   * Close date picker modal
   */
  closeBookingModal(): void {
    this.showDatePickerModal = false;
    this.datePickerError = '';
  }

  /**
   * Proceed with booking - navigate to booking component with dates
   */
  proceedWithBooking(): void {
    if (!this.checkIn || !this.checkOut) {
      this.datePickerError = 'Please select check-in and check-out dates';
      return;
    }

    if (this.checkIn >= this.checkOut) {
      this.datePickerError = 'Check-out date must be after check-in date';
      return;
    }

    this.datePickerError = '';
    
    // Navigate to booking component with dates as query parameters
    this.router.navigate(['/booking'], {
      queryParams: {
        checkIn: this.checkIn,
        checkOut: this.checkOut
      }
    });
  }

  /**
   * Calculate number of nights
   */
  calculateNumberOfNights(): number {
    if (!this.checkIn || !this.checkOut) return 1;
    const start = new Date(this.checkIn);
    const end = new Date(this.checkOut);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(1, diffDays);
  }

  /**
   * Toggle edit mode for a field
   */
  toggleEdit(field: string): void {
    this.editingFields[field] = !this.editingFields[field];
    
    // Clear error message when toggling edit
    if (this.editingFields[field]) {
      this.errorMessage = '';
    }
    
    // Reset password form when toggling off
    if (field === 'password' && !this.editingFields[field]) {
      this.passwordData = {
        current_password: '',
        new_password: '',
        confirm_password: '',
      };
    }
  }

  /**
   * Save profile field to API
   */
  saveField(field: string): void {
    if (!this.profileData) return;

    const updatePayload: ProfileUpdate = {};
    let fieldValue: string | undefined;

    switch (field) {
      case 'name':
        fieldValue = this.formData.full_name?.trim();
        if (!fieldValue) {
          this.errorMessage = 'Name cannot be empty';
          return;
        }
        updatePayload.full_name = fieldValue;
        break;
      case 'gender':
        fieldValue = this.formData.gender?.trim();
        updatePayload.gender = fieldValue;
        break;
      case 'phone':
        fieldValue = this.formData.phone_number?.trim();
        updatePayload.phone_number = fieldValue;
        break;
      case 'dob':
        fieldValue = this.formData.dob?.trim();
        updatePayload.dob = fieldValue;
        break;
      default:
        return;
    }

    this.profileService.updateProfile(updatePayload).subscribe({
      next: (response: ProfileResponse) => {
        this.profileData = response;
        this.editingFields[field] = false;
        this.successMessage = `${field.charAt(0).toUpperCase() + field.slice(1)} updated successfully!`;
        this.errorMessage = '';
        
        // Clear success message after 3 seconds
        if (this.successTimeout) clearTimeout(this.successTimeout);
        this.successTimeout = setTimeout(() => (this.successMessage = ''), 3000);
      },
      error: (err: any) => {
        console.error(`Error updating ${field}:`, err);
        
        // Extract error message from various formats
        let errorMsg = `Failed to update ${field}. Please try again.`;
        if (err?.error?.detail) {
          errorMsg = err.error.detail;
        } else if (err?.error?.message) {
          errorMsg = err.error.message;
        } else if (typeof err?.error === 'string') {
          errorMsg = err.error;
        }
        
        this.errorMessage = errorMsg;
        
        // Clear error after 5 seconds
        if (this.errorTimeout) clearTimeout(this.errorTimeout);
        this.errorTimeout = setTimeout(() => (this.errorMessage = ''), 5000);
      },
    });
  }

  /**
   * Change user password
   */
  changePassword(): void {
    // Validation
    if (!this.passwordData.current_password?.trim()) {
      this.errorMessage = 'Please enter your current password';
      return;
    }

    if (!this.passwordData.new_password?.trim()) {
      this.errorMessage = 'Please enter a new password';
      return;
    }

    if (this.passwordData.new_password !== this.passwordData.confirm_password) {
      this.errorMessage = 'New passwords do not match';
      return;
    }

    if (this.passwordData.new_password.length < 8) {
      this.errorMessage = 'Password must be at least 8 characters long';
      return;
    }

    if (this.passwordData.current_password === this.passwordData.new_password) {
      this.errorMessage = 'New password must be different from current password';
      return;
    }

    const changePasswordPayload: ChangePasswordRequest = {
      current_password: this.passwordData.current_password,
      new_password: this.passwordData.new_password,
    };

    this.profileService.changePassword(changePasswordPayload).subscribe({
      next: (response: any) => {
        this.successMessage = response?.message || 'Password changed successfully!';
        this.editingFields['password'] = false;
        this.errorMessage = '';
        this.passwordData = {
          current_password: '',
          new_password: '',
          confirm_password: '',
        };
        
        // Clear success message after 3 seconds
        if (this.successTimeout) clearTimeout(this.successTimeout);
        this.successTimeout = setTimeout(() => (this.successMessage = ''), 3000);
      },
      error: (err: any) => {
        console.error('Error changing password:', err);
        
        // Extract error message from various possible response formats
        let errorMsg = 'Failed to change password. Please try again.';
        
        if (err?.error?.detail) {
          errorMsg = err.error.detail;
        } else if (err?.error?.message) {
          errorMsg = err.error.message;
        } else if (err?.message) {
          errorMsg = err.message;
        } else if (typeof err?.error === 'string') {
          errorMsg = err.error;
        } else if (err?.status === 401) {
          errorMsg = 'Current password is incorrect. Please try again.';
        } else if (err?.status === 400) {
          errorMsg = 'Password does not meet requirements. Please try again.';
        }
        
        this.errorMessage = errorMsg;
        
        // Clear error after 5 seconds
        if (this.errorTimeout) clearTimeout(this.errorTimeout);
        this.errorTimeout = setTimeout(() => (this.errorMessage = ''), 5000);
      },
    });
  }

  /**
   * Handle profile image upload
   */
  onImageUpload(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;

    if (!files || files.length === 0) return;

    const file = files[0];

    // Validate file type
    if (!file.type.startsWith('image/')) {
      this.errorMessage = 'Please select a valid image file';
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      this.errorMessage = 'File size must be less than 5MB';
      return;
    }

    // Preview image
    const reader = new FileReader();
    reader.onload = (e) => {
      this.profileImage = e.target?.result as string;
    };
    reader.readAsDataURL(file);

    // Upload to API
    this.profileService.uploadProfileImage(file).subscribe({
      next: (response: ProfileResponse) => {
        this.profileData = response;
        this.successMessage = 'Profile image updated successfully!';
        this.errorMessage = '';
        
        // Clear success message after 3 seconds
        if (this.successTimeout) clearTimeout(this.successTimeout);
        this.successTimeout = setTimeout(() => (this.successMessage = ''), 3000);
      },
      error: (err: any) => {
        console.error('Error uploading image:', err);
        
        let errorMsg = 'Failed to upload image. Please try again.';
        if (err?.error?.detail) {
          errorMsg = err.error.detail;
        } else if (typeof err?.error === 'string') {
          errorMsg = err.error;
        }
        
        this.errorMessage = errorMsg;
        this.profileImage = this.profileData?.profile_image_url || 'https://via.placeholder.com/150';
        
        // Clear error after 5 seconds
        if (this.errorTimeout) clearTimeout(this.errorTimeout);
        this.errorTimeout = setTimeout(() => (this.errorMessage = ''), 5000);
      },
    });
  }

  /**
   * Get display value for a field
   */
  getDisplayValue(field: string): string {
    if (!this.profileData) return 'Not set';

    switch (field) {
      case 'name':
        return this.profileData.full_name || 'Not set';
      case 'gender':
        return this.profileData.gender || 'Not set';
      case 'email':
        return this.profileData.email || 'Not set';
      case 'phone':
        return this.profileData.phone_number || 'Not set';
      case 'dob':
        return this.profileData.dob || 'Not set';
      default:
        return 'Not set';
    }
  }
}

