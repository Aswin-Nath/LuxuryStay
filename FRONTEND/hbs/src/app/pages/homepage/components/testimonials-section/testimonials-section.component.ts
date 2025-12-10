import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Testimonial {
  name: string;
  role: string;
  message: string;
  rating: number;
}

@Component({
  selector: 'app-testimonials-section',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section id="testimonials" class="scroll-mt-24 py-14 px-6 text-center bg-white">
      <h2 class="cursive-heading text-3xl font-extrabold mb-10 text-center bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
        What Our Guests Say
      </h2>
      <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
        <div *ngFor="let testimonial of testimonials" class="bg-linear-to-br from-yellow-50 to-red-50 p-6 rounded-2xl shadow hover:shadow-xl border border-yellow-200">
          <div class="flex justify-center mb-3">
            <span *ngFor="let i of [1,2,3,4,5]" class="text-yellow-500">★</span>
          </div>
          <p class="text-gray-700 italic mb-4">"{{ testimonial.message }}"</p>
          <p class="font-bold text-gray-800">{{ testimonial.name }}</p>
          <p class="text-sm text-gray-600">{{ testimonial.role }}</p>
        </div>
      </div>
    </section>
  `,
  styles: []
})
export class TestimonialsSectionComponent {
  @Input() testimonials: Testimonial[] = [];
}
