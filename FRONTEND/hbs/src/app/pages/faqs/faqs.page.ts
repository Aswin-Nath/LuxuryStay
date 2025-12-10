import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-faqs',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent, FooterComponent],
  templateUrl: './faqs.page.html',
  styleUrl: './faqs.page.css'
})
export class FaqsComponent implements OnInit {
  activeTab: 'rooms' | 'amenities' = 'rooms';
  expandedIndex: number | null = null;

  roomsFaqs = [
    {
      question: 'What types of rooms are available?',
      answer: 'We offer Deluxe Rooms, Executive Suites, and Presidential Suites, each with premium amenities and views.'
    },
    {
      question: 'What is the check-in and check-out time?',
      answer: 'Standard check-in is at 2:00 PM and check-out is at 12:00 PM. Early check-in and late check-out may be arranged based on availability.'
    },
    {
      question: 'Do rooms have air conditioning?',
      answer: 'Yes, all rooms are equipped with individual climate control systems for your comfort.'
    },
    {
      question: 'Is Wi-Fi available in rooms?',
      answer: 'Yes, complimentary high-speed Wi-Fi is available in all rooms and throughout the hotel.'
    },
    {
      question: 'Can I request a specific room type?',
      answer: 'Absolutely! We accommodate room preference requests based on availability at no extra cost.'
    }
  ];

  amenitiesFaqs = [
    {
      question: 'What amenities does the spa offer?',
      answer: 'Our spa provides massages, facials, body treatments, and wellness therapies conducted by certified therapists.'
    },
    {
      question: 'Are there any dining options in the hotel?',
      answer: 'Yes, we have 5 fine dining restaurants, a café, and 24/7 room service with an extensive menu.'
    },
    {
      question: 'Is there a fitness center?',
      answer: 'Yes, our state-of-the-art fitness center is open 24/7 with modern equipment and personal training available.'
    },
    {
      question: 'Can I use the pool if I\'m not staying overnight?',
      answer: 'Day passes are available for non-residents to enjoy our facilities. Contact concierge for details.'
    },
    {
      question: 'Do you have conference facilities?',
      answer: 'Yes, we offer fully equipped conference halls for meetings, seminars, and events with catering services.'
    },
    {
      question: 'Is there valet parking?',
      answer: 'Yes, complimentary valet parking is available for all guests at our hotel.'
    }
  ];

  constructor() {}

  ngOnInit(): void {}

  switchTab(tab: 'rooms' | 'amenities'): void {
    this.activeTab = tab;
    this.expandedIndex = null;
  }

  toggleFaq(index: number): void {
    this.expandedIndex = this.expandedIndex === index ? null : index;
  }
}
