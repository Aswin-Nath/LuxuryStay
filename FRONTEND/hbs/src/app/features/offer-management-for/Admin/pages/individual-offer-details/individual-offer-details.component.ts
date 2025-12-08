import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { OfferService, Offer, OfferImage } from '../../../services/offer.service';
import { AdminNavbarComponent } from '../../../layout/Admin/admin-navbar/admin-navbar.component';
import { AdminSidebarComponent } from '../../../layout/Admin/admin-sidebar/admin-sidebar.component';

@Component({
  selector: 'app-individual-offer-details',
  standalone: true,
  imports: [CommonModule, AdminNavbarComponent, AdminSidebarComponent],
  templateUrl: './individual-offer-details.component.html',
  styleUrl: './individual-offer-details.component.css',
})
export class IndividualOfferDetailsComponent implements OnInit {
  offerId: number | null = null;
  offer: Offer | null = null;
  images: OfferImage[] = [];
  primaryImage: OfferImage | null = null;
  loading = true;
  error = '';
  actionLoading = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private offerService: OfferService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      if (params['id']) {
        this.offerId = parseInt(params['id'], 10);
        this.loadOfferDetails();
      } else {
        this.error = 'Invalid offer ID';
        this.loading = false;
      }
    });
  }

  loadOfferDetails(): void {
    if (!this.offerId) return;

    this.offerService.getOffer(this.offerId).subscribe({
      next: (offer) => {
        this.offer = offer;
        this.loadOfferImages();
      },
      error: () => {
        this.error = 'Failed to load offer details';
        this.loading = false;
      },
    });
  }

  loadOfferImages(): void {
    if (!this.offerId) return;

    this.offerService.getOfferImages(this.offerId).subscribe({
      next: (images) => {
        this.images = images;
        // Set primary image (first marked as primary or first uploaded)
        this.primaryImage = images.find(img => img.is_primary) || (images.length > 0 ? images[0] : null);
        this.loading = false;
      },
      error: () => {
        // Silently handle error - offers may not have images
        this.loading = false;
      },
    });
  }

  editOffer(offerId?: number): void {
    if (!offerId && this.offerId) offerId = this.offerId;
    if (offerId) {
      this.router.navigate(['/admin/offers/edit', offerId]);
    }
  }

  backToList(): void {
    this.router.navigate(['admin/offers']);
  }

  toggleOfferStatus(): void {
    if (!this.offer || !this.offerId) return;

    this.actionLoading = true;
    const newStatus = !this.offer.is_active;

    this.offerService.toggleOfferStatus(this.offerId, newStatus).subscribe({
      next: (updatedOffer) => {
        this.offer = updatedOffer;
        this.actionLoading = false;
      },
      error: (err) => {
        this.error = `Failed to ${newStatus ? 'activate' : 'deactivate'} offer`;
        this.actionLoading = false;
      },
    });
  }

  get isActive(): boolean {
    return this.offer?.is_active || false;
  }

  get isValid(): boolean {
    if (!this.offer) return false;
    const today = new Date();
    const validFrom = new Date(this.offer.valid_from);
    const validTo = new Date(this.offer.valid_to);
    return today >= validFrom && today <= validTo;
  }

  get usagePercentage(): number {
    if (!this.offer || !this.offer.max_uses) return 0;
    return Math.round((this.offer.current_uses / this.offer.max_uses) * 100);
  }
}
