import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CustomerNavbarComponent } from '../../layout/Customer/customer-navbar/customer-navbar.component';
import { FooterComponent } from '../../layout/Customer/footer/footer.component';

@Component({
  selector: 'app-cancellation-policy',
  standalone: true,
  imports: [CommonModule, RouterModule, CustomerNavbarComponent, FooterComponent],
  templateUrl: './cancellation-policy.page.html',
  styleUrl: './cancellation-policy.page.css'
})
export class CancellationPolicyComponent implements OnInit {
  constructor() {}

  ngOnInit(): void {}
}
