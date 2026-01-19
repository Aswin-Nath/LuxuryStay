import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { IssuesService, IssueResponse, ChatMessage, Image } from '../../../../services/issues.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CustomerSidebarComponent } from "../../../../layout/Customer/customer-sidebar/customer-sidebar.component";
import { CustomerNavbarComponent } from "../../../../layout/Customer/customer-navbar/customer-navbar.component";

@Component({
  selector: 'app-issue-details-customer',
  standalone: true,
  imports: [CommonModule, FormsModule, CustomerNavbarComponent],
  templateUrl: './issue-details.component.html',
  styleUrls: ['./issue-details.component.css']
})
export class IssueDetailsCustomerComponent implements OnInit, OnDestroy {
  issue: IssueResponse | null = null;
  chats: ChatMessage[] = [];
  images: Image[] = [];
  
  isLoadingIssue = false;
  isLoadingChats = false;
  isPostingChat = false;
  errorMessage = '';
  successMessage = '';
  
  newChatMessage = '';
  issueId: number | null = null;

  // Lightbox
  selectedImage: Image | null = null;
  showLightbox = false;
  currentImageIndex = 0;

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
        this.loadChats();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadIssueDetails(): void {
    if (!this.issueId) return;
    
    this.isLoadingIssue = true;
    this.issuesService
      .getMyIssueDetails(this.issueId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.issue = data;
          this.images = data.images || [];
          // Load images explicitly via API
          this.loadIssueImages();
          this.isLoadingIssue = false;
        },
        error: (err) => {
          this.errorMessage = 'Failed to load issue details. Please try again.';
          this.isLoadingIssue = false;
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
          this.images = data || [];
        },
        error: (err) => {
          console.error('Error loading issue images:', err);
          // Keep the images from the issue details response
        }
      });
  }

  loadChats(): void {
    if (!this.issueId) return;
    
    this.isLoadingChats = true;
    this.issuesService
      .getIssueChats(this.issueId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.chats = data;
          this.isLoadingChats = false;
          // Auto-scroll to bottom
          setTimeout(() => {
            const chatContainer = document.querySelector('#chatMessages');
            if (chatContainer) {
              chatContainer.scrollTop = chatContainer.scrollHeight;
            }
          }, 100);
        },
        error: (err) => {
          console.error('Failed to load chats:', err);
          this.isLoadingChats = false;
        }
      });
  }

  postChat(): void {
    if (!this.issueId || !this.newChatMessage.trim()) {
      return;
    }

    this.isPostingChat = true;
    this.issuesService
      .postChat(this.issueId, this.newChatMessage)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (chat) => {
          this.chats.push(chat);
          this.newChatMessage = '';
          this.isPostingChat = false;
          this.successMessage = 'Message sent!';
          setTimeout(() => (this.successMessage = ''), 3000);
          
          // Auto-scroll to bottom
          setTimeout(() => {
            const chatContainer = document.querySelector('#chatMessages');
            if (chatContainer) {
              chatContainer.scrollTop = chatContainer.scrollHeight;
            }
          }, 100);
        },
        error: (err) => {
          this.errorMessage = 'Failed to send message. Please try again.';
          this.isPostingChat = false;
          console.error(err);
        }
      });
  }

  openLightbox(image: Image): void {
    this.selectedImage = image;
    this.currentImageIndex = this.images.indexOf(image);
    this.showLightbox = true;
  }

  closeLightbox(): void {
    this.showLightbox = false;
    this.selectedImage = null;
  }

  nextImage(): void {
    if (this.currentImageIndex < this.images.length - 1) {
      this.currentImageIndex++;
      this.selectedImage = this.images[this.currentImageIndex];
    }
  }

  prevImage(): void {
    if (this.currentImageIndex > 0) {
      this.currentImageIndex--;
      this.selectedImage = this.images[this.currentImageIndex];
    }
  }

  downloadImage(): void {
    if (this.selectedImage) {
      const link = document.createElement('a');
      link.href = this.selectedImage.image_url;
      link.target = '_blank';
      link.download = `issue-image-${this.selectedImage.image_id}`;
      link.click();
    }
  }

  editIssue(): void {
    if (this.issueId) {
      this.router.navigate(['/issues/edit', this.issueId]);
    }
  }

  goBack(): void {
    this.router.navigate(['/issues/']);
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

  Math = Math;
}
