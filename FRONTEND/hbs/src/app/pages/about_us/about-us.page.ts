import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-about-us',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent, FooterComponent],
  templateUrl: './about-us.page.html',
  styleUrl: './about-us.page.css'
})
export class AboutUsComponent implements OnInit {
  teamMembers = [
    {
      name: 'John Smith',
      position: 'General Manager',
      image: 'https://via.placeholder.com/150?text=John'
    },
    {
      name: 'Sarah Johnson',
      position: 'Head Chef',
      image: 'https://via.placeholder.com/150?text=Sarah'
    },
    {
      name: 'Michael Chen',
      position: 'Concierge Manager',
      image: 'https://via.placeholder.com/150?text=Michael'
    }
  ];

  faqs = [
    {
      question: 'What is the best time to visit?',
      answer: 'LuxuryStay is a year-round destination. However, spring and fall offer the most pleasant weather.'
    },
    {
      question: 'Do you offer group discounts?',
      answer: 'Yes! Groups of 10 or more can receive special rates. Contact our sales team for details.'
    },
    {
      question: 'Are pets allowed?',
      answer: 'Pets are allowed in select rooms with an additional fee of $50 per night.'
    }
  ];

  faqExpandedIndex: number | null = null;

  constructor() {}

  ngOnInit(): void {}

  toggleFaq(index: number): void {
    this.faqExpandedIndex = this.faqExpandedIndex === index ? null : index;
  }
}
