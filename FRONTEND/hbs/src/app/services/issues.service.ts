import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
export interface IssueCreate {
  booking_id: number;
  room_ids?: number[];
  title: string;
  description: string;
}

export interface Issue {
  issue_id: number;
  booking_id: number;
  room_ids?: number[];
  user_id: number;
  title: string;
  description: string;
  status: string;
  reported_at: string;
  resolved_at?: string;
  last_updated: string;
  is_deleted: boolean;
  resolved_by?: number;
  images?: Image[];
  created_at?: string;
}

export interface IssueResponse {
  issue_id: number;
  booking_id: number;
  room_ids?: number[];
  user_id: number;
  title: string;
  description: string;
  status: string;
  reported_at: string;
  resolved_at?: string;
  last_updated: string;
  is_deleted: boolean;
  resolved_by?: number;
  images?: Image[];
}

export interface Image {
  image_id: number;
  entity_type: string;
  entity_id: number;
  image_url: string;
  caption?: string;
  is_primary: boolean;
  uploaded_by?: number;
  created_at: string;
  is_deleted: boolean;
}

export interface ChatMessage {
  chat_id: number;
  issue_id: number;
  sender_id: number;
  message: string;
  sent_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class IssuesService {
  private apiUrl = `${environment.apiUrl}/issues`;

  constructor(private http: HttpClient) {}

  // ========== CUSTOMER ENDPOINTS ==========

  /**
   * Create a new issue/complaint
   * @param payload Issue data (title, description, booking_id, room_ids)
   * @returns Observable of created issue
   */
  createIssue(payload: IssueCreate): Observable<IssueResponse> {
    const formData = new FormData();
    formData.append('title', payload.title);
    formData.append('description', payload.description);
    formData.append('booking_id', payload.booking_id.toString());
    if (payload.room_ids && payload.room_ids.length > 0) {
      formData.append('room_ids', JSON.stringify(payload.room_ids));
    }

    return this.http.post<IssueResponse>(`${this.apiUrl}/`, formData);
  }

  /**
   * Get paginated list of customer's own issues
   * @param limit Page size
   * @param offset Pagination offset
   * @returns Observable of issues list
   */
  getMyIssues(
    limit: number = 50,
    offset: number = 0,
    status?: string,
    room_id?: string,
    search?: string,
    date_from?: string,
    date_to?: string,
    sort_by: string = 'recent'
  ): Observable<IssueResponse[]> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString())
      .set('sort_by', sort_by);
    
    if (status) params = params.set('status', status);
    if (room_id) params = params.set('room_id', room_id);
    if (search) params = params.set('search', search);
    if (date_from) params = params.set('date_from', date_from);
    if (date_to) params = params.set('date_to', date_to);
    
    return this.http.get<IssueResponse[]>(`${this.apiUrl}/customer/`, { params });
  }

  /**
   * Get single issue details (customer can only view own issues)
   * @param issueId Issue ID to fetch
   * @returns Observable of issue with full details
   */
  getMyIssueDetails(issueId: number): Observable<IssueResponse> {
    return this.http.get<IssueResponse>(`${this.apiUrl}/customer/${issueId}`);
  }

  /**
   * Update issue title and/or description (owner only)
   * @param issueId Issue ID to update
   * @param title New title (optional)
   * @param description New description (optional)
   * @returns Observable of updated issue
   */
  updateIssue(issueId: number, title?: string, description?: string): Observable<IssueResponse> {
    const formData = new FormData();
    if (title) {
      formData.append('title', title);
    }
    if (description) {
      formData.append('description', description);
    }

    return this.http.put<IssueResponse>(`${this.apiUrl}/${issueId}`, formData);
  }

  /**
   * Get chat messages for customer's issue
   * @param issueId Issue ID
   * @returns Observable of chat messages
   */
  getIssueChats(issueId: number): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.apiUrl}/customer/${issueId}/chat`);
  }

  /**
   * Post a chat message to customer's issue
   * @param issueId Issue ID
   * @param message Message text
   * @returns Observable of created chat message
   */
  postChat(issueId: number, message: string): Observable<ChatMessage> {
    const formData = new FormData();
    formData.append('message', message);

    return this.http.post<ChatMessage>(`${this.apiUrl}/customer/${issueId}/chat`, formData);
  }

  /**
   * Get all images for an issue
   * @param issueId Issue ID
   * @returns Observable of image records for the issue
   */
  getIssueImages(issueId: number): Observable<Image[]> {
    return this.http.get<Image[]>(`${this.apiUrl}/${issueId}/images`);
  }

  /**
   * Upload images to an issue
   * @param issueId Issue ID
   * @param files Image files to upload
   * @returns Observable of created image records
   */
  uploadIssueImages(issueId: number, files: File[]): Observable<Image[]> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    return this.http.post<Image[]>(`${this.apiUrl}/${issueId}/images`, formData);
  }

  /**
   * Delete an image from an issue
   * @param issueId Issue ID
   * @param imageId Image ID to delete
   * @returns Observable of deletion response
   */
  deleteIssueImage(issueId: number, imageId: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${issueId}/images/${imageId}`);
  }

  // ========== ADMIN ENDPOINTS ==========

  /**
   * Get paginated list of all issues (admin only) with filtering and sorting
   * @param limit Page size
   * @param offset Pagination offset
   * @param status Filter by status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
   * @param room_id Filter by room ID
   * @param search Search in title and description
   * @param date_from Filter from date (YYYY-MM-DD)
   * @param date_to Filter to date (YYYY-MM-DD)
   * @param sort_by Sort by: recent, oldest, title
   * @returns Observable of filtered issues list
   */
  getAllIssuesAdmin(
    limit: number = 50,
    offset: number = 0,
    status?: string,
    room_id?: string,
    search?: string,
    date_from?: string,
    date_to?: string,
    sort_by: string = 'recent'
  ): Observable<IssueResponse[]> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString())
      .set('sort_by', sort_by);
    
    if (status) params = params.set('status', status);
    if (room_id) params = params.set('room_id', room_id);
    if (search) params = params.set('search', search);
    if (date_from) params = params.set('date_from', date_from);
    if (date_to) params = params.set('date_to', date_to);
    
    return this.http.get<IssueResponse[]>(`${this.apiUrl}/admin/`, { params });
  }

  /**
   * Get single issue details (admin view)
   * @param issueId Issue ID to fetch
   * @returns Observable of issue with full details
   */
  getIssueDetailsAdmin(issueId: number): Observable<IssueResponse> {
    return this.http.get<IssueResponse>(`${this.apiUrl}/admin/${issueId}`);
  }

  /**
   * Update issue status (admin only)
   * @param issueId Issue ID to update
   * @param status New status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
   * @returns Observable of updated issue
   */
  updateIssueStatus(issueId: number, status: string): Observable<IssueResponse> {
    const formData = new FormData();
    formData.append('status', status);

    return this.http.put<IssueResponse>(`${this.apiUrl}/admin/${issueId}/status`, formData);
  }

  /**
   * Get chat messages for an issue (admin view)
   * @param issueId Issue ID
   * @returns Observable of chat messages
   */
  getIssueChatsAdmin(issueId: number): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(`${this.apiUrl}/admin/${issueId}/chat`);
  }

  /**
   * Post a chat message to an issue (admin only)
   * @param issueId Issue ID
   * @param message Message text
   * @returns Observable of created chat message
   */
  postChatAdmin(issueId: number, message: string): Observable<ChatMessage> {
    const formData = new FormData();
    formData.append('message', message);

    return this.http.post<ChatMessage>(`${this.apiUrl}/admin/${issueId}/chat`, formData);
  }
}
