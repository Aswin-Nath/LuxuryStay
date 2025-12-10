import { Component, OnInit } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './footer.component.html',
  styleUrl: './footer.component.css'
})
export class FooterComponent implements OnInit {
  currentYear = new Date().getFullYear();
  email: string = '';
  subscriptionMessage: string = '';

  constructor(private router: Router) {}

  ngOnInit(): void {}

  subscribe(): void {
    if (this.email && this.email.includes('@')) {
      this.subscriptionMessage = 'Thank you for subscribing!';
      this.email = '';
      setTimeout(() => {
        this.subscriptionMessage = '';
      }, 3000);
    } else {
      this.subscriptionMessage = 'Please enter a valid email';
    }
  }

  getDirections(): void {
    window.open('https://www.google.com/maps/search/123+Luxury+Street+New+York+USA', '_blank');
  }

  navigateTo(path: string): void {
    this.router.navigate([path]);
  }
}
