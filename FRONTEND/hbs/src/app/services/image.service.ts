import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface ImageData {
  image_id: number;
  entity_type: string;
  entity_id: number;
  image_url: string;
  caption?: string;
  is_primary: boolean;
  created_at?: string;
}

@Injectable({
  providedIn: 'root',
})
export class ImageService {
  private apiUrl = `${environment.apiUrl}/images`;

  constructor(private http: HttpClient) {}

  /**
   * Get images for a specific entity (room_type, offer, amenity, etc.)
   * @param entityType Type of entity (room_type, offer, amenity, review, issue)
   * @param entityId ID of the entity
   * @returns Observable of ImageData array
   */
  getImagesForEntity(entityType: string, entityId: number): Observable<ImageData[]> {
    let params = new HttpParams()
      .set('entity_type', entityType)
      .set('entity_id', entityId.toString());

    return this.http.get<ImageData[]>(`${this.apiUrl}`, { params }).pipe(
      catchError((error) => {
        console.error(`Failed to load images for ${entityType}:${entityId}`, error);
        return of([]); // Return empty array on error
      })
    );
  }

  /**
   * Get all images for a room type
   * @param roomTypeId Room type ID
   * @returns Observable of ImageData array
   */
  getRoomTypeImages(roomTypeId: number): Observable<ImageData[]> {
    return this.getImagesForEntity('room_type', roomTypeId);
  }

  /**
   * Get all images for an offer
   * @param offerId Offer ID
   * @returns Observable of ImageData array
   */
  getOfferImages(offerId: number): Observable<ImageData[]> {
    return this.http
      .get<ImageData[]>(`${this.apiUrl}/offers/${offerId}/images`)
      .pipe(
        catchError((error) => {
          console.error(`Failed to load offer images for offer:${offerId}`, error);
          return of([]); // Return empty array on error
        })
      );
  }

  /**
   * Get all images for amenities
   * @param amenityId Amenity ID
   * @returns Observable of ImageData array
   */
  getAmenityImages(amenityId: number): Observable<ImageData[]> {
    return this.getImagesForEntity('amenity', amenityId);
  }

  /**
   * Get primary image for an entity
   * @param entityType Type of entity
   * @param entityId ID of the entity
   * @returns Observable of primary ImageData or null if not found
   */
  getPrimaryImageForEntity(entityType: string, entityId: number): Observable<ImageData | null> {
    return this.getImagesForEntity(entityType, entityId).pipe(
      map((images) => {
        const primaryImage = images.find((img) => img.is_primary);
        return primaryImage || images[0] || null;
      })
    );
  }

  /**
   * Get primary image URL for a room type
   * @param roomTypeId Room type ID
   * @returns Observable of image URL string
   */
  getPrimaryRoomTypeImageUrl(roomTypeId: number): Observable<string> {
    return this.getPrimaryImageForEntity('room_type', roomTypeId).pipe(
      map((image) => image?.image_url || '')
    );
  }

  /**
   * Get primary image URL for an offer
   * @param offerId Offer ID
   * @returns Observable of image URL string
   */
  getPrimaryOfferImageUrl(offerId: number): Observable<string> {
    return this.getOfferImages(offerId).pipe(
      map((images) => {
        const primaryImage = images.find((img) => img.is_primary);
        return (primaryImage || images[0])?.image_url || '';
      })
    );
  }
}
