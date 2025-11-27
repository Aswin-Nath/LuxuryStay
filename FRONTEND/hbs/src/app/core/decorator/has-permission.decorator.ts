import 'reflect-metadata';

export function HasPermission(scopes: string | string[]) {
  return function (constructor: Function) {
    Reflect.defineMetadata(
      'permissions',
      Array.isArray(scopes) ? scopes : [scopes],
      constructor
    );
  };
}
