import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminManagementService, CreateAdminPayload, Role } from '../../../core/services/admin-management/admin-management.service';
import { RoleManagementService } from '../../../core/services/role-management/role-management.service';

@Component({
  selector: 'app-admin-form-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-form-modal.component.html',
  styleUrls: ['./admin-form-modal.component.css']
})
export class AdminFormModalComponent implements OnInit {
  @Input() isOpen = false;
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() adminId: number | null = null;
  @Input() set adminData(data: any) {
    if (data && this.mode === 'edit') {
      this.formData = {
        full_name: data.full_name || '',
        email: data.email || '',
        password: '',
        phone_number: data.phone_number || '',
        dob: data.dob ? new Date(data.dob).toISOString().split('T')[0] : '',
        gender: data.gender ? this.normalizeGender(data.gender) : 'Male',
        role_id: data.role_id || 0
      };
      this.touched = {};
      this.errors = {};
    }
  }
  @Output() close = new EventEmitter<void>();
  @Output() success = new EventEmitter<string>();

  // Form data
  formData: CreateAdminPayload = {
    full_name: '',
    email: '',
    password: '',
    phone_number: '',
    dob: '',
    gender: 'Male',
    role_id: 0
  };

  // Available roles (excluding customer role)
  roles: Role[] = [];

  // Gender options
  genderOptions = ['Male', 'Female', 'Other'];

  // Validation state
  errors: { [key: string]: string } = {};
  isSubmitting = false;
  showPassword = false;

  // Email validation
  emailAvailable = true;

  // Phone number validation
  phoneChecking = false;
  phoneAvailable = true;
  phoneCheckTimeout: any = null;

  // Field touched state
  touched: { [key: string]: boolean } = {};

  constructor(
    private adminService: AdminManagementService,
    private roleService: RoleManagementService
  ) {}

  ngOnInit(): void {
    this.loadRoles();
  }

  /**
   * Load available roles from backend
   */
  loadRoles(): void {
    this.roleService.getRoles().subscribe({
      next: (allRoles: any[]) => {
        // Filter out customer role (role_id = 1) - only show admin roles
        this.roles = allRoles.filter(r => r.role_id !== 1);
        
        // Set default role if not already set
        if (this.roles.length > 0 && !this.formData.role_id) {
          this.formData.role_id = this.roles[0].role_id;
        }
      },
      error: (err: any) => {
        console.error('Error loading roles:', err);
        // Fallback to database roles if API fails
        this.roles = [
          { role_id: 2, role_name: 'super_admin' },
          { role_id: 3, role_name: 'normal_admin' },
          { role_id: 4, role_name: 'content admin' },
          { role_id: 5, role_name: 'BACKUP_ADMIN' },
          { role_id: 6, role_name: 'Offer Manager' }
        ];
      }
    });
  }

  /**
   * Normalize gender value
   */
  normalizeGender(gender: string): string {
    const normalized = gender.charAt(0).toUpperCase() + gender.slice(1).toLowerCase();
    return this.genderOptions.includes(normalized) ? normalized : 'Male';
  }

  /**
   * Toggle password visibility
   */
  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }
  /**
   * Validate full name
   */
  validateFullName(): void {
    const fullName = this.formData.full_name.trim();
    
    this.errors['full_name'] = '';
    
    if (!fullName) {
      this.errors['full_name'] = 'Full name is required';
    } else if (fullName.length < 2) {
      this.errors['full_name'] = 'Full name must be at least 2 characters';
    } else if (!/^[a-zA-Z\s'-]+$/.test(fullName)) {
      this.errors['full_name'] = 'Full name can only contain letters, spaces, hyphens and apostrophes';
    }
  }

  /**
   * Validate email availability
   */
  validateEmail(): void {
    const email = this.formData.email.trim();
    
    this.errors['email'] = '';
    this.emailAvailable = true;

    if (!email) {
      this.errors['email'] = 'Email is required';
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      this.errors['email'] = 'Invalid email format';
      return;
    }


  }

  /**
   * Validate phone number
   */
  validatePhoneNumber(): void {
    const phone = this.formData.phone_number.trim();
    
    this.errors['phone_number'] = '';
    this.phoneAvailable = true;

    if (!phone) {
      this.errors['phone_number'] = 'Phone number is required';
      return;
    }

    const phoneRegex = /^[0-9\s\-\+\(\)]+$/;
    if (!phoneRegex.test(phone)) {
      this.errors['phone_number'] = 'Invalid phone number format';
      return;
    }

    if (phone.replace(/\D/g, '').length < 7) {
      this.errors['phone_number'] = 'Phone number must have at least 7 digits';
      return;
    }


  }

  /**
   * Validate password
   */
  validatePasswordField(): void {
    const password = this.formData.password;
    this.errors['password'] = '';

    if (this.mode === 'create' && !password) {
      this.errors['password'] = 'Password is required';
      return;
    }

    if (password && password.length < 8) {
      this.errors['password'] = 'Password must be at least 8 characters';
      return;
    }

    if (password && !/[A-Z]/.test(password)) {
      this.errors['password'] = 'Password must contain at least one uppercase letter';
      return;
    }

    if (password && !/[a-z]/.test(password)) {
      this.errors['password'] = 'Password must contain at least one lowercase letter';
      return;
    }

    if (password && !/[0-9]/.test(password)) {
      this.errors['password'] = 'Password must contain at least one digit';
      return;
    }

    if (password && !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      this.errors['password'] = 'Password must contain at least one special character';
      return;
    }
  }

  /**
   * Validate date of birth
   */
  validateDateOfBirth(): void {
    const dob = this.formData.dob;
    
    this.errors['dob'] = '';

    if (!dob) {
      this.errors['dob'] = 'Date of birth is required';
      return;
    }

    const dobDate = new Date(dob);
    const today = new Date();
    const age = today.getFullYear() - dobDate.getFullYear();
    const monthDiff = today.getMonth() - dobDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dobDate.getDate())) {
      // Not birthday yet this year
    }

    if (age < 18) {
      this.errors['dob'] = 'Admin must be at least 18 years old';
      return;
    }

    if (age > 100) {
      this.errors['dob'] = 'Please enter a valid date of birth';
      return;
    }
  }

  /**
   * Check if field is touched
   */
  isTouched(field: string): boolean {
    return this.touched[field] || false;
  }

  /**
   * Mark field as touched
   */
  markTouched(field: string): void {
    this.touched[field] = true;
  }

  /**
   * Validate all fields
   */
  validateForm(): boolean {
    this.validateFullName();
    this.validateEmail();
    this.validatePhoneNumber();
    this.validatePasswordField();
    this.validateDateOfBirth();

    return !Object.keys(this.errors).some(key => this.errors[key]);
  }

  /**
   * Submit form
   */
  onSubmit(): void {
    // Mark all fields as touched
    Object.keys(this.formData).forEach(key => {
      this.touched[key] = true;
    });

    if (!this.validateForm()) {
      this.errors['general'] = 'Please fix all errors before submitting';
      return;
    }

    this.isSubmitting = true;
    this.errors['general'] = '';

    const payload: CreateAdminPayload = {
      ...this.formData,
      dob: this.formData.dob ? new Date(this.formData.dob).toISOString().split('T')[0] : ''
    };

    if (this.mode === 'create') {
      this.adminService.createAdmin(payload).subscribe({
        next: (response: any) => {
          this.success.emit('Admin created successfully');
          this.resetForm();
          this.close.emit();
        },
        error: (err: any) => {
          this.isSubmitting = false;
          if (err.error?.detail) {
            this.errors['general'] = err.error.detail;
          } else {
            this.errors['general'] = 'Failed to create admin. Please try again.';
          }
        }
      });
    } else if (this.mode === 'edit' && this.adminId) {
      // For edit mode, only include password if it was provided
      if (!payload.password) {
        delete payload.password;
      }
      
      this.adminService.updateAdmin(this.adminId, payload).subscribe({
        next: (response: any) => {
          this.success.emit('Admin updated successfully');
          this.resetForm();
          this.close.emit();
        },
        error: (err: any) => {
          this.isSubmitting = false;
          if (err.error?.detail) {
            this.errors['general'] = err.error.detail;
          } else {
            this.errors['general'] = 'Failed to update admin. Please try again.';
          }
        }
      });
    }
  }

  /**
   * Close modal
   */
  onClose(): void {
    this.resetForm();
    this.close.emit();
  }

  /**
   * Reset form
   */
  resetForm(): void {
    this.formData = {
      full_name: '',
      email: '',
      password: '',
      phone_number: '',
      dob: '',
      gender: 'Male',
      role_id: 0
    };
    this.errors = {};
    this.touched = {};
    this.isSubmitting = false;
    this.showPassword = false;
    this.emailAvailable = true;
    this.phoneAvailable = true;
  }
}
