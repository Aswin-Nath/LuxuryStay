import { Component } from '@angular/core';

@Component({
  selector: 'app-footer-section',
  standalone: true,
  template: `
    <footer class="bg-gray-900 text-white py-12 px-6">
      <div class="max-w-6xl mx-auto grid md:grid-cols-4 gap-8">
        <div>
          <h3 class="font-bold text-lg mb-4">LuxuryStay</h3>
          <p class="text-gray-400 text-sm">Providing the finest luxury accommodation experience.</p>
        </div>
        <div>
          <h4 class="font-bold mb-4">Quick Links</h4>
          <ul class="space-y-2 text-sm text-gray-400">
            <li><a href="#rooms" class="hover:text-yellow-500">Rooms</a></li>
            <li><a href="#offers" class="hover:text-yellow-500">Offers</a></li>
            <li><a href="#facilities" class="hover:text-yellow-500">Facilities</a></li>
            <li><a href="#destinations" class="hover:text-yellow-500">Destinations</a></li>
          </ul>
        </div>
        <div>
          <h4 class="font-bold mb-4">Contact</h4>
          <ul class="space-y-2 text-sm text-gray-400">
            <li>📞 +1 (800) LUXURY-1</li>
            <li>✉️ hello@luxurystay.com</li>
            <li>📍 123 Elegance Ave, City</li>
          </ul>
        </div>
        <div>
          <h4 class="font-bold mb-4">Follow Us</h4>
          <div class="flex space-x-4">
            <a href="#" class="text-gray-400 hover:text-yellow-500"><i class="fab fa-facebook"></i></a>
            <a href="#" class="text-gray-400 hover:text-yellow-500"><i class="fab fa-twitter"></i></a>
            <a href="#" class="text-gray-400 hover:text-yellow-500"><i class="fab fa-instagram"></i></a>
          </div>
        </div>
      </div>
      <div class="border-t border-gray-700 mt-8 pt-8 text-center text-gray-400 text-sm">
        <p>&copy; 2025 LuxuryStay Hotel. All rights reserved.</p>
      </div>
    </footer>
  `,
  styles: []
})
export class FooterSectionComponent {}
