import { Component, OnInit, ViewChild, ElementRef, inject, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RoomsService } from '../../../../../shared/services/rooms.service';

interface BulkUploadResults {
  total_processed: number;
  successfully_created: number;
  skipped: number;
  created_rooms: Array<{
    room_id: number;
    room_no: string;
    room_type_id: number;
  }>;
  skipped_rooms: Array<{
    room_no: string;
    reason: string;
  }>;
}

@Component({
  selector: 'app-bulk-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './bulk-upload.html',
  styleUrl: './bulk-upload.css'
})
export class BulkUploadComponent implements OnInit {
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
  @Input() isOpen = false;
  @Output() close = new EventEmitter<void>();
  @Output() uploadComplete = new EventEmitter<void>();

  selectedFile: File | null = null;
  selectedFileName: string = '';
  isUploading = false;
  uploadResults: BulkUploadResults | null = null;

  private roomsService = inject(RoomsService);

  constructor() {}

  ngOnInit(): void {}

  /**
   * Handle file selection
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      
      // Validate file type
      if (!file.name.endsWith('.csv')) {
        this.showToast('Please select a valid CSV file', 'error');
        return;
      }

      this.selectedFile = file;
      this.selectedFileName = file.name;
    }
  }

  /**
   * Show toast notification
   */
  private showToast(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'success'): void {
    const toast = document.getElementById('toast');
    if (toast) {
      const toastMsg = document.getElementById('toastMessage');
      if (toastMsg) {
        toastMsg.textContent = message;
      }
      
      toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2`;
      
      if (type === 'success') {
        toast.classList.add('bg-green-500', 'text-white');
      } else if (type === 'error') {
        toast.classList.add('bg-red-500', 'text-white');
      } else if (type === 'warning') {
        toast.classList.add('bg-orange-500', 'text-white');
      } else if (type === 'info') {
        toast.classList.add('bg-blue-500', 'text-white');
      }
      
      toast.classList.remove('hidden');
      
      setTimeout(() => {
        toast.classList.add('hidden');
      }, 3000);
    }
  }

  /**
   * Download CSV template
   */
  downloadTemplate(): void {
    // Template with room type name format only
    const templateContent = `room_no,room_type_name,room_status,freeze_reason
101,Deluxe,AVAILABLE,NONE
102,Deluxe,AVAILABLE,NONE
201,Standard,AVAILABLE,NONE
202,Standard,AVAILABLE,NONE`;

    const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'room_bulk_upload_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    this.showToast('Template downloaded successfully', 'success');
  }

  /**
   * Handle bulk upload
   */
  handleBulkUpload(): void {
    if (!this.selectedFile) {
      this.showToast('Please select a CSV file first', 'error');
      return;
    }

    this.isUploading = true;

    this.roomsService.bulkUploadRooms(this.selectedFile).subscribe({
      next: (response: any) => {
        this.isUploading = false;
        this.uploadResults = response;

        // Show summary toast
        const message = `✅ Added ${response.successfully_created} rooms. ${response.skipped} skipped.`;
        if (response.skipped > 0) {
          this.showToast(message, 'warning');
        } else {
          this.showToast(message, 'success');
        }

        // Reset file input after successful upload
        this.selectedFile = null;
        this.selectedFileName = '';
        if (this.fileInput) {
          this.fileInput.nativeElement.value = '';
        }

        // Auto-close modal after 2 seconds if all successful
        if (response.skipped === 0) {
          setTimeout(() => {
            this.closeBulkUploadModal();
          }, 2000);
        } else {
          // Emit upload complete event so parent can refresh
          this.uploadComplete.emit();
        }
      },
      error: (error: any) => {
        this.isUploading = false;
        const errorMsg = error?.error?.detail || error?.message || 'Error uploading rooms. Please try again.';
        this.showToast(errorMsg, 'error');
      }
    });
  }

  /**
   * Close bulk upload modal
   */
  closeBulkUploadModal(): void {
    // Reset state
    this.selectedFile = null;
    this.selectedFileName = '';
    this.uploadResults = null;
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
    // Emit close event
    this.close.emit();
    // Emit upload complete so parent can refresh
    this.uploadComplete.emit();
  }
}
