
import { AuthenticationService } from "../../services/authentication.service";
import { Injectable } from "@angular/core";
import { Resolve } from "@angular/router";
import {map,tap} from "rxjs/operators";

@Injectable({ providedIn: 'root' })
export class PermissionResolver implements Resolve<boolean> {

  constructor(
    private auth: AuthenticationService,
    private permission: AuthenticationService
  ) {}

  resolve() {
    return this.auth.fetchUserPermissions().pipe(
      tap(perms => this.permission.loadPermissions(perms)),
      map(() => true)
    );
  }
}
