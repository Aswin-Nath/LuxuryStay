import { Routes } from '@angular/router';
import { Signup } from './features/signup/signup';
import { Login } from './features/login/login';
import { ForgotPassword } from './features/forgot-password/forgot-password';
import { HomePageComponent } from './pages/home_page/home-page/home-page.component';
import { AuthGuard } from './core/guards/auth.guard';
import { PublicGuard } from './core/guards/public.guard';
import { ForbiddenPageComponent } from './core/components/forbidden-page/forbidden-page.component';
import { PermissionResolver } from './core/resolver/permission.resolver';
import { PermissionGuard } from './core/guards/permission.guard';
import { CustomerDashboardComponent } from './features/dashboard/customer-dashboard/customer-dashboard.component';
import { AdminDashboardComponent } from './features/dashboard/admin-dashboard/admin-dashboard.component';

export const routes: Routes = [
	{ path: '', redirectTo: 'login', pathMatch: 'full' },
	{ path: 'login', component: Login, canActivate: [PublicGuard] },
	{ path: 'forgot-password', component: ForgotPassword, canActivate: [PublicGuard] },
	{ path: 'signup', component: Signup, canActivate: [PublicGuard] },
	{
		path: '',
		canActivate: [AuthGuard],
		resolve: { permissions: PermissionResolver },
		children: [
			{
				path: 'home_page',
				component: HomePageComponent,
				canActivate: [PermissionGuard]
			},
			// Customer Routes
			{
				path: '',
				children: [
					{ path: 'dashboard', component: CustomerDashboardComponent },
					{ path: '', redirectTo: 'dashboard', pathMatch: 'full' }
				]
			},
			// Admin Routes
			{
				path: 'admin',
				children: [
					{ path: 'dashboard', component: AdminDashboardComponent },
					{ path: '', redirectTo: 'dashboard', pathMatch: 'full' }
				]
			}
		]
	},
	{ path: '403', component: ForbiddenPageComponent },
	{ path: '**', redirectTo: 'login' }
];
