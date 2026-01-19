import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
// ============================================================================
// 📋 REFUND MODELS & INTERFACES
// ============================================================================

export interface Refund {
  refund_id: number;
  booking_id: number;
  user_id: number;
  type: string; // 'CANCELLATION', 'PARTIAL_CANCEL', 'SERVICE_ISSUE', etc.
  status: string; // 'INITIATED', 'PROCESSING', 'COMPLETED', 'REJECTED', etc.
  refund_amount: number;
  initiated_at: string; // ISO datetime
  processed_at: string | null;
  completed_at: string | null;
  remarks: string | null;
  is_deleted: boolean;
  transaction_method_id: number | null;
  transaction_number: string | null;
  full_cancellation: boolean;
}

export interface RefundFilters {
  booking_id?: number | null;
  user_id?: number | null;
  status?: string | null;
  type?: string | null;
  from_date?: string | null;
  to_date?: string | null;
  limit?: number;
  offset?: number;
}

export interface RefundTransactionUpdate {
  status?: string;
  transaction_method_id?: number | null;
  transaction_number?: string | null;
}

// ============================================================================
// 🔹 REFUND SERVICE
// ============================================================================

@Injectable({
  providedIn: 'root'
})
export class RefundsService {
  private baseUrl = `${environment.apiUrl}/refunds`;

  constructor(private http: HttpClient) {}

  // ========== CUSTOMER ENDPOINTS ==========

  /**
   * Get customer's refunds with pagination
   * @param filters Refund filters and pagination params
   * @returns Observable<Refund[]>
   */
  getCustomerRefunds(filters: Partial<RefundFilters> = {}): Observable<Refund[]> {
    let params = new HttpParams();
    
    if (filters.limit !== undefined) params = params.set('limit', filters.limit.toString());
    if (filters.offset !== undefined) params = params.set('offset', filters.offset.toString());
    if (filters.booking_id) params = params.set('booking_id', filters.booking_id.toString());
    if (filters.status) params = params.set('status', filters.status);
    if (filters.type) params = params.set('type', filters.type);
    if (filters.from_date) params = params.set('from_date', filters.from_date);
    if (filters.to_date) params = params.set('to_date', filters.to_date);

    return this.http.get<Refund[]>(
      `${this.baseUrl}/customer/`,
      { params }
    );
  }

  /**
   * Get single customer refund detail
   * @param refundId Refund ID
   * @returns Observable<Refund>
   */
  getCustomerRefundDetail(refundId: number): Observable<Refund> {
    return this.http.get<Refund>(`${this.baseUrl}/customer/${refundId}`);
  }

  // ========== ADMIN ENDPOINTS ==========

  /**
   * Get all refunds (admin) with pagination and filters
   * @param filters Refund filters and pagination params
   * @returns Observable<Refund[]>
   */
  getAdminRefunds(filters: Partial<RefundFilters> = {}): Observable<Refund[]> {
    let params = new HttpParams();
    
    if (filters.limit !== undefined) params = params.set('limit', filters.limit.toString());
    if (filters.offset !== undefined) params = params.set('offset', filters.offset.toString());
    if (filters.booking_id) params = params.set('booking_id', filters.booking_id.toString());
    if (filters.user_id) params = params.set('user_id', filters.user_id.toString());
    if (filters.status) params = params.set('status', filters.status);
    if (filters.type) params = params.set('type', filters.type);
    if (filters.from_date) params = params.set('from_date', filters.from_date);
    if (filters.to_date) params = params.set('to_date', filters.to_date);

    return this.http.get<Refund[]>(
      `${this.baseUrl}/admin/`,
      { params }
    );
  }

  /**
   * Get single refund detail (admin)
   * @param refundId Refund ID
   * @returns Observable<Refund>
   */
  getAdminRefundDetail(refundId: number): Observable<Refund> {
    return this.http.get<Refund>(`${this.baseUrl}/admin/${refundId}`);
  }

  /**
   * Update refund transaction (admin only)
   * @param refundId Refund ID
   * @param payload Transaction update payload
   * @returns Observable<Refund>
   */
  updateRefundTransaction(refundId: number, payload: RefundTransactionUpdate): Observable<Refund> {
    return this.http.put<Refund>(`${this.baseUrl}/${refundId}`, payload);
  }

  // ========== UTILITY METHODS ==========

  /**
   * Format refund status for display
   */
  getStatusColor(status: string): string {
    const statusColorMap: { [key: string]: string } = {
      'INITIATED': 'bg-blue-100 text-blue-800',
      'PROCESSING': 'bg-yellow-100 text-yellow-800',
      'COMPLETED': 'bg-green-100 text-green-800',
      'REJECTED': 'bg-red-100 text-red-800',
      'CANCELLED': 'bg-gray-100 text-gray-800',
    };
    return statusColorMap[status] || 'bg-gray-100 text-gray-800';
  }

  /**
   * Get status badge icon
   */
  getStatusIcon(status: string): string {
    const statusIconMap: { [key: string]: string } = {
      'INITIATED': 'hourglass_empty',
      'PROCESSING': 'schedule',
      'COMPLETED': 'check_circle',
      'REJECTED': 'cancel',
      'CANCELLED': 'block',
    };
    return statusIconMap[status] || 'help';
  }

  /**
   * Format refund type for display
   */
  getTypeLabel(type: string): string {
    const typeMap: { [key: string]: string } = {
      'CANCELLATION': 'Full Cancellation',
      'PARTIAL_CANCEL': 'Partial Cancellation',
      'SERVICE_ISSUE': 'Service Issue',
      'OVERBILLING': 'Overbilling',
      'NO_SHOW': 'No Show',
      'OTHER': 'Other',
    };
    return typeMap[type] || type;
  }

  /**
   * Format currency
   */
  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(amount);
  }

  /**
   * Format date
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  /**
   * Format full datetime
   */
  formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
