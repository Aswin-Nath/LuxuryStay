import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-destinations',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent, FooterComponent],
  templateUrl: './destinations.page.html',
  styleUrl: './destinations.page.css'
})
export class DestinationsComponent implements OnInit {
  destinations = [
    {
      name: 'New York',
      image: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&w=600&q=80',
      description: 'Experience the vibrant energy of NYC'
    },
    {
      name: 'Maldives',
      image: 'https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=600&q=80',
      description: 'Tropical paradise with pristine beaches'
    },
    {
      name: 'Paris',
      image: 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=600&q=80',
      description: 'City of love and romantic getaways'
    }
  ];

  constructor() {}

  ngOnInit(): void {}
}
