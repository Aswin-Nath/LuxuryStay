import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
export interface ProfileResponse {
  user_id: number;
  full_name: string;
  email: string;
  phone_number?: string;
  role_id: number;
  profile_image_url?: string;
  dob?: string;
  gender?: string;
}

export interface ProfileUpdate {
  full_name?: string;
  phone_number?: string;
  dob?: string;
  gender?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

@Injectable({
  providedIn: 'root',
})
export class ProfileService {
  private baseUrl = `${environment.apiUrl}/profile`;

  constructor(private http: HttpClient) {}

  /**
   * Get authenticated user's profile
   */
  getProfile(): Observable<ProfileResponse> {
    return this.http.get<ProfileResponse>(`${this.baseUrl}/`);
  }

  /**
   * Update user's profile information
   */
  updateProfile(profileData: ProfileUpdate): Observable<ProfileResponse> {
    return this.http.put<ProfileResponse>(`${this.baseUrl}/`, profileData);
  }

  /**
   * Upload profile image
   */
  uploadProfileImage(file: File): Observable<ProfileResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ProfileResponse>(`${this.baseUrl}/image`, formData);
  }

  /**
   * Change user password
   */
  changePassword(data: ChangePasswordRequest): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/password`, data);
  }
}