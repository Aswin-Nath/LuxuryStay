import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { IssuesService, IssueResponse } from '../../../../services/issues.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CustomerSidebarComponent } from "../../../../layout/Customer/customer-sidebar/customer-sidebar.component";
import { CustomerNavbarComponent } from "../../../../layout/Customer/customer-navbar/customer-navbar.component";

@Component({
  selector: 'app-edit-issue',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomerSidebarComponent, CustomerNavbarComponent],
  templateUrl: './edit-issue.component.html',
  styleUrls: ['./edit-issue.component.css']
})
export class EditIssueComponent implements OnInit, OnDestroy {
  issue: IssueResponse | null = null;
  issueId: number | null = null;
  
  // Form fields
  title: string = '';
  description: string = '';
  
  // Image upload properties
  newImages: any[] = [];
  selectedImageFiles: File[] = [];
  isUploadingImages = false;
  isDeletingImage = false;

  // Image viewer modal properties
  showLightbox = false;
  selectedImage: any = null;
  currentImageIndex = 0;
  
  isLoading = false;
  isSaving = false;
  errorMessage = '';
  successMessage = '';

  private destroy$ = new Subject<void>();

  constructor(
    private issuesService: IssuesService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.issueId = parseInt(params['id'], 10);
      if (this.issueId) {
        this.loadIssueDetails();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadIssueDetails(): void {
    if (!this.issueId) return;
    
    this.isLoading = true;
    this.issuesService
      .getMyIssueDetails(this.issueId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.issue = data;
          this.title = data.title;
          this.description = data.description;
          // Load images explicitly
          this.loadIssueImages();
          this.isLoading = false;
        },
        error: (err) => {
          this.errorMessage = 'Failed to load issue details. Please try again.';
          this.isLoading = false;
          console.error(err);
        }
      });
  }

  loadIssueImages(): void {
    if (!this.issueId) return;
    
    this.issuesService
      .getIssueImages(this.issueId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          console.log('Images loaded:', data);
          if (this.issue) {
            this.issue.images = data || [];
            console.log('Issue images updated:', this.issue.images);
          }
        },
        error: (err) => {
          console.error('Error loading issue images:', err);
          // Keep existing images from issue details response
        }
      });
  }

  saveChanges(): void {
    if (!this.issueId || !this.title.trim() || !this.description.trim()) {
      this.errorMessage = 'Please fill in all required fields.';
      return;
    }

    this.isSaving = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.issuesService
      .updateIssue(this.issueId, this.title, this.description)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          // After issue update, upload images if any are selected
          if (this.selectedImageFiles.length > 0) {
            this.uploadIssuImages();
          } else {
            this.handleUpdateSuccess();
          }
        },
        error: (err) => {
          this.errorMessage = err.error?.error || 'Failed to update issue. Please try again.';
          this.isSaving = false;
          console.error(err);
        }
      });
  }

  onImageSelect(event: any): void {
    const files = Array.from(event.target.files) as File[];
    files.forEach((file: File) => {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.newImages.push({
          name: file.name,
          preview: e.target.result,
          file: file
        });
      };
      reader.readAsDataURL(file);
    });
    this.selectedImageFiles = this.selectedImageFiles.concat(files);
  }

  removeNewImage(index: number): void {
    this.newImages.splice(index, 1);
    this.selectedImageFiles.splice(index, 1);
  }

  deleteExistingImage(imageId: number, index?: number): void {
    if (!this.issueId) return;

    this.issuesService
      .deleteIssueImage(this.issueId, imageId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          if (this.issue && this.issue.images) {
            const idx = index ?? this.issue.images.findIndex(img => img.image_id === imageId);
            if (idx >= 0) {
              this.issue.images.splice(idx, 1);
            }
          }
          this.successMessage = 'Image deleted successfully';
          setTimeout(() => (this.successMessage = ''), 2000);
        },
        error: (err: any) => {
          this.errorMessage = 'Failed to delete image';
        }
      });
  }

  onImageError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.backgroundColor = '#e5e7eb';
  }

  openLightbox(image: any): void {
    this.selectedImage = image;
    this.showLightbox = true;
    if (this.issue && this.issue.images) {
      this.currentImageIndex = this.issue.images.findIndex(img => img.image_id === image.image_id);
    }
  }

  closeLightbox(): void {
    this.showLightbox = false;
    this.selectedImage = null;
  }

  nextImage(): void {
    if (this.issue?.images && this.currentImageIndex < this.issue.images.length - 1) {
      this.currentImageIndex++;
      this.selectedImage = this.issue.images[this.currentImageIndex];
    }
  }

  prevImage(): void {
    if (this.currentImageIndex > 0) {
      this.currentImageIndex--;
      this.selectedImage = this.issue?.images?.[this.currentImageIndex];
    }
  }

  downloadImage(): void {
    if (this.selectedImage) {
      const link = document.createElement('a');
      link.href = this.selectedImage.image_url;
      link.download = `image-${this.selectedImage.image_id}.jpg`;
      link.click();
    }
  }

  uploadIssuImages(): void {
    if (!this.issueId || this.selectedImageFiles.length === 0) {
      this.handleUpdateSuccess();
      return;
    }

    this.isUploadingImages = true;
    this.issuesService
      .uploadIssueImages(this.issueId, this.selectedImageFiles)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.handleUpdateSuccess();
        },
        error: (err) => {
          console.error('Error uploading images:', err);
          // Still show success for issue update, but warn about images
          this.successMessage = 'Issue updated! However, image upload encountered an issue.';
          this.isSaving = false;
          this.isUploadingImages = false;
        }
      });
  }

  private handleUpdateSuccess(): void {
    this.successMessage = this.selectedImageFiles.length > 0 
      ? 'Issue and images updated successfully!' 
      : 'Issue updated successfully!';
    this.isSaving = false;
    this.isUploadingImages = false;
    setTimeout(() => {
      this.router.navigate(['/issues/details', this.issueId]);
    }, 1500);
  }

  cancelEdit(): void {
    this.router.navigate(['/issues/details', this.issueId]);
  }

  goBack(): void {
    this.router.navigate(['/issues']);
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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
}
