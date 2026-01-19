import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { RefundsService, Refund, RefundFilters } from '../../../../services/refunds.service';

@Component({
  selector: 'app-my-refunds',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './my-refunds.component.html',
  styleUrls: ['./my-refunds.component.css'],
})
export class MyRefundsComponent implements OnInit {
  // ========== STATE ==========
  refunds: Refund[] = [];
  loading = true;
  error: string | null = null;
  Math = Math;

  // ========== PAGINATION ==========
  currentPage = 1;
  pageSize = 10;
  totalRefunds = 0;
  totalPages = 1;
  jumpPageInput = '';

  // ========== FILTERS ==========
  filters: Partial<RefundFilters> = {
    booking_id: null,
    status: null,
    type: null,
    from_date: null,
    to_date: null,
  };

  // ========== FILTER OPTIONS ==========
  statusOptions = [
    { value: '', label: 'All Status' },
    { value: 'INITIATED', label: 'Initiated' },
    { value: 'PROCESSING', label: 'Processing' },
    { value: 'COMPLETED', label: 'Completed' },
    { value: 'REJECTED', label: 'Rejected' },
    { value: 'CANCELLED', label: 'Cancelled' },
  ];

  typeOptions = [
    { value: '', label: 'All Types' },
    { value: 'CANCELLATION', label: 'Cancellation' },
    { value: 'PARTIAL_CANCEL', label: 'Partial Cancellation' },
    { value: 'SERVICE_ISSUE', label: 'Service Issue' },
    { value: 'OVERBILLING', label: 'Overbilling' },
    { value: 'NO_SHOW', label: 'No Show' },
    { value: 'OTHER', label: 'Other' },
  ];

  constructor(
    private refundsService: RefundsService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadRefunds();
  }

  // ========== LOAD DATA ==========
  loadRefunds(): void {
    this.loading = true;
    this.error = null;

    const offset = (this.currentPage - 1) * this.pageSize;
    const queryFilters: Partial<RefundFilters> = {
      ...this.filters,
      limit: this.pageSize,
      offset: offset,
    };

    this.refundsService.getCustomerRefunds(queryFilters).subscribe({
      next: (response: Refund[]) => {
        this.refunds = response;
        this.loading = false;
        if (response.length < this.pageSize) {
          this.totalRefunds = offset + response.length;
        } else {
          this.totalRefunds = offset + this.pageSize + 1;
        }
        this.totalPages = Math.ceil(this.totalRefunds / this.pageSize) || 1;
      },
      error: (err: any) => {
        console.error('Error loading refunds:', err);
        this.error = 'Failed to load refunds. Please try again.';
        this.loading = false;
      },
    });
  }

  // ========== FILTER ACTIONS ==========
  applyFilters(): void {
    this.currentPage = 1;
    this.loadRefunds();
  }

  clearFilters(): void {
    this.filters = {
      booking_id: null,
      status: null,
      type: null,
      from_date: null,
      to_date: null,
    };
    this.currentPage = 1;
    this.loadRefunds();
  }

  // ========== PAGINATION ==========
  goToPage(pageNum: number): void {
    if (pageNum < 1 || pageNum > this.totalPages) {
      return;
    }
    this.currentPage = pageNum;
    this.loadRefunds();
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadRefunds();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadRefunds();
    }
  }

  jumpToPage(pageInput: string): void {
    const pageNum = parseInt(pageInput, 10);
    if (!isNaN(pageNum)) {
      this.goToPage(pageNum);
    }
  }

  getPaginationArray(): number[] {
    const pages: number[] = [];
    const maxPagesToShow = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(this.totalPages, startPage + maxPagesToShow - 1);

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    return pages;
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
  viewRefund(refundId: number): void {
    this.router.navigate(['/customer/refund-detail', refundId]);
  }
}
