import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
@Injectable({
  providedIn: 'root',
})
export class SignupService {

  private baseUrl = `${environment.apiUrl}/auth`; // FastAPI default port

  constructor(private http: HttpClient) {}

  signup(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/signup`, payload, { withCredentials: true });
  }
}
