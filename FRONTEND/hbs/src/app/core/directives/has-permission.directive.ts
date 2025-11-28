import { Directive, Input, TemplateRef, ViewContainerRef } from "@angular/core";
import { PermissionService } from "../services/permissions/permissions";

@Directive({
    selector:"[appHasPermission]",
    standalone: true
})
export class HasPermissionDirective{
    private scope: string | null = null;
    
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

    @Input() set appHasPermission(scope: string | null | undefined){
        // Store the exact scope value passed
        this.scope = scope || null;
        this.updateView();
    }

    private updateView(){
        // If no permission is set (null or undefined), show the element
        if (!this.scope) {
            console.log(`🔍 Directive Check [NO PERMISSION]:`, true);
            this.view.clear();
            this.view.createEmbeddedView(this.template);
            return;
        }

        // If scope is 'ANY', show the element
        if (this.scope === 'ANY') {
            console.log(`🔍 Directive Check [ANY]:`, true);
            this.view.clear();
            this.view.createEmbeddedView(this.template);
            return;
        }

        // Check if user has the permission
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