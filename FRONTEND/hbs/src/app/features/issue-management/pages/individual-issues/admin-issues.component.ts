import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IssuesService, IssueResponse } from '../../../../services/issues.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { AdminNavbarComponent } from "../../../../layout/Admin/admin-navbar/admin-navbar.component";
import { AdminSidebarComponent } from "../../../../layout/Admin/admin-sidebar/admin-sidebar.component";

@Component({
  selector: 'app-admin-issues',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './admin-issues.component.html',
  styleUrls: ['./admin-issues.component.css']
})
export class AdminIssuesComponent implements OnInit, OnDestroy {
  issues: IssueResponse[] = [];
  filteredIssues: IssueResponse[] = [];
  isLoading = false;
  errorMessage = '';
  successMessage = '';

  // Pagination
  currentPage = 1;
  pageSize = 5;
  pageSizeOptions = [5, 10, 15, 20];
  totalRecords = 0;
  totalPages = 0;

  // Filters
  filterStatus = 'all';
  searchText = '';
  roomNo = '';
  sortBy = 'recent';
  dateRangeStart = '';
  dateRangeEnd = '';

  private destroy$ = new Subject<void>();

  constructor(
    private issuesService: IssuesService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadIssues();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadIssues(): void {
    this.isLoading = true;
    
    // Convert filter values to appropriate types for backend
    const status = this.filterStatus !== 'all' ? this.filterStatus : undefined;
    const room_id = this.roomNo ? this.roomNo : undefined;
    const search = this.searchText || undefined;
    const date_from = this.dateRangeStart || undefined;
    const date_to = this.dateRangeEnd || undefined;
    
    this.issuesService
      .getAllIssuesAdmin(100, 0, status, room_id, search, date_from, date_to, this.sortBy)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.issues = data;
          this.filteredIssues = data;  // Backend already filters, just display
          this.isLoading = false;
          this.calculateTotalPages();
        },
        error: (err) => {
          this.errorMessage = 'Failed to load issues. Please try again.';
          this.isLoading = false;
          console.error(err);
        }
      });
  }

  applyFilters(): void {
    // Now just call loadIssues which calls backend with filters
    this.loadIssues();
  }

  calculateTotalPages(): void {
    this.totalRecords = this.filteredIssues.length;
    this.totalPages = Math.ceil(this.filteredIssues.length / this.pageSize);
  }

  changePageSize(size: number): void {
    this.pageSize = size;
    this.currentPage = 1;
    this.calculateTotalPages();
  }

  getCurrentPageIssues(): IssueResponse[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return this.filteredIssues.slice(startIndex, endIndex);
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPages = 5;
    
    if (this.totalPages <= maxPages) {
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, this.currentPage - 2);
      const endPage = Math.min(this.totalPages, this.currentPage + 2);
      
      if (startPage > 1) pages.push(1);
      if (startPage > 2) pages.push(-1); // -1 represents ellipsis
      
      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }
      
      if (endPage < this.totalPages - 1) pages.push(-1);
      if (endPage < this.totalPages) pages.push(this.totalPages);
    }
    
    return pages;
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  jumpToPage(): void {
    const input = prompt(`Enter page number (1-${this.totalPages}):`);
    if (input) {
      const page = parseInt(input, 10);
      this.goToPage(page);
    }
  }

  getStatusColor(status: string): string {
    switch (status.toUpperCase()) {
      case 'OPEN':
        return 'bg-blue-100 text-blue-800';
      case 'IN_PROGRESS':
        return 'bg-yellow-100 text-yellow-800';
      case 'RESOLVED':
        return 'bg-green-100 text-green-800';
      case 'CLOSED':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }

  viewIssueDetails(issueId: number): void {
    this.router.navigate(['/admin/issues/details', issueId]);
  }

  resetFilters(): void {
    this.filterStatus = 'all';
    this.searchText = '';
    this.roomNo = '';
    this.sortBy = 'recent';
    this.dateRangeStart = '';
    this.dateRangeEnd = '';
    this.currentPage = 1;
    this.pageSize = 5;
    this.loadIssues();  // Reload with no filters
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  Math = Math;
}
