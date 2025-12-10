import { Component, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-hero-section',
  standalone: true,
  template: `
    <section class="relative bg-cover bg-center h-[60vh] sm:h-[70vh]" style="background-image:url('https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80');">
      <div class="absolute inset-0 bg-opacity-60 flex items-center justify-center">
        <div class="text-center text-white max-w-lg sm:max-w-2xl px-4">
          <h1 class="cursive-heading text-4xl sm:text-5xl font-bold mb-6">LuxuryStay</h1>
          <p class="text-lg sm:text-xl mb-8 text-gray-200">Experience elegance, comfort, and world-class hospitality</p>
          <button (click)="onBookNow()"
            class="px-8 py-3 bg-linear-to-r from-yellow-500 to-red-500 text-white font-semibold rounded-lg shadow-lg hover:opacity-90 transition">
            Book Your Stay
          </button>
        </div>
      </div>
    </section>
  `,
  styles: []
})
export class HeroSectionComponent {
  @Output() bookNow = new EventEmitter<void>();

  onBookNow(): void {
    this.bookNow.emit();
  }
}
