import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProfileService, ProfileResponse, ChangePasswordRequest } from '../../../core/services/profile/profile.service';
// import { AdminNavbarComponent } from '../../core/components/admin-navbar/admin-navbar.component';
// import { AdminSidebarComponent } from '../../core/components/admin-sidebar/admin-sidebar.component';
interface AdminProfile extends ProfileResponse {
  role?: string;
}
import { AdminSidebarComponent } from '../../../core/components/admin-sidebar/admin-sidebar.component';
import { AdminNavbarComponent } from '../../../core/components/admin-navbar/admin-navbar.component';
@Component({
  selector: 'app-admin-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminNavbarComponent,AdminSidebarComponent],
  templateUrl: './admin-profile.component.html',
  styleUrls: ['./admin-profile.component.css'],
  providers: [ProfileService],
})
export class AdminProfileComponent implements OnInit {
  private readonly profileService: ProfileService = inject(ProfileService);
  profileData: AdminProfile | null = null;
  profileImage: string = 'https://via.placeholder.com/150';
  isLoading: boolean = true;
  errorMessage: string = '';
  successMessage: string = '';
  currentPage: string = 'profile';

  // Edit mode flags
  editingFields: { [key: string]: boolean } = {
    phone: false,
    password: false,
  };

  // Error/Success message timeout
  private errorTimeout: any = null;
  private successTimeout: any = null;

  // Form data
  phoneNumber: string = '';

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
   * Load admin profile data from API
   */
  loadProfile(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.profileService.getProfile().subscribe({
      next: (data: ProfileResponse) => {
        this.profileData = data as AdminProfile;
        this.profileImage = data.profile_image_url || 'https://via.placeholder.com/150';
        this.phoneNumber = data.phone_number || '';
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
   * Save phone number to API
   */
  savePhoneNumber(): void {
    if (!this.profileData) return;

    const phoneValue = this.phoneNumber?.trim();
    if (!phoneValue) {
      this.errorMessage = 'Phone number cannot be empty';
      return;
    }

    const updatePayload = {
      phone_number: phoneValue,
    };

    this.profileService.updateProfile(updatePayload).subscribe({
      next: (response: ProfileResponse) => {
        this.profileData = response as AdminProfile;
        this.editingFields['phone'] = false;
        this.successMessage = 'Phone number updated successfully!';
        this.errorMessage = '';
        
        // Clear success message after 3 seconds
        if (this.successTimeout) clearTimeout(this.successTimeout);
        this.successTimeout = setTimeout(() => (this.successMessage = ''), 3000);
      },
      error: (err: any) => {
        console.error('Error updating phone number:', err);
        
        // Extract error message from various formats
        let errorMsg = 'Failed to update phone number. Please try again.';
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
   * Change admin password
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
        this.profileData = response as AdminProfile;
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
      case 'email':
        return this.profileData.email || 'Not set';
      case 'gender':
        return this.profileData.gender || 'Not set';
      case 'phone':
        return this.profileData.phone_number || 'Not set';
      case 'role':
        return this.getRoleDisplayName(this.profileData.role_id);
      default:
        return 'Not set';
    }
  }

  /**
   * Map role ID to display name
   */
  getRoleDisplayName(roleId: number | undefined): string {
    if (!roleId) return 'Not set';
    
    const roleMap: { [key: number]: string } = {
      1: 'Customer',
      2: 'Super Admin',
      3: 'Normal Admin',
      4: 'Content Admin',
    };
    
    return roleMap[roleId] || 'Not set';
  }
}
