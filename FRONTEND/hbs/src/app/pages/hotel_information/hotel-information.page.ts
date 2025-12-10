import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-hotel-information',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent, FooterComponent],
  templateUrl: './hotel-information.page.html',
  styleUrl: './hotel-information.page.css'
})
export class HotelInformationComponent implements OnInit {
  constructor() {}

  ngOnInit(): void {}
}
