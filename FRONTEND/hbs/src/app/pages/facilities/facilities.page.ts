import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-facilities',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent, FooterComponent],
  templateUrl: './facilities.page.html',
  styleUrl: './facilities.page.css'
})
export class FacilitiesComponent implements OnInit {
  facilities = [
    {
      name: 'Wellness Spa',
      image: '/assets/images/spa.png',
      description: 'Rejuvenating spa treatments and wellness therapies.'
    },
    {
      name: 'Infinity Pool',
      image: '/assets/images/pool.jpg',
      description: 'Olympic-size pool with stunning sunset views.'
    },
    {
      name: 'Fine Dining',
      image: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=600&q=80',
      description: 'Award-winning restaurants and 24-hour room service.'
    },
    {
      name: 'Fitness Center',
      image: '/assets/images/gym.png',
      description: 'State-of-the-art gym equipment and personal trainers.'
    },
    {
      name: 'Conference Hall',
      image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=600&q=80',
      description: 'Professional event spaces for meetings and conferences.'
    },
    {
      name: 'Luxury Lounge',
      image: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=600&q=80',
      description: 'Exclusive lounge with premium amenities and services.'
    }
  ];

  constructor() {}

  ngOnInit(): void {}
}
