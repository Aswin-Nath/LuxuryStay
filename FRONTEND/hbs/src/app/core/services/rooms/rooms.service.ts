import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface RoomType {
  room_type_id: number;
  type_name: string;
  price_per_night: number;
  max_adult_count: number;
  max_child_count: number;
  square_ft: number;
}

export interface Room {
  room_id: number;
  room_no: string;
  room_type_id: number;
  room_type: RoomType;
  room_status: string;
  freeze_reason?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PaginatedRoomsResponse {
  data: Room[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RoomsFilterParams {
  room_id?: number | null;
  room_type_id?: number | null;
  status_filter?: string | null;
  is_freezed?: boolean | null;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

@Injectable({
  providedIn: 'root'
})
export class RoomsService {
  private apiUrl = `${environment.apiUrl}/room-management`;

  constructor(private http: HttpClient) {}

  getRooms(filters?: RoomsFilterParams): Observable<PaginatedRoomsResponse> {
    let params = new HttpParams();
    
    if (filters) {
      if (filters.room_id !== undefined && filters.room_id !== null) {
        params = params.set('room_id', filters.room_id.toString());
      }
      if (filters.room_type_id !== undefined && filters.room_type_id !== null) {
        params = params.set('room_type_id', filters.room_type_id.toString());
      }
      if (filters.status_filter !== undefined && filters.status_filter !== null) {
        params = params.set('status_filter', filters.status_filter);
      }
      if (filters.is_freezed !== undefined && filters.is_freezed !== null) {
        params = params.set('is_freezed', filters.is_freezed.toString());
      }
      if (filters.skip !== undefined) {
        params = params.set('skip', filters.skip.toString());
      }
      if (filters.limit !== undefined) {
        params = params.set('limit', filters.limit.toString());
      }
      if (filters.sort_by !== undefined && filters.sort_by !== null) {
        params = params.set('sort_by', filters.sort_by);
      }
      if (filters.sort_order !== undefined && filters.sort_order !== null) {
        params = params.set('sort_order', filters.sort_order);
      }
    }
    
    return this.http.get<PaginatedRoomsResponse>(`${this.apiUrl}/rooms`, { params });
  }

  getRoom(id: number): Observable<Room> {
    return this.http.get<Room>(`${this.apiUrl}/rooms/${id}`);
  }

  createRoom(room: any): Observable<Room> {
    return this.http.post<Room>(`${this.apiUrl}/rooms`, room);
  }

  updateRoom(id: number, room: any): Observable<Room> {
    return this.http.put<Room>(`${this.apiUrl}/rooms/${id}`, room);
  }

  deleteRoom(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/rooms/${id}`);
  }

  freezeRoom(id: number, reason: string = ''): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/rooms/${id}/freeze`, { freeze_reason: reason });
  }

  unfreezeRoom(id: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/rooms/${id}/freeze`);
  }

  getRoomTypes(withDetails?: boolean): Observable<RoomType[]> {
    return this.http.get<RoomType[]>(`${this.apiUrl}/room-types`);
  }

  getRoomType(id: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/types/${id}`);
  }

  updateRoomType(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/types/${id}`, data);
  }

  // Update amenities for all rooms of a room type
  updateRoomTypeAmenities(roomTypeId: number, amenityIds: number[]): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/types/${roomTypeId}/amenities/update`, { amenity_ids: amenityIds });
  }

  getRoomTypesWithStats(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/room-types/with-stats`);
  }

  getAmenities(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/amenities`);
  }

  // Dashboard KPIs
  getRoomKpis(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/dashboard/kpis`);
  }

  // Amenities with room count
  getAmenitiesWithRoomCount(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/amenities/with-room-count`);
  }

  // Get amenities for a specific room type (NEW ENDPOINT)
  getAmenitiesForRoomType(roomTypeId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/types/${roomTypeId}/amenities`);
  }

  // Get rooms for a specific amenity (deprecated - now returns room types)
  getRoomsForAmenity(amenityId: number): Observable<Room[]> {
    return this.http.get<Room[]>(`${this.apiUrl}/amenities/${amenityId}/rooms`);
  }

  // Map amenity to room (deprecated - use updateRoomTypeAmenities instead)
  mapAmenity(roomId: number, amenityId: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/rooms/${roomId}/amenities/map`, { amenity_ids: [amenityId] });
  }

  // Unmap amenity from room (deprecated - use updateRoomTypeAmenities instead)
  unmapAmenity(roomId: number, amenityId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/rooms/${roomId}/amenities/unmap`, { body: { amenity_ids: [amenityId] } });
  }

  // Delete amenity (will unmap from all rooms)
  deleteAmenity(amenityId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/amenities/${amenityId}`);
  }

  // Update amenity
  updateAmenity(amenityId: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/amenities/${amenityId}`, data);
  }

  // Upload single image for room type
  uploadRoomTypeImage(roomTypeId: number, file: File, caption?: string): Observable<any> {
    const formData = new FormData();
    formData.append('image', file);
    if (caption) {
      formData.append('caption', caption);
    }
    return this.http.post<any>(`${this.apiUrl}/types/${roomTypeId}/images`, formData);
  }

  // Upload multiple images for room type
  uploadRoomTypeImages(roomTypeId: number, files: File[]): Observable<any[]> {
    const uploadObservables = files.map(file => this.uploadRoomTypeImage(roomTypeId, file));
    return new Observable(subscriber => {
      let results: any[] = [];
      let completed = 0;

      if (uploadObservables.length === 0) {
        subscriber.next([]);
        subscriber.complete();
        return;
      }

      uploadObservables.forEach((obs, index) => {
        obs.subscribe({
          next: (result) => {
            results[index] = result;
            completed++;
            if (completed === uploadObservables.length) {
              subscriber.next(results);
              subscriber.complete();
            }
          },
          error: (err) => subscriber.error(err)
        });
      });
    });
  }

  // Get images for room type
  getRoomTypeImages(roomTypeId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/types/${roomTypeId}/images`);
  }

  // Delete room type images
  deleteRoomTypeImages(roomTypeId: number, imageIds: number[]): Observable<any> {
    let params = new HttpParams();
    imageIds.forEach(id => {
      params = params.append('image_ids', id.toString());
    });
    return this.http.delete<any>(`${this.apiUrl}/types/${roomTypeId}/images`, { params });
  }

  // Mark room type image as primary
  markRoomTypeImagePrimary(roomTypeId: number, imageId: number): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/types/${roomTypeId}/images/${imageId}/primary`, {});
  }

  // Create new amenity
  createAmenity(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/amenities`, data);
  }

  // Create new room type
  createRoomType(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/types`, data);
  }

  // Create new room type with images (FormData)
  createRoomTypeWithImages(formData: FormData): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/types`, formData);
  }

  // Bulk upload rooms from CSV
  bulkUploadRooms(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/rooms/bulk-upload`, formData);
  }
}
