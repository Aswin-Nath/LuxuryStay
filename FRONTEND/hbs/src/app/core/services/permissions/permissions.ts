import { Injectable } from "@angular/core";
import { BehaviorSubject, Observable } from "rxjs";

@Injectable({providedIn:"root"})
export class PermissionService{
    private userScopes = new BehaviorSubject<Set<string>>(new Set());
    public permissions$ = this.userScopes.asObservable();

    load(scopes:string[]){
        console.log("🔐 Loaded Scopes in PermissionService:", scopes);
        console.log("🔐 Total permissions:", scopes.length);
        scopes.forEach(s => console.log("  ✓", s));
        this.userScopes.next(new Set(scopes));
    }

    hasPermission(scope:string){
        return this.userScopes.value.has(scope);
    }

    hasAll(scopes:string[]){
        const current = this.userScopes.value;
        return scopes.every(s => current.has(s));
    }
    
}