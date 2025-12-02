import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { OfferService, OfferListItem, RoomType } from '../../../services/offer.service';
import { AdminNavbarComponent } from '../../../core/components/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../core/components/admin-sidebar/admin-sidebar.component';

@Component({
  selector: 'app-offer-management',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './offer-management.component.html',
  styleUrl: './offer-management.component.css',
})
export class OfferManagementComponent implements OnInit {
  offers: OfferListItem[] = [];
  filteredOffers: OfferListItem[] = [];
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;

  // Basic Filters

  filterActive: 'all' | 'active' | 'inactive' = 'all';
  sortBy: 'name' | 'date' | 'discount' = 'date';

  // Advanced Filters
  minDiscount: number | null = null;
  maxDiscount: number | null = null;
  startDate: string = '';
  endDate: string = '';
  selectedRoomTypeId: number | null = null;
  roomTypes: RoomType[] = [];
  loadingRoomTypes = false;

  // Pagination
  currentPage = 1;
  itemsPerPage = 10;

  constructor(private offerService: OfferService, private router: Router) {}

  ngOnInit(): void {
    this.loadRoomTypes();
    this.loadOffers();
  }

  // ============================================================
  // LOAD & FETCH
  // ============================================================

  loadRoomTypes(): void {
    this.loadingRoomTypes = true;
    this.offerService.getRoomTypes().subscribe({
      next: (data) => {
        this.roomTypes = data;
        this.loadingRoomTypes = false;
      },
      error: (err) => {
        console.error('Failed to load room types', err);
        this.loadingRoomTypes = false;
      },
    });
  }

  loadOffers(): void {
    this.loading = true;
    this.error = null;

    let isActive: boolean | undefined;
    if (this.filterActive === 'active') isActive = true;
    if (this.filterActive === 'inactive') isActive = false;

    // Build filters object
    const filters = {
      minDiscount: this.minDiscount || undefined,
      maxDiscount: this.maxDiscount || undefined,
      startDate: this.startDate ? new Date(this.startDate).toISOString().split('T')[0] : undefined,
      endDate: this.endDate ? new Date(this.endDate).toISOString().split('T')[0] : undefined,
      roomTypeId: this.selectedRoomTypeId || undefined,
    };

    this.offerService.listOffersAdmin(0, 500, filters).subscribe({
      next: (data) => {
        this.offers = data;
        this.applyFiltersAndSort();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load offers';
        console.error(err);
        this.loading = false;
      },
    });
  }

  // ============================================================
  // FILTER & SORT
  // ============================================================

  applyFiltersAndSort(): void {
    let filtered = [...this.offers];


    // Sort
    if (this.sortBy === 'name') {
      filtered.sort((a, b) => a.offer_name.localeCompare(b.offer_name));
    } else if (this.sortBy === 'discount') {
      filtered.sort((a, b) => b.discount_percent - a.discount_percent);
    } else {
      filtered.sort(
        (a, b) =>
          (new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      );
    }

    this.filteredOffers = filtered;
  }

  onSearchChange(): void {
    this.applyFiltersAndSort();
  }

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadOffers();
  }

  onDiscountFilterChange(): void {
    this.currentPage = 1;
    this.loadOffers();
  }

  onDateFilterChange(): void {
    this.currentPage = 1;
    this.loadOffers();
  }

  onRoomTypeFilterChange(): void {
    this.currentPage = 1;
    this.loadOffers();
  }

  resetFilters(): void {
    this.filterActive = 'all';
    this.minDiscount = null;
    this.maxDiscount = null;
    this.startDate = '';
    this.endDate = '';
    this.selectedRoomTypeId = null;
    this.sortBy = 'date';
    this.currentPage = 1;
    this.loadOffers();
  }

  onSortChange(): void {
    this.applyFiltersAndSort();
  }

  // ============================================================
  // NAVIGATION
  // ============================================================

  createNewOffer(): void {
    this.router.navigate(['/admin/offers/create']);
  }

  editOffer(offerId: number): void {
    this.router.navigate(['/admin/offers/edit', offerId]);
  }

  viewOffer(offerId: number): void {
    this.router.navigate(['/admin/offers/view', offerId]);
  }

  // ============================================================
  // TOGGLE & DELETE
  // ============================================================

  toggleOfferStatus(offer: OfferListItem): void {
    this.offerService.toggleOfferStatus(offer.offer_id, !offer.is_active).subscribe({
      next: () => {
        offer.is_active = !offer.is_active;
        this.successMessage = `Offer ${offer.is_active ? 'activated' : 'deactivated'}!`;
        setTimeout(() => (this.successMessage = null), 3000);
      },
      error: (err) => {
        this.error = 'Failed to toggle offer status';
        console.error(err);
      },
    });
  }

  deleteOffer(offer: OfferListItem): void {
    if (confirm(`Are you sure you want to delete "${offer.offer_name}"?`)) {
      this.offerService.deleteOffer(offer.offer_id).subscribe({
        next: () => {
          this.offers = this.offers.filter((o) => o.offer_id !== offer.offer_id);
          this.applyFiltersAndSort();
          this.successMessage = 'Offer deleted successfully!';
          setTimeout(() => (this.successMessage = null), 3000);
        },
        error: (err) => {
          // Check if error is due to active bookings
          if (err.status === 400 || err.error?.error?.includes('active booking')) {
            this.error = 'Cannot delete offer with active bookings. Please ensure all bookings are checked out or canceled.';
          } else if (err.status === 409 || err.error?.error?.includes('currently in use')) {
            this.error = 'This offer is currently being used. Cannot delete at this time.';
          } else {
            this.error = err.error?.error || 'Failed to delete offer';
          }
          console.error(err);
          setTimeout(() => (this.error = null), 5000);
        },
      });
    }
  }

  // ============================================================
  // PAGINATION
  // ============================================================

  get paginatedOffers(): OfferListItem[] {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    return this.filteredOffers.slice(start, start + this.itemsPerPage);
  }

  get totalPages(): number {
    return Math.ceil(this.filteredOffers.length / this.itemsPerPage);
  }

  previousPage(): void {
    if (this.currentPage > 1) this.currentPage--;
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) this.currentPage++;
  }

  // ============================================================
  // FORMATTING
  // ============================================================

  getValidityStatus(validFrom: string, validTo: string): string {
    const now = new Date();
    const from = new Date(validFrom);
    const to = new Date(validTo);

    if (now < from) return 'upcoming';
    if (now > to) return 'expired';
    return 'active';
  }

  getUsagePercentage(currentUses: number, maxUses?: number): number {
    if (!maxUses) return 0;
    return (currentUses / maxUses) * 100;
  }
}
