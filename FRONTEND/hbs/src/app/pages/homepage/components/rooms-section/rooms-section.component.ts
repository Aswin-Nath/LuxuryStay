import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

interface Room {
  id: number;
  name: string;
  image: string;
  description: string;
  price: string;
}

@Component({
  selector: 'app-rooms-section',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section id="rooms" class="scroll-mt-24 py-16 px-6 bg-gray-50 text-center">
      <h2 class="cursive-heading text-3xl sm:text-4xl font-bold mb-12 bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
        Our Rooms
      </h2>
      <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-10 max-w-6xl mx-auto text-left">
        <div *ngFor="let room of rooms" class="flex flex-col">
          <img [src]="room.image" [alt]="room.name" class="h-56 w-full object-cover rounded-lg shadow">
          <h3 class="mt-4 font-serif text-lg sm:text-xl font-bold uppercase">{{ room.name }}</h3>
          <p class="text-gray-600 text-sm mt-2 grow">{{ room.description }}</p>
          <div class="flex items-center justify-between mt-4">
            <span class="text-yellow-600 font-semibold">{{ room.price }}</span>
            <button (click)="onAddToWishlist(room.id)" class="text-red-600 hover:text-red-700">
              <i class="fas fa-heart"></i>
            </button>
          </div>
        </div>
      </div>
      <div class="text-center mt-10">
        <button (click)="onViewAll()"
          class="px-6 py-3 bg-yellow-500 text-white font-semibold rounded-lg hover:bg-yellow-600 transition">
          View All Rooms
        </button>
      </div>
    </section>
  `,
  styles: []
})
export class RoomsSectionComponent {
  @Input() rooms: Room[] = [];
  @Output() viewAll = new EventEmitter<void>();
  @Output() addToWishlist = new EventEmitter<number>();

  onViewAll(): void {
    this.viewAll.emit();
  }

  onAddToWishlist(roomId: number): void {
    this.addToWishlist.emit(roomId);
  }
}
