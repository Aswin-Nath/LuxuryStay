import { Component, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-about-section',
  standalone: true,
  template: `
    <section class="scroll-mt-24 py-16 px-6 max-w-6xl mx-auto grid md:grid-cols-2 gap-10 items-center">
      <div>
        <h2 class="text-3xl sm:text-4xl font-bold mb-8 bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
          Sophistication & Luxury of LuxuryStay
        </h2>
        <p class="text-gray-700 text-base sm:text-lg mb-6">
          One of the finest luxury hotels in the city, LuxuryStay is designed to reflect elegance and comfort. 
          Our centrally located 5-star hotel offers the best in hospitality for both business and leisure travelers. 
          With unmatched facilities, intuitive service, and refined interiors, we create memories that last forever.
        </p>
        <button (click)="onLearnMore()"
          class="inline-block px-6 py-3 bg-linear-to-r from-yellow-500 to-red-500 text-white font-semibold rounded-lg shadow-md hover:opacity-90 hover:scale-105 transition">
          Know more about us →
        </button>
      </div>
      <div>
        <img src="https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1000&q=80" 
          alt="Hotel Image" class="rounded-2xl shadow-lg">
      </div>
    </section>
  `,
  styles: []
})
export class AboutSectionComponent {
  @Output() learnMore = new EventEmitter<void>();

  onLearnMore(): void {
    this.learnMore.emit();
  }
}
