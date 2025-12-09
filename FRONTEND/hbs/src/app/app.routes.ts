import { Routes } from '@angular/router';
import { Signup } from './features/auth/signup/pages/signup-form/signup-form.component';
import { Login } from './features/auth/login/pages/login-form/login-form.component';
import { ForgotPassword } from './features/auth/forgot-password/pages/forgot-password-form/forgot-password-form.component';
import { PermissionGuard } from './core/guards/permission.guard';
import { PublicGuard } from './core/guards/public.guard';
import { AuthGuard } from './core/guards/auth.guard';
import { PermissionResolver } from './core/resolver/permission.resolver';
import { ForbiddenPageComponent } from './shared/components/forbidden-page/forbidden-page.component';
import { HomePageComponent } from './pages/home_page/home-page/home-page.component';
import { CustomerDashboardComponent } from './features/dashboard/customer-dashboard/customer-dashboard.component';
import { AdminDashboardComponent } from './features/dashboard/admin-dashboard/admin-dashboard.component';
import { ProfileComponent } from './features/profile/customer/profile.component';
import { AdminProfileComponent } from './features/profile/admin/admin-profile.component';
import { AdminManagementComponent } from './features/admin-management/pages/admins-display/admins-display.component';
import { RoleManagementComponent } from './features/role-management/pages/roles-display/roles-display.component';
import { Rooms } from './features/rooms-management/admin/pages/rooms-display/room-display.component';
import { IndividualRoomComponent } from './features/rooms-management/admin/pages/individual-room/individual-room';
import { EditRoomComponent } from './features/rooms-management/admin/pages/edit-room/edit-room';
import { RoomTypesAmenitiesManagementComponent } from './features/amenity-management/pages/amenity-details/amenity-details.component';
import { EditRoomTypeComponent } from './features/room-type-management/pages/edit-room-type/edit-room-type';
import { ViewRoomTypeComponent } from './features/room-type-management/pages/individual-room-type-details/individual-room-type-details.component';
import { BookingComponent } from './features/customer_booking/room_booking/pages/room_booking/room_booking.component';
import { MyBookingsComponent } from './features/booking-management/customer/pages/my-bookings/my-bookings.component';
import { BookingDetailsComponent } from './features/booking-management/customer/pages/individual-booking/individual-booking.component';
import { OfferManagementComponent } from './features/offer-management-for/Admin/pages/offersDisplay/offer-management.component';
import { CreateOfferComponent } from './features/offer-management-for/Admin/pages/create-offer/create-offer.component';
import { EditOfferComponent } from './features/offer-management-for/Admin/pages/edit-offer/edit-offer.component';
import { IndividualOfferDetailsComponent } from './features/offer-management-for/Admin/pages/individual-offer-details/individual-offer-details.component';
import { AdminBookingsComponent } from './features/booking-management/admin/pages/bookings/bookings.component';
import { AdminBookingDetailsComponent } from './features/booking-management/admin/pages/individual-booking/individual-booking.component';
import { OfferDisplayComponent } from './features/offer-management-for/Customer/pages/offers-display/offers-display.component';
import { RoomDisplayComponent } from './features/rooms-management/customer/pages/rooms-display/rooms-display.component';
import { WishlistComponent } from './features/wishlist-management/pages/wishlist-display/wishlist-display.component';
import { CustomerRoomDetailComponent } from './features/rooms-management/customer/pages/individual-room-details/individual-room-details.component';
import { CustomerOfferDetailComponent } from './features/offer-management-for/Customer/pages/individual-offers-details/individual-offers-details.component';
import { OfferBookingComponent } from './features/customer_booking/offer_booking/pages/offer_booking/offer_booking.component';
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
					{ path: 'booking/:booking_id', component: BookingDetailsComponent },
					{ path: 'offers', component: OfferDisplayComponent },
					{ path: 'rooms', component: RoomDisplayComponent },
					{ path: 'wishlist', component: WishlistComponent },
					{ path: 'room-details/:id', component: CustomerRoomDetailComponent },
					{ path: 'offer-details/:id', component: CustomerOfferDetailComponent },
					{ path: 'offers/book/:offerId', component: OfferBookingComponent },
					{
						path: 'bookings',
						children: [
							{ path: '', component: MyBookingsComponent },
							{ path: 'details/:id', component: BookingDetailsComponent }
						]
					},
					{ path: '', redirectTo: 'dashboard', pathMatch: 'full' },
					{path:"offer-claim",component:BookingComponent}
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
						path: 'bookings',
						children: [
							{ path: '', component: AdminBookingsComponent },
							{ path: 'booking/:id', component: AdminBookingDetailsComponent }
						]
					},
					{
						path: 'offers',
						children: [
							{ path: '', component: OfferManagementComponent },
							{ path: 'create', component: CreateOfferComponent },
							{ path: 'edit/:id', component: EditOfferComponent },
							{ path: 'view/:id', component: IndividualOfferDetailsComponent }
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
