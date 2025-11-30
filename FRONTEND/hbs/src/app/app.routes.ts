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
import { ProfileComponent } from './features/profile/customer/profile.component';
import { AdminProfileComponent } from './features/profile/admin/admin-profile.component';
import { AdminManagementComponent } from './features/admin-management/dashboard/admin-management.component';
import { RoleManagementComponent } from './features/admin-management/roles-management/role-management.component';
import { Rooms } from './features/room-management/rooms/rooms';
import { IndividualRoomComponent } from './features/room-management/individual-room/individual-room';
import { EditRoomComponent } from './features/room-management/edit-room/edit-room';
import { RoomTypesAmenitiesManagementComponent } from './features/room-management/room-types-amenities-management/room-types-amenities-management';
import { EditRoomTypeComponent } from './features/room-management/edit-room-type/edit-room-type';
import { ViewRoomTypeComponent } from './features/room-management/view-room-type/view-room-type';
import { BookingComponent } from './features/booking/booking.component';
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
					{ path: 'profile', component: ProfileComponent },
					{ path: 'booking', component: BookingComponent },
					{ path: '', redirectTo: 'dashboard', pathMatch: 'full' }
				]
			},
			// Admin Routes
			{
				path: 'admin',
				children: [
					{ path: 'dashboard', component: AdminDashboardComponent },
					{ path: 'profile', component: AdminProfileComponent },
					{ 
						path: 'management', 
						component: AdminManagementComponent,
						canActivate: [PermissionGuard],
						data: { requiredPermission: 'ADMIN_CREATION:READ' }
					},
					{ 
						path: 'roles', 
						component: RoleManagementComponent,
						canActivate: [PermissionGuard],
						data: { requiredPermission: 'ADMIN_CREATION:READ' }
					},
					{
						path: 'rooms',
						children: [
							{ path: '', component: Rooms },
							{ path: ':id/view', component: IndividualRoomComponent },
							{ path: ':id/edit', component: EditRoomComponent }
						]
					},
					{
						path: 'room-types-amenities',
						component: RoomTypesAmenitiesManagementComponent,
						canActivate: [PermissionGuard],
						data: { requiredPermission: 'ADMIN_CREATION:READ' }
					},
					{
						path: 'room-type/:id/view',
						component: ViewRoomTypeComponent,
						canActivate: [PermissionGuard],
						data: { requiredPermission: 'ROOM_MANAGEMENT:READ' }
					},
					{
						path: 'edit-room-type/:id',
						component: EditRoomTypeComponent,
						canActivate: [PermissionGuard],
						data: { requiredPermission: 'ROOM_MANAGEMENT:WRITE' }
					},
					{ path: '', redirectTo: 'dashboard', pathMatch: 'full' }
				]
			}
		]
	},
	{ path: '403', component: ForbiddenPageComponent },
	{ path: '**', redirectTo: 'login' }
];
