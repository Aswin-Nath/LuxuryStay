import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EditRoom } from './edit-room';

describe('EditRoom', () => {
  let component: EditRoom;
  let fixture: ComponentFixture<EditRoom>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditRoom]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EditRoom);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
