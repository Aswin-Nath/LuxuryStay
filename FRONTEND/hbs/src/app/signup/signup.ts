import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
@Component({
  selector: 'app-signup',
  templateUrl: './signup.html',
  styleUrls: ['./signup.css'],
  imports:[CommonModule,RouterLink],
  standalone:true
})
export class Signup {

  showPassword = false;

  togglePassword() {
    this.showPassword = !this.showPassword;
  }
  enablePassword = false;
}
