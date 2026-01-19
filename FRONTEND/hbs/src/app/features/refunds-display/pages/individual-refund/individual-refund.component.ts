import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RefundsService, Refund } from '../../../../services/refunds.service';

@Component({
  selector: 'app-customer-refund-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './individual-refund.component.html',
  styleUrl: './individual-refund.component.css'
})
export class CustomerRefundDetailComponent implements OnInit {
  refund: Refund | null = null;
  loading = true;
  error: string | null = null;

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

    this.refundsService.getCustomerRefundDetail(refundId).subscribe({
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

  // ========== NAVIGATION ==========
  goBack(): void {
    this.router.navigate(['/customer/my-refunds']);
  }
}
