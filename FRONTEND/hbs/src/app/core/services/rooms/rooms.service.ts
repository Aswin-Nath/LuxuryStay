import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable } from 'rxjs';

export interface RoomType {
  room_type_id: number;
  room_type_name: string;
  description?: string;
  message?: string;
}

@Injectable({ providedIn: 'root' })
export class RoomsService {
  private readonly baseUrl = `${environment.apiUrl}/room-management`;

  constructor(private http: HttpClient) {}

  getRoomTypes(includeDeleted: boolean = false): Observable<RoomType[]> {
    return this.http.get<RoomType[]>(`${this.baseUrl}/types?include_deleted=${includeDeleted}`);
  }

  getRooms(roomTypeId?: number, isFreezed?: boolean, statusFilter?: string): Observable<any[]> {
    let query = `${this.baseUrl}/rooms`;
    const params: string[] = [];
    if (roomTypeId !== undefined) params.push(`room_type_id=${roomTypeId}`);
    if (typeof isFreezed !== 'undefined') params.push(`is_freezed=${isFreezed}`);
    if (statusFilter) params.push(`status_filter=${encodeURIComponent(statusFilter)}`);
    if (params.length > 0) {
      query += `?${params.join('&')}`;
    }
    return this.http.get<any[]>(query);
  }
}
