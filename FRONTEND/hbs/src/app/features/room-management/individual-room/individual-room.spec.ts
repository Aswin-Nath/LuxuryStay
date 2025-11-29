import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IndividualRoomComponent } from './individual-room';

describe('IndividualRoom', () => {
  let component: IndividualRoomComponent;
  let fixture: ComponentFixture<IndividualRoomComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IndividualRoomComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(IndividualRoomComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
