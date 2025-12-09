
import { PermissionService } from "../../services/permissions";
import { Injectable } from "@angular/core";
import { Resolve } from "@angular/router";
import {map,tap} from "rxjs/operators";
import { AuthenticationService } from "../../services/authentication.service";
@Injectable({ providedIn: 'root' })
export class PermissionResolver implements Resolve<boolean> {

  constructor(
    private auth: AuthenticationService,
    private permission: PermissionService
  ) {}

  resolve() {
    return this.auth.fetchUserPermissions().pipe(
      tap(perms => this.permission.load(perms)),
      map(() => true)
    );
  }
}
