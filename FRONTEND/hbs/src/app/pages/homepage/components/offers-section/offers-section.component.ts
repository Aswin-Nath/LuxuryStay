import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Offer {
  id: number;
  name: string;
  image: string;
  description: string;
  discount: string;
}

@Component({
  selector: 'app-offers-section',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section id="offers" class="scroll-mt-24 py-16 px-6 bg-white text-center">
      <h2 class="cursive-heading text-3xl sm:text-4xl font-bold mb-12 bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
        Special Offers
      </h2>
      <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-10 max-w-6xl mx-auto text-left">
        <div *ngFor="let offer of offers" class="flex flex-col">
          <div class="relative">
            <img [src]="offer.image" [alt]="offer.name" class="h-56 w-full object-cover rounded-lg shadow">
            <div class="absolute top-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg font-bold">
              {{ offer.discount }} OFF
            </div>
          </div>
          <h3 class="mt-4 font-serif text-lg sm:text-xl font-bold uppercase">{{ offer.name }}</h3>
          <p class="text-gray-600 text-sm mt-2 grow">{{ offer.description }}</p>
          <button (click)="onLearnMore()" class="mt-4 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition">
            Learn More
          </button>
        </div>
      </div>
    </section>
  `,
  styles: []
})
export class OffersSectionComponent {
  @Input() offers: Offer[] = [];
  @Output() learnMore = new EventEmitter<void>();

  onLearnMore(): void {
    this.learnMore.emit();
  }
}
