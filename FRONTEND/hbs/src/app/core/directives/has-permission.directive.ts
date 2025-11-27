import { Directive, Input, TemplateRef, ViewContainerRef } from "@angular/core";
import { PermissionService } from "../services/permissions/permissions";

@Directive({
    selector:"[appHasPermission]",
    standalone: true
})
export class HasPermissionDirective{
    private scope!: string;
    
    constructor(
        private template:TemplateRef<any>,
        private view:ViewContainerRef,
        private permissions:PermissionService
    ){
        // Subscribe to permission changes and re-render
        this.permissions.permissions$.subscribe(() => {
            this.updateView();
        });
    }

    @Input() set appHasPermission(scope:string){
        this.scope = scope;
        this.updateView();
    }

    private updateView(){
        const hasAccess = this.permissions.hasPermission(this.scope);
        console.log(`🔍 Directive Check [${this.scope}]:`, hasAccess);
        this.view.clear();
        if(hasAccess){
            console.log(`✅ SHOWING content for [${this.scope}]`);
            this.view.createEmbeddedView(this.template);
        } else {
            console.log(`❌ HIDING content for [${this.scope}]`);
        }
    }
}