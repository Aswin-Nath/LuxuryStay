import { Routes } from '@angular/router';
import { Signup } from './features/signup/signup';
import { Login } from './features/login/login';
import { HomePageComponent } from './pages/home_page/home-page/home-page.component';

export const routes: Routes = [
	{ path: '', redirectTo: 'login', pathMatch: 'full' },
	{ path: 'login', component: Login },
	{ path: 'signup', component: Signup },
	{ path: 'home_page', component: HomePageComponent },
	{ path: '**', redirectTo: 'login' },
];
