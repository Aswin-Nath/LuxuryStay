import { Component, OnInit, Output, EventEmitter, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface SearchFilters {
  searchText?: string;
  priceMin?: number;
  priceMax?: number;
  discountMin?: number;
  discountMax?: number;
  sortBy?: string;
  categoryFilter?: string;
}

@Component({
  selector: 'app-customer-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './customer-search.component.html',
  styleUrl: './customer-search.component.css',
})
export class CustomerSearchComponent implements OnInit {
  @Input() searchType: 'rooms' | 'offers' | 'wishlist' = 'rooms';
  @Input() categories: Array<{ id: string; name: string }> = [];
  @Output() filtersChanged = new EventEmitter<SearchFilters>();

  filters: SearchFilters = {
    searchText: '',
    priceMin: undefined,
    priceMax: undefined,
    discountMin: undefined,
    discountMax: undefined,
    sortBy: 'newest',
    categoryFilter: 'all',
  };

  get searchPlaceholder(): string {
    switch (this.searchType) {
      case 'rooms':
        return 'Search by room type, amenities...';
      case 'offers':
        return 'Search by offer name, discount...';
      case 'wishlist':
        return 'Search your wishlist...';
      default:
        return 'Search...';
    }
  }

  get showDiscountFilter(): boolean {
    return this.searchType === 'offers';
  }

  get showPriceFilter(): boolean {
    return this.searchType === 'rooms' || this.searchType === 'offers';
  }

  ngOnInit(): void {
    // Initialize categories if needed
  }

  onFilterChange(): void {
    this.filtersChanged.emit(this.filters);
  }

  onSearchChange(): void {
    this.filtersChanged.emit(this.filters);
  }

  resetFilters(): void {
    this.filters = {
      searchText: '',
      priceMin: undefined,
      priceMax: undefined,
      discountMin: undefined,
      discountMax: undefined,
      sortBy: 'newest',
      categoryFilter: 'all',
    };
    this.filtersChanged.emit(this.filters);
  }
}
