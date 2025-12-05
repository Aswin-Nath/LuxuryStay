import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OfferClaimComponent } from './offer-claim.component';

describe('OfferClaimComponent', () => {
  let component: OfferClaimComponent;
  let fixture: ComponentFixture<OfferClaimComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OfferClaimComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(OfferClaimComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
