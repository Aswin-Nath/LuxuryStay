import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
@Injectable({
  providedIn: 'root',
})
export class SignupService {

  private baseUrl = 'http://localhost:8000/auth'; // FastAPI default port

  constructor(private http: HttpClient) {}

  signup(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/signup`, payload, { withCredentials: true });
  }
}
