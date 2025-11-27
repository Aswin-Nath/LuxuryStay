import { Injectable } from "@angular/core";
import { AuthenticationService } from "../services/authentication/authentication.service";
import { PermissionService } from "../services/permissions/permissions";
import { CanActivate,ActivatedRouteSnapshot,Router, GuardResult, MaybeAsync, RouterStateSnapshot } from "@angular/router";
import 'reflect-metadata';



@Injectable({providedIn:"root"})
export class PermissionGuard implements CanActivate{

    constructor
    (
    private permissionService:PermissionService,
    private auth:AuthenticationService,
    private router:Router
    )
    {

    }

    canActivate(route: ActivatedRouteSnapshot): boolean{
        const routeScopes=route.data['permissions'] || [];
        const componentData=route.routeConfig?.component as any;
        const decaratorScopes:string []=Reflect.getMetadata("permissions",componentData) || [];
        //  Merge all required permissions
        const requiredScopes = [...routeScopes, ...decaratorScopes];

        // 5️⃣ No permission required → allow access
        if (requiredScopes.length === 0) return true;

        // 6️⃣ Check if user has all required permissions
        const allowed = this.permissionService.hasAll(requiredScopes);

        if (!allowed) {
            this.router.navigate(['/403']);
            return false;
            }
        return true;
}
}