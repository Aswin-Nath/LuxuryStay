import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private backendUrl: string;

  constructor() {
    this.backendUrl = this.getBackendUrl();
  }

  private getBackendUrl(): string {
    if (typeof window !== 'undefined' && (window as any).__env__) {
      return (window as any).__env__.BACKEND_URL || 'http://localhost:8000';
    }
    return 'http://localhost:8000';
  }

  get apiUrl(): string {
    return this.backendUrl;
  }

  getFullUrl(endpoint: string): string {
    const path = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${this.backendUrl}/${path}`;
  }
}
