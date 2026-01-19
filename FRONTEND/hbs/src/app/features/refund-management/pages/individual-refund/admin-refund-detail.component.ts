import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RefundsService, Refund, RefundTransactionUpdate } from '../../../../services/refunds.service';

@Component({
  selector: 'app-admin-refund-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-refund-detail.component.html',
  styleUrl: './admin-refund-detail.component.css'
})
export class AdminRefundDetailComponent implements OnInit {
  refund: Refund | null = null;
  loading = true;
  error: string | null = null;
  showUpdateForm = false;
  updating = false;

  // Form state
  updatePayload: RefundTransactionUpdate = {};

  // Payment methods (mock data - replace with actual from backend)
  paymentMethods = [
    { id: 1, name: 'Credit Card' },
    { id: 2, name: 'Debit Card' },
    { id: 3, name: 'UPI' },
    { id: 4, name: 'Net Banking' },
    { id: 5, name: 'Bank Transfer' },
  ];

  statusOptions = [
    { value: 'INITIATED', label: 'Initiated' },
    { value: 'PROCESSING', label: 'Processing' },
    { value: 'COMPLETED', label: 'Completed' },
    { value: 'REJECTED', label: 'Rejected' },
    { value: 'CANCELLED', label: 'Cancelled' },
  ];

  constructor(
    private refundsService: RefundsService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      const refundId = parseInt(params['refundId'], 10);
      if (refundId) {
        this.loadRefund(refundId);
      }
    });
  }

  loadRefund(refundId: number): void {
    this.loading = true;
    this.error = null;

    this.refundsService.getAdminRefundDetail(refundId).subscribe({
      next: (data: Refund) => {
        this.refund = data;
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Error loading refund:', err);
        this.error = 'Failed to load refund details. Please try again.';
        this.loading = false;
      },
    });
  }

  // ========== UPDATE REFUND ==========
  showUpdateFormFn(): void {
    this.showUpdateForm = true;
    if (this.refund) {
      this.updatePayload = {
        status: this.refund.status,
        transaction_method_id: this.refund.transaction_method_id,
        transaction_number: this.refund.transaction_number,
      };
    }
  }

  updateRefund(): void {
    if (!this.refund) return;

    this.updating = true;
    this.refundsService.updateRefundTransaction(this.refund.refund_id, this.updatePayload).subscribe({
      next: (updated: Refund) => {
        this.refund = updated;
        this.showUpdateForm = false;
        this.updating = false;
        alert('Refund updated successfully!');
        window.location.reload();
      },
      error: (err: any) => {
        console.error('Error updating refund:', err);
        alert('Failed to update refund: ' + (err.error?.detail || 'Unknown error'));
        this.updating = false;
      },
    });
  }

  cancelUpdate(): void {
    this.showUpdateForm = false;
  }

  // ========== UTILITY METHODS ==========
  getStatusColor(status: string): string {
    return this.refundsService.getStatusColor(status);
  }

  getStatusIcon(status: string): string {
    return this.refundsService.getStatusIcon(status);
  }

  getTypeLabel(type: string): string {
    return this.refundsService.getTypeLabel(type);
  }

  formatCurrency(amount: number): string {
    return this.refundsService.formatCurrency(amount);
  }

  formatDate(dateString: string): string {
    return this.refundsService.formatDate(dateString);
  }

  formatDateTime(dateString: string): string {
    return this.refundsService.formatDateTime(dateString);
  }

  getPaymentMethodName(methodId: number | null): string {
    if (!methodId) return 'Not specified';
    const method = this.paymentMethods.find(m => m.id === methodId);
    return method ? method.name : 'Unknown method';
  }

  // ========== NAVIGATION ==========
  goBack(): void {
    this.router.navigate(['/admin/refunds']);
  }
}
