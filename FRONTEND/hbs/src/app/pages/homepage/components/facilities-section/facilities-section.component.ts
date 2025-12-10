import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Facility {
  id: number;
  name: string;
  image: string;
  description: string;
}

@Component({
  selector: 'app-facilities-section',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section id="facilities" class="scroll-mt-24 py-16 px-6 bg-white text-center">
      <h2 class="cursive-heading text-3xl sm:text-4xl font-extrabold mb-12 bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
        Our Facilities
      </h2>
      <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-10 max-w-6xl mx-auto text-left">
        <div *ngFor="let facility of facilities" class="flex flex-col cursor-pointer hover:shadow-lg transition" (click)="onExplore()">
          <img [src]="facility.image" [alt]="facility.name" class="h-44 w-full object-cover rounded-lg shadow">
          <h3 class="mt-4 font-serif text-lg font-bold uppercase text-yellow-700">{{ facility.name }}</h3>
          <p class="text-gray-600 text-sm mt-2 grow">{{ facility.description }}</p>
          <div class="mt-4">
            <a href="javascript:void(0)" class="text-yellow-600 font-semibold hover:text-yellow-700">Explore →</a>
          </div>
        </div>
      </div>
    </section>
  `,
  styles: []
})
export class FacilitiesSectionComponent {
  @Input() facilities: Facility[] = [];
  @Output() explore = new EventEmitter<void>();

  onExplore(): void {
    this.explore.emit();
  }
}
