import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NavbarComponent } from './navbar.component';
import { AuthenticationService } from '../../services/authentication/authentication.service';
import { BehaviorSubject, of } from 'rxjs';
import { By } from '@angular/platform-browser';

describe('NavbarComponent', () => {
  let component: NavbarComponent;
  let fixture: any;
  let authState$: BehaviorSubject<boolean>;
  let mockAuthService: any;

  beforeEach(async () => {
    authState$ = new BehaviorSubject<boolean>(false);
    mockAuthService = {
      authState$: authState$.asObservable(),
      logout: jasmine.createSpy('logout').and.returnValue(of({}))
    };

    await TestBed.configureTestingModule({
      imports: [RouterTestingModule],
      providers: [{ provide: AuthenticationService, useValue: mockAuthService }],
      declarations: [NavbarComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(NavbarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('shows Login and Signup when logged out', () => {
    const el = fixture.debugElement.nativeElement;
    expect(el.textContent).toContain('Login');
    expect(el.textContent).toContain('Sign up');
  });

  it('shows Logout when logged in', fakeAsync(() => {
    authState$.next(true);
    fixture.detectChanges();
    tick();
    const el = fixture.debugElement.nativeElement;
    expect(el.textContent).toContain('Logout');
  }));

  it('calls authService.logout on pressing logout', fakeAsync(() => {
    authState$.next(true);
    fixture.detectChanges();
    tick();
    const button = fixture.debugElement.query(By.css('button'));
    button.nativeElement.click();
    expect(mockAuthService.logout).toHaveBeenCalled();
  }));
});
