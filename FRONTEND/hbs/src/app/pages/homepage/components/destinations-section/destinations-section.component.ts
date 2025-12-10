import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
interface Destination {
  name: string;
  image: string;
  description: string;
}

@Component({
  selector: 'app-destinations-section',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section id="destinations" class="scroll-mt-24 py-16 px-6 bg-white">
      <h2 class="cursive-heading text-3xl sm:text-4xl font-extrabold mb-12 text-center bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
        Popular Destinations
      </h2>
      <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-12 max-w-6xl mx-auto text-left">
        <div *ngFor="let dest of destinations" class="group cursor-pointer hover:scale-105 transition-transform duration-300" (click)="onExplore(dest.name)">
          <div class="relative overflow-hidden rounded-lg">
            <img [src]="dest.image" [alt]="dest.name" class="h-64 w-full object-cover group-hover:scale-110 transition-transform duration-300">
            <div class="absolute inset-0 bg-opacity-40 group-hover:bg-opacity-50 transition flex items-end p-6">
              <div class="text-white">
                <h3 class="text-2xl font-bold">{{ dest.name }}</h3>
                <p class="text-sm text-gray-200">{{ dest.description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="text-center mt-10">
        <button (click)="onViewAll()"
          class="px-6 py-3 bg-yellow-500 text-white font-semibold rounded-lg hover:bg-yellow-600 transition">
          View All Destinations
        </button>
      </div>
    </section>
  `,
  styles: []
})
export class DestinationsSectionComponent {
  @Input() destinations: Destination[] = [];
  @Output() viewAll = new EventEmitter<void>();
  @Output() explore = new EventEmitter<string>();
  constructor(private router:Router){
  }
  onViewAll(): void {
    console.log("called");
    this.router?.navigate(["/destinations"]);
  }

  onExplore(destination: string): void {
    this.router?.navigate(["/destinations"]);
  }
}
