import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
interface ImageUrl{
  image_url:string;
} 
export interface Review {
  review_id: number;
  booking_id: number;
  user_id: number;
  room_type_id?: number;
  rating: number;
  comment: string;
  created_at: string;
  updated_at: string;
  admin_response?: string;
  admin_id?: number;
  responded_at?: string;
  images?: ImageUrl[];
  admin_response_images?: ImageUrl[];
  user?: {
    user_id: number;
    full_name: string;
    profile_image_url?: string;
  };
  admin?: {
    user_id: number;
    full_name: string;
    profile_image_url?: string;
  };
}

export interface ReviewCreate {
  booking_id: number;
  room_type_id?: number;
  rating: number;
  comment?: string;
}

export interface AdminResponseCreate {
  admin_response: string;
}

@Injectable({
  providedIn: 'root'
})
export class ReviewsService {
  private apiUrl = `${environment.apiUrl}/reviews`;
  
  constructor(private http: HttpClient) {}

  // Get reviews for a specific booking
  getReviewsByBooking(bookingId: number): Observable<Review[]> {
    return this.http.get<Review[]>(`${this.apiUrl}?booking_id=${bookingId}`);
  }

  // Get reviews for a room type
  getReviewsByRoomType(roomTypeId: number): Observable<Review[]> {
    return this.http.get<Review[]>(`${this.apiUrl}?room_type_id=${roomTypeId}`);
  }

  // Get single review with details
  getReview(reviewId: number): Observable<Review> {
    return this.http.get<Review>(`${this.apiUrl}/${reviewId}`);
  }

  // Create a new review
  createReview(payload: ReviewCreate): Observable<Review> {
    console.log(this.apiUrl);
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        formData.append(key, value.toString());
      }
    });
    return this.http.post<Review>(this.apiUrl, formData);
  }

  // Update existing review (user can only update their own)
  updateReview(reviewId: number, rating: number, comment: string): Observable<Review> {
    const formData = new FormData();
    formData.append('rating', rating.toString());
    if (comment) {
      formData.append('comment', comment);
    }
    return this.http.put<Review>(`${this.apiUrl}/${reviewId}`, formData);
  }

  // Admin posts response to review (one response per review)
  addAdminResponse(reviewId: number, adminResponse: string): Observable<Review> {
    const payload ={'admin_response':adminResponse};
    return this.http.put<Review>(`${this.apiUrl}/${reviewId}/respond`, payload);
  }

  // Upload images for review (user review images)
  uploadReviewImages(reviewId: number, files: File[]): Observable<any> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    return this.http.post(`${this.apiUrl}/${reviewId}/images`, formData);
  }

  // Upload images for admin response
  uploadAdminResponseImages(reviewId: number, files: File[]): Observable<any> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    return this.http.post(`${this.apiUrl}/${reviewId}/admin-images`, formData);
  }

  // Delete review image
  deleteReviewImage(reviewId: number, imageId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${reviewId}/images/${imageId}`);
  }

  // Delete admin response image
  deleteAdminResponseImage(reviewId: number, imageId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${reviewId}/admin-images/${imageId}`);
  }

  // Delete entire review
  deleteReview(reviewId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${reviewId}`);
  }
}
