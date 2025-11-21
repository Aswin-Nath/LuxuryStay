import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HTTP_INTERCEPTORS, HttpClient } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TokenInterceptor } from './token.interceptor';
import { AuthenticationService } from '../services/authentication/authentication.service';
import { Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { BehaviorSubject, of, throwError } from 'rxjs';

describe('TokenInterceptor', () => {
  let httpMock: HttpTestingController;
  let http: HttpClient;
  let authService: any;
  let router: Router;
  let authState$: BehaviorSubject<boolean>;

  beforeEach(() => {
    authState$ = new BehaviorSubject<boolean>(true);
    authService = {
      authState$: authState$.asObservable(),
      refreshToken: jasmine.createSpy('refreshToken'),
      logout: jasmine.createSpy('logout').and.returnValue(of({})),
      setAuthenticated: jasmine.createSpy('setAuthenticated')
    };

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule.withRoutes([])],
      providers: [
        { provide: AuthenticationService, useValue: authService },
        { provide: HTTP_INTERCEPTORS, useClass: TokenInterceptor, multi: true }
      ]
    });

    httpMock = TestBed.inject(HttpTestingController);
    http = TestBed.inject(HttpClient);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should logout and set unauthenticated on refresh failure', fakeAsync(() => {
    authService.refreshToken.and.returnValue(throwError(() => ({ status: 401 })));
    http.get('/api/protected').subscribe({ next: () => fail('should have failed'), error: () => {} });
    const req1 = httpMock.expectOne('/api/protected');
    req1.flush({}, { status: 401, statusText: 'Unauthorized' });
    tick();
    expect(authService.refreshToken).toHaveBeenCalled();
    expect(authService.setAuthenticated).toHaveBeenCalledWith(false);
    expect(authService.logout).toHaveBeenCalled();
  }));
});
