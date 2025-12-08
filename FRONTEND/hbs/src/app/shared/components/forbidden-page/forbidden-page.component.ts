import { Component } from '@angular/core';
import { Location } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-forbidden-page',
  templateUrl: './forbidden-page.component.html',
  standalone:true,
  imports:[RouterLink],
  styleUrl: './forbidden-page.component.css'
})
export class ForbiddenPageComponent {

  constructor(private location: Location) {}

  goBack() {
    this.location.back();
  }
}
