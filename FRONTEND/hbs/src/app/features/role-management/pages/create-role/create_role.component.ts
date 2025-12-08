import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-add-role-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './create_role.html',
  styleUrls: ['./create_role.css']
})
export class AddRoleModalComponent implements OnInit {
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<{ role_name: string; role_description: string }>();

  roleForm!: FormGroup;
  isSubmitting = false;
  errorMessage = '';

  constructor(private fb: FormBuilder) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  /**
   * Initialize form with validators
   */
  initializeForm(): void {
    this.roleForm = this.fb.group({
      role_name: ['', [Validators.required, Validators.minLength(2)]],
      role_description: ['', [Validators.required, Validators.minLength(5)]]
    });
  }

  /**
   * Get form control for template
   */
  get f() {
    return this.roleForm.controls;
  }

  /**
   * Check if field has error
   */
  hasError(fieldName: string, errorType: string): boolean {
    const field = this.roleForm.get(fieldName);
    return field ? field.hasError(errorType) && (field.dirty || field.touched) : false;
  }

  /**
   * Save new role
   */
  onSave(): void {
    if (this.roleForm.invalid) {
      Object.keys(this.roleForm.controls).forEach(key => {
        this.roleForm.get(key)?.markAsTouched();
      });
      this.errorMessage = 'Please fill in all required fields correctly';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    const roleData = this.roleForm.value;
    this.save.emit(roleData);
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
    this.roleForm.reset();
    this.errorMessage = '';
    Object.keys(this.roleForm.controls).forEach(key => {
      this.roleForm.get(key)?.markAsUntouched();
      this.roleForm.get(key)?.markAsPristine();
    });
  }

  /**
   * Called after successful save
   */
  finishSubmitting(): void {
    this.isSubmitting = false;
    this.resetForm();
    this.close.emit();
  }

  /**
   * Handle error after save
   */
  handleError(errorMessage: string): void {
    this.isSubmitting = false;
    this.errorMessage = errorMessage;
  }
}
