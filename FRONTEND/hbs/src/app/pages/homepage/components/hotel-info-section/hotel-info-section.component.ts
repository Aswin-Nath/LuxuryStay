import { Component } from '@angular/core';

@Component({
  selector: 'app-hotel-info-section',
  standalone: true,
  template: `
    <section id="hotel-info" class="scroll-mt-24 py-16 px-6 bg-white">
      <div class="max-w-6xl mx-auto">
        <h2 class="cursive-heading text-3xl sm:text-4xl font-extrabold mb-12 text-center bg-linear-to-r from-yellow-600 to-red-600 bg-clip-text text-transparent">
          Hotel Information
        </h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-8 text-gray-700 text-sm sm:text-base">
          <div class="space-y-2 border-t pt-3">
            <h3 class="font-bold text-lg">Check In / Out</h3>
            <p>Check-in: 3:00 PM</p>
            <p>Check-out: 11:00 AM</p>
          </div>
          <div class="space-y-2 border-t pt-3">
            <h3 class="font-bold text-lg">Rooms & Suites</h3>
            <p>250+ Luxury Rooms</p>
            <p>Modern Amenities</p>
          </div>
          <div class="space-y-2 border-t pt-3">
            <h3 class="font-bold text-lg">Dining</h3>
            <p>5 Fine Dining Restaurants</p>
            <p>24/7 Room Service</p>
          </div>
          <div class="space-y-2 border-t pt-3">
            <h3 class="font-bold text-lg">Wellness</h3>
            <p>Spa & Fitness Center</p>
            <p>Indoor Pool</p>
          </div>
        </div>
      </div>
    </section>
  `,
  styles: []
})
export class HotelInfoSectionComponent {}
